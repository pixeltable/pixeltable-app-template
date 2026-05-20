"""Dashboard endpoints: stats, alerts, activity."""
import logging
from collections import Counter
from datetime import datetime

from fastapi import APIRouter
import pixeltable as pxt

import config
from functions import gemini_text, parse_segment_analysis, severity_from_analysis
from models import ActivityItem, AlertItem, AlertsResponse, DashboardStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])

COST_PER_REMOTE_INSPECTION = 300.0


def _table(name: str):
    return pxt.get_table(f'{config.NAMESPACE}.{name}')


@router.get('/stats', response_model=DashboardStats)
def get_stats():
    """Aggregate statistics for the dashboard — ROI-oriented."""
    stats: dict = {
        'total_videos': 0, 'total_frames': 0, 'total_segments': 0,
        'total_audio_chunks': 0, 'total_transcripts': 0, 'total_alerts': 0,
        'anomalies_detected': 0, 'critical_alerts': 0, 'sites_monitored': 0,
        'est_cost_savings': 0.0, 'avg_processing_time': 0.0,
        'sites': [], 'severity_counts': {'critical': 0, 'warning': 0, 'info': 0},
        'recent_transcripts': [], 'top_labels': [],
    }

    try:
        videos = _table('videos')
        video_rows = list(videos.select(videos.site_name, videos.duration).collect())
        stats['total_videos'] = len(video_rows)
        site_names = sorted({r['site_name'] for r in video_rows if r.get('site_name')})
        stats['sites'] = site_names
        stats['sites_monitored'] = len(site_names)
        stats['est_cost_savings'] = len(video_rows) * COST_PER_REMOTE_INSPECTION
        durations = [r['duration'] for r in video_rows if r.get('duration')]
        stats['avg_processing_time'] = sum(durations) / len(durations) if durations else 0.0
    except Exception as e:
        logger.warning(f'Could not count videos: {e}')

    try:
        stats['total_frames'] = _table('video_frames').count()
    except Exception as e:
        logger.warning(f'Could not count frames: {e}')

    # Severity + labels from video_segments (Gemini analysis) + DETR
    try:
        segs = _table('video_segments')
        seg_rows = list(segs.select(segs.segment_analysis).collect())
        stats['total_segments'] = len(seg_rows)

        sev_counts: Counter[str] = Counter()
        for r in seg_rows:
            analysis = parse_segment_analysis(r.get('segment_analysis'))
            sev = severity_from_analysis(analysis)
            sev_counts[sev] += 1

        stats['severity_counts'] = dict(sev_counts)
        stats['anomalies_detected'] = sev_counts['critical'] + sev_counts['warning']
        stats['critical_alerts'] = sev_counts['critical']
        stats['total_alerts'] = sev_counts['critical']
    except Exception as e:
        logger.warning(f'Could not count segments: {e}')

    # Top DETR labels from video_frames
    try:
        frames = _table('video_frames')
        frame_rows = list(frames.select(frames.detr_seg).collect())
        label_counter: Counter[str] = Counter()
        for r in frame_rows:
            seg = r.get('detr_seg') or {}
            for info in seg.get('segments_info', []):
                label = info.get('label_text')
                if label:
                    label_counter[label] += 1
        stats['top_labels'] = [{'label': lbl, 'count': cnt} for lbl, cnt in label_counter.most_common(10)]
    except Exception as e:
        logger.warning(f'Could not count labels: {e}')

    try:
        stats['total_audio_chunks'] = _table('audio_chunks').count()
    except Exception as e:
        logger.warning(f'Could not count audio chunks: {e}')

    try:
        sentences = _table('video_sentences')
        stats['total_transcripts'] = sentences.count()
        recent = list(sentences.select(sentences.text).limit(8).collect())
        stats['recent_transcripts'] = [r['text'] for r in recent if r.get('text')]
    except Exception as e:
        logger.warning(f'Could not count transcripts: {e}')

    return stats


@router.get('/alerts', response_model=AlertsResponse)
def get_alerts(site_name: str | None = None, limit: int = 50):
    """Segments classified as CRITICAL or WARNING by Gemini analysis."""
    try:
        segs = _table('video_segments')
        base = segs.where(segs.site_name == site_name) if site_name else segs
        rows = list(
            base.select(
                uuid=segs.uuid,
                segment_analysis=segs.segment_analysis,
                segment_start=segs.segment_start,
                segment_end=segs.segment_end,
                video_segment=segs.video_segment,
                site_name=segs.site_name,
                camera_id=segs.camera_id,
            ).collect()
        )

        items: list[dict] = []
        for r in rows:
            analysis = parse_segment_analysis(r.get('segment_analysis'))
            sev = severity_from_analysis(analysis)
            if sev == 'info':
                continue
            video_path = str(r.get('video_segment', ''))
            items.append({
                'uuid': str(r.get('uuid', '')),
                'frame': '',
                'segment_labels': analysis.get('equipment', []),
                'severity': sev,
                'frame_description': analysis.get('description', ''),
                'site_name': r.get('site_name'),
                'camera_id': r.get('camera_id'),
                'video_url': f'/api/browse/media?path={video_path}' if video_path else None,
                'severity_reason': analysis.get('severity_reason', ''),
            })
            if len(items) >= limit:
                break

        return AlertsResponse(alerts=items, total=len(items))
    except Exception as e:
        logger.warning(f'Could not fetch alerts: {e}')
        return AlertsResponse(alerts=[], total=0)


@router.get('/activity', response_model=list[ActivityItem])
def get_activity(limit: int = 20):
    """Recent processing activity: uploads, frame analysis, transcriptions."""
    items: list[dict] = []

    try:
        videos = _table('videos')
        rows = list(
            videos.select(
                site_name=videos.site_name, camera_id=videos.camera_id,
                timestamp=videos.timestamp, duration=videos.duration,
            )
            .order_by(videos.timestamp, asc=False)
            .limit(limit)
            .collect()
        )
        for r in rows:
            ts = r.get('timestamp')
            items.append({
                'type': 'upload',
                'label': f"Video uploaded ({r.get('camera_id', 'unknown')})",
                'detail': f"Duration: {r.get('duration', 0):.1f}s" if r.get('duration') else None,
                'site_name': r.get('site_name'),
                'timestamp': ts.isoformat() if isinstance(ts, datetime) else None,
            })
    except Exception as e:
        logger.warning(f'Could not fetch video activity: {e}')

    try:
        frames = _table('video_frames')
        total_frames = frames.count()
        if total_frames > 0:
            items.append({
                'type': 'analysis',
                'label': f'{total_frames} frames with DETR segmentation',
                'detail': 'Auto panoptic segmentation + overlay',
            })
    except Exception as e:
        logger.warning(f'Could not fetch frame activity: {e}')

    try:
        seg_count = _table('video_segments').count()
        if seg_count > 0:
            items.append({
                'type': 'segments',
                'label': f'{seg_count} segments analyzed by Gemini',
                'detail': 'Description + severity + PPE in one JSON call per segment',
            })
    except Exception as e:
        logger.warning(f'Could not fetch segment activity: {e}')

    try:
        chunk_count = _table('audio_chunks').count()
        if chunk_count > 0:
            items.append({
                'type': 'audio',
                'label': f'{chunk_count} audio chunks transcribed',
                'detail': 'Whisper local transcription',
            })
    except Exception as e:
        logger.warning(f'Could not fetch audio activity: {e}')

    return items[:limit]
