import { useState, useEffect } from 'react'
import {
  Frame, Film, Clapperboard, AudioLines, Loader2, Play, ScanEye, X,
  ClipboardList, HardHat, ShieldAlert, Wrench, AlertTriangle,
} from 'lucide-react'
import { cn, toDataUrl, formatDuration } from '@/lib/utils'
import { FormattedText } from '@/components/ui/formatted-text'
import { Badge } from '@/components/ui/badge'
import { SeverityBadge } from '@/components/ui/severity-badge'
import * as api from '@/lib/api'
import type {
  BrowseFrameItem,
  BrowseSegmentItem,
  BrowseSceneItem,
  BrowseAudioItem,
  BrowseDetectionItem,
} from '@/types'

const MEDIUM_TABS = [
  { id: 'detections', label: 'Detections', icon: ScanEye },
  { id: 'frames', label: 'Frames', icon: Frame },
  { id: 'segments', label: 'Video Segments', icon: Film },
  { id: 'scenes', label: 'Scenes', icon: Clapperboard },
  { id: 'audio', label: 'Audio', icon: AudioLines },
] as const

type MediumTab = (typeof MEDIUM_TABS)[number]['id']

export function BrowsePage() {
  const [tab, setTab] = useState<MediumTab>('detections')

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4">
        <h2 className="text-lg font-semibold">Asset Inspection Browser</h2>
        <p className="text-sm text-muted-foreground">
          Explore detections, frames, video segments, scenes, and audio across all inspection footage
        </p>
      </div>

      <div className="flex items-center gap-1 px-6 pb-3">
        {MEDIUM_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer',
              tab === id
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent',
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {tab === 'detections' && <DetectionsGrid />}
        {tab === 'frames' && <FrameGridView />}
        {tab === 'segments' && <SegmentsList />}
        {tab === 'scenes' && <ScenesList />}
        {tab === 'audio' && <AudioList />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Pre-computed DETR panoptic segmentation grid
// ---------------------------------------------------------------------------

function DetectionsGrid() {
  const [detections, setDetections] = useState<BrowseDetectionItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selected, setSelected] = useState<BrowseDetectionItem | null>(null)

  useEffect(() => {
    setIsLoading(true)
    api.browseDetections({ limit: 48 })
      .then(setDetections)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading DETR panoptic segmentation results...
      </div>
    )
  }

  if (!detections.length) {
    return (
      <div className="text-center text-muted-foreground py-12 text-sm">
        No detections yet. Upload videos &mdash; DETR panoptic segmentation runs automatically on every frame.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        DETR Panoptic Segmentation &mdash; auto-computed on every video frame via Pixeltable
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {detections.map((d, i) => (
          <button
            key={i}
            onClick={() => setSelected(d)}
            className="relative group rounded-lg border overflow-hidden bg-card cursor-pointer text-left hover:ring-2 hover:ring-primary/50 transition-all"
          >
            <img
              src={toDataUrl(d.segmentation_overlay)}
              alt={`Detection ${i}`}
              className="w-full aspect-video object-cover"
            />
            <div className="p-1.5 space-y-0.5">
              <div className="flex items-center gap-1">
                {d.site_name && <p className="text-[10px] text-muted-foreground truncate">{d.site_name}</p>}
              </div>
              {d.detected_labels.length > 0 && (
                <div className="flex flex-wrap gap-0.5">
                  {d.detected_labels.slice(0, 3).map((label, li) => (
                    <span key={li} className="text-[9px] bg-primary/10 text-primary px-1 py-0.5 rounded">{label}</span>
                  ))}
                  {d.detected_labels.length > 3 && (
                    <span className="text-[9px] text-muted-foreground">+{d.detected_labels.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      {selected && <DetectionDetailPanel detection={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function DetectionDetailPanel({ detection, onClose }: { detection: BrowseDetectionItem; onClose: () => void }) {
  const thingSegments = detection.segments_info.filter(s => s.label_text)

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card rounded-xl border shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <ScanEye className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">DETR Panoptic Segmentation</h3>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-muted transition-colors cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <img
            src={toDataUrl(detection.segmentation_overlay)}
            alt="Segmentation overlay"
            className="w-full rounded-lg border"
          />

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {detection.site_name && <span>{detection.site_name}</span>}
            {detection.camera_id && <Badge variant="default" className="text-[10px]">{detection.camera_id}</Badge>}
            {detection.asset_id && <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">{detection.asset_id}</span>}
          </div>

          {thingSegments.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Detected Objects ({thingSegments.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {thingSegments.map((seg, i) => (
                  <span key={i} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">
                    {seg.label_text}
                    <span className="text-primary/60 ml-1">{(seg.score * 100).toFixed(0)}%</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <p className="text-[10px] text-muted-foreground italic">
            Computed automatically by Pixeltable &middot; facebook/detr-resnet-50-panoptic &middot; overlay_segmentation
          </p>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Frame grid (thumbnails only — AI analysis is on segments)
// ---------------------------------------------------------------------------

function FrameGridView() {
  const [frames, setFrames] = useState<BrowseFrameItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    api.browseFrames({ limit: 80 }).then(setFrames).catch(() => {}).finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading frames...
      </div>
    )
  }

  if (!frames.length) {
    return (
      <div className="text-center text-muted-foreground py-12 text-sm">
        No frames yet. Upload videos to start analyzing.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Extracted at 1 fps &mdash; used for DETR segmentation + multimodal embedding search
      </div>
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-1.5">
        {frames.map((f, i) => (
          <div
            key={i}
            className="relative rounded-md border overflow-hidden bg-card"
          >
            <img src={toDataUrl(f.frame)} alt={`Frame ${i}`} className="w-full aspect-video object-cover" />
            {f.site_name && (
              <p className="px-1 py-0.5 text-[9px] text-muted-foreground truncate">{f.site_name}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Segments list (Gemini AI analysis — 1 JSON call per segment)
// ---------------------------------------------------------------------------

function SegmentsList() {
  const [segments, setSegments] = useState<BrowseSegmentItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [playingIdx, setPlayingIdx] = useState<number | null>(null)
  const [selected, setSelected] = useState<BrowseSegmentItem | null>(null)

  useEffect(() => {
    setIsLoading(true)
    api.browseSegments({ limit: 60 }).then(setSegments).catch(() => {}).finally(() => setIsLoading(false))
  }, [])

  if (isLoading) return <div className="flex items-center justify-center py-12 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mr-2" />Loading segments...</div>
  if (!segments.length) return <div className="text-center text-muted-foreground py-12 text-sm">No segments found</div>

  return (
    <div className="space-y-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        AI Analysis &mdash; 1 Gemini JSON call per segment (description + severity + PPE)
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {segments.map((s, i) => (
          <div key={i} className="rounded-lg border bg-card overflow-hidden">
            {playingIdx === i && s.video_url ? (
              <video src={s.video_url} controls autoPlay className="w-full aspect-video bg-black" />
            ) : (
              <button
                onClick={() => s.video_url && setPlayingIdx(i)}
                className={cn('w-full aspect-video bg-muted/50 flex items-center justify-center', s.video_url ? 'cursor-pointer hover:bg-muted transition-colors' : 'cursor-default')}
              >
                {s.video_url ? (
                  <div className="flex flex-col items-center gap-1 text-muted-foreground">
                    <div className="rounded-full bg-primary/10 p-3"><Play className="h-6 w-6 text-primary fill-primary" /></div>
                    <span className="text-xs">Click to play</span>
                  </div>
                ) : (
                  <Film className="h-8 w-8 text-muted-foreground/40" />
                )}
              </button>
            )}
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{s.segment_start.toFixed(1)}s &ndash; {s.segment_end.toFixed(1)}s</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">{formatDuration(s.segment_end - s.segment_start)}</span>
                  {s.severity && <SeverityBadge severity={s.severity} />}
                </div>
              </div>

              {s.description && (
                <p className="text-xs text-muted-foreground line-clamp-2">{s.description}</p>
              )}

              <div className="flex items-center gap-2 flex-wrap">
                {s.site_name && <span className="text-xs text-muted-foreground">{s.site_name}</span>}
                {s.camera_id && <Badge variant="default" className="text-[10px]">{s.camera_id}</Badge>}
                {s.ppe_status && s.ppe_status !== 'N_A' && (
                  <span className="flex items-center gap-0.5 text-[10px] text-amber-600 dark:text-amber-400">
                    <HardHat className="h-3 w-3" /> {s.ppe_status}
                  </span>
                )}
              </div>

              {(s.equipment?.length > 0 || s.hazards?.length > 0) && (
                <div className="flex flex-wrap gap-1">
                  {s.equipment?.slice(0, 3).map((eq, j) => (
                    <span key={`e${j}`} className="text-[9px] bg-blue-500/10 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                      <Wrench className="h-2.5 w-2.5" />{eq}
                    </span>
                  ))}
                  {s.hazards?.slice(0, 2).map((hz, j) => (
                    <span key={`h${j}`} className="text-[9px] bg-red-500/10 text-red-600 dark:text-red-400 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                      <AlertTriangle className="h-2.5 w-2.5" />{hz}
                    </span>
                  ))}
                </div>
              )}

              <button
                onClick={() => setSelected(s)}
                className="text-[10px] text-primary hover:underline cursor-pointer"
              >
                View full analysis &rarr;
              </button>
            </div>
          </div>
        ))}
      </div>

      {selected && <SegmentDetailPanel segment={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function SegmentDetailPanel({ segment, onClose }: { segment: BrowseSegmentItem; onClose: () => void }) {
  const [showWorkOrder, setShowWorkOrder] = useState(false)

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card rounded-xl border shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">Segment AI Analysis</h3>
            {segment.severity && <SeverityBadge severity={segment.severity} />}
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-muted transition-colors cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {segment.video_url && (
            <video src={segment.video_url} controls className="w-full rounded-lg border aspect-video bg-black" />
          )}

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{segment.segment_start.toFixed(1)}s &ndash; {segment.segment_end.toFixed(1)}s</span>
            {segment.site_name && <span>{segment.site_name}</span>}
            {segment.camera_id && <Badge variant="default" className="text-[10px]">{segment.camera_id}</Badge>}
            {segment.asset_id && <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">{segment.asset_id}</span>}
          </div>

          {segment.description && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI Assessment</div>
              <div className="bg-muted/50 rounded-lg p-3 border">
                <FormattedText text={segment.description} className="text-sm" />
              </div>
            </div>
          )}

          {segment.severity_reason && (
            <div className="text-xs">
              <span className="font-medium text-muted-foreground">Severity Reason:</span>{' '}
              <span className="text-foreground/80">{segment.severity_reason}</span>
            </div>
          )}

          {segment.ppe_status && segment.ppe_status !== 'N_A' && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                <HardHat className="h-3.5 w-3.5" /> PPE Compliance
              </div>
              <div className="bg-muted/50 rounded-lg p-3 border text-sm">
                <span className="font-medium">{segment.ppe_status}</span>
                {segment.ppe_details && <span className="text-muted-foreground"> &mdash; {segment.ppe_details}</span>}
              </div>
            </div>
          )}

          {segment.equipment && segment.equipment.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                <Wrench className="h-3.5 w-3.5" /> Equipment Observed
              </div>
              <div className="flex flex-wrap gap-1.5">
                {segment.equipment.map((eq, i) => (
                  <span key={i} className="text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-1 rounded-full">{eq}</span>
                ))}
              </div>
            </div>
          )}

          {segment.hazards && segment.hazards.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" /> Identified Hazards
              </div>
              <div className="flex flex-wrap gap-1.5">
                {segment.hazards.map((hz, i) => (
                  <span key={i} className="text-xs bg-red-500/10 text-red-600 dark:text-red-400 px-2 py-1 rounded-full">{hz}</span>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 border-t">
            <button onClick={() => setShowWorkOrder(!showWorkOrder)}
              className="flex items-center gap-1.5 rounded-md bg-orange-600 text-white px-3 py-1.5 text-sm font-medium hover:bg-orange-700 cursor-pointer">
              <ClipboardList className="h-3.5 w-3.5" />
              {showWorkOrder ? 'Hide Work Order' : 'Generate Work Order'}
            </button>

            {showWorkOrder && (
              <div className="mt-3 bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-orange-800 dark:text-orange-300">Work Order — {segment.asset_id ?? 'N/A'}</h4>
                  <span className={cn(
                    'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase',
                    segment.severity === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                      : segment.severity === 'warning' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300'
                        : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
                  )}>Priority: {segment.severity ?? 'info'}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div><span className="font-medium text-muted-foreground">Site:</span> {segment.site_name ?? 'N/A'}</div>
                  <div><span className="font-medium text-muted-foreground">Camera:</span> {segment.camera_id ?? 'N/A'}</div>
                  <div><span className="font-medium text-muted-foreground">Asset ID:</span> {segment.asset_id ?? 'N/A'}</div>
                  <div><span className="font-medium text-muted-foreground">Time Range:</span> {segment.segment_start.toFixed(1)}s &ndash; {segment.segment_end.toFixed(1)}s</div>
                </div>
                {segment.description && (
                  <div className="text-xs">
                    <span className="font-medium text-muted-foreground">Finding:</span>{' '}
                    <span className="text-foreground/80">{segment.description}</span>
                  </div>
                )}
                <p className="text-[10px] text-muted-foreground italic">Generated by SiteWatch AI &mdash; Condition-Based Maintenance (CBM)</p>
              </div>
            )}
          </div>

          <p className="text-[10px] text-muted-foreground italic">
            1 Gemini JSON call per segment &middot; description + severity + PPE + equipment + hazards
          </p>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Scenes list
// ---------------------------------------------------------------------------

function ScenesList() {
  const [scenes, setScenes] = useState<BrowseSceneItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [playingIdx, setPlayingIdx] = useState<number | null>(null)

  useEffect(() => {
    setIsLoading(true)
    api.browseScenes({ limit: 60 }).then(setScenes).catch(() => {}).finally(() => setIsLoading(false))
  }, [])

  if (isLoading) return <div className="flex items-center justify-center py-12 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mr-2" />Loading scenes...</div>
  if (!scenes.length) return <div className="text-center text-muted-foreground py-12 text-sm">No scenes detected</div>

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {scenes.map((s, i) => {
        const duration = s.scene_end - s.scene_start
        const mediaUrl = s.video_url?.split('#')[0]
        return (
          <div key={i} className="rounded-lg border bg-card overflow-hidden">
            {playingIdx === i && mediaUrl ? (
              <video src={mediaUrl} controls autoPlay className="w-full aspect-video bg-black"
                onLoadedMetadata={(e) => { e.currentTarget.currentTime = s.scene_start }}
                onTimeUpdate={(e) => { if (e.currentTarget.currentTime >= s.scene_end) e.currentTarget.pause() }}
              />
            ) : (
              <button
                onClick={() => mediaUrl && setPlayingIdx(i)}
                className={cn('w-full aspect-video bg-muted/50 flex items-center justify-center', mediaUrl ? 'cursor-pointer hover:bg-muted transition-colors' : 'cursor-default')}
              >
                {mediaUrl ? (
                  <div className="flex flex-col items-center gap-1 text-muted-foreground">
                    <div className="rounded-full bg-purple-500/10 p-3"><Clapperboard className="h-6 w-6 text-purple-500" /></div>
                    <span className="text-xs">Click to play scene</span>
                  </div>
                ) : (
                  <Clapperboard className="h-8 w-8 text-muted-foreground/40" />
                )}
              </button>
            )}
            <div className="p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">Scene {i + 1}: {s.scene_start.toFixed(1)}s &ndash; {s.scene_end.toFixed(1)}s</span>
                <span className="text-xs text-muted-foreground">{formatDuration(duration)}</span>
              </div>
              <div className="flex items-center gap-2">
                {s.site_name && <span className="text-xs text-muted-foreground">{s.site_name}</span>}
                {s.camera_id && <Badge variant="default" className="text-[10px]">{s.camera_id}</Badge>}
                <span className="text-xs text-muted-foreground ml-auto truncate max-w-32">{s.source}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Audio list
// ---------------------------------------------------------------------------

function AudioList() {
  const [chunks, setChunks] = useState<BrowseAudioItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    api.browseAudio({ limit: 60 }).then(setChunks).catch(() => {}).finally(() => setIsLoading(false))
  }, [])

  if (isLoading) return <div className="flex items-center justify-center py-12 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin mr-2" />Loading audio chunks...</div>
  if (!chunks.length) return <div className="text-center text-muted-foreground py-12 text-sm">No audio chunks found. Upload videos with audio to generate chunks.</div>

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {chunks.map((c, i) => (
        <div key={i} className="rounded-lg border bg-card overflow-hidden">
          {c.audio_url ? (
            <div className="bg-muted/30 px-4 py-3 border-b">
              <audio controls preload="none" className="w-full h-8" src={c.audio_url}><track kind="captions" /></audio>
            </div>
          ) : (
            <div className="bg-muted/30 px-4 py-3 border-b flex items-center justify-center text-muted-foreground">
              <AudioLines className="h-5 w-5 mr-2" /><span className="text-xs">No audio file</span>
            </div>
          )}
          <div className="p-3 space-y-2">
            {c.transcription ? (
              <div className="text-sm text-muted-foreground line-clamp-4"><FormattedText text={c.transcription} className="text-sm" /></div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No transcription available</p>
            )}
            <div className="flex items-center gap-2">
              {c.site_name && <span className="text-xs text-muted-foreground">{c.site_name}</span>}
              {c.camera_id && <Badge variant="default" className="text-[10px]">{c.camera_id}</Badge>}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
