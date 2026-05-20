import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Upload, Video, Trash2, ChevronDown, ChevronUp, Loader2,
  MapPin, Camera, Clock, Tag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SeverityBadge } from '@/components/ui/severity-badge'
import { cn, toDataUrl, formatDuration } from '@/lib/utils'
import { FormattedText } from '@/components/ui/formatted-text'
import * as api from '@/lib/api'
import type { VideoItem, FrameItem, SceneItem } from '@/types'

export function VideosPage() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [expandedUuid, setExpandedUuid] = useState<string | null>(null)
  const [siteFilter, setSiteFilter] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Upload form state
  const [siteName, setSiteName] = useState('Default Site')
  const [cameraId, setCameraId] = useState('CAM-01')
  const [location, setLocation] = useState('')
  const [assetId, setAssetId] = useState('XFMR-SUB-B-014')
  const [gpsLat, setGpsLat] = useState('37.7749')
  const [gpsLon, setGpsLon] = useState('-122.4194')
  const [tags, setTags] = useState('')

  const loadVideos = useCallback(async () => {
    try {
      const data = await api.getVideos(siteFilter || undefined)
      setVideos(data)
    } catch {
      /* empty */
    }
  }, [siteFilter])

  useEffect(() => {
    loadVideos()
  }, [loadVideos])

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList?.length) return
    setIsUploading(true)
    try {
      for (const file of Array.from(fileList)) {
        await api.uploadVideo(file, {
          site_name: siteName,
          camera_id: cameraId,
          location,
          asset_id: assetId,
          gps_lat: gpsLat,
          gps_lon: gpsLon,
          tags,
        })
      }
      await loadVideos()
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setIsUploading(false)
    }
  }

  const handleDelete = async (uuid: string) => {
    try {
      await api.deleteVideo(uuid)
      await loadVideos()
      if (expandedUuid === uuid) setExpandedUuid(null)
    } catch {
      /* empty */
    }
  }

  const sites = [...new Set(videos.map((v) => v.site_name).filter(Boolean))]

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Upload zone */}
      <div className="m-4 mb-2 border-2 border-dashed rounded-lg p-4">
        <p className="text-xs font-medium text-muted-foreground mb-1">Upload Inspection Footage</p>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-3">
          <input
            type="text"
            placeholder="Site name"
            value={siteName}
            onChange={(e) => setSiteName(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="Camera ID"
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="Asset ID"
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="GPS Lat"
            value={gpsLat}
            onChange={(e) => setGpsLat(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="GPS Lon"
            value={gpsLon}
            onChange={(e) => setGpsLon(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <input
            type="text"
            placeholder="Tags (comma-separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <div
            className="border-2 border-dashed rounded-md flex items-center justify-center gap-2 text-sm text-muted-foreground hover:border-primary/50 transition-colors cursor-pointer py-1.5"
            onDragOver={(e) => {
              e.preventDefault()
              e.stopPropagation()
            }}
            onDrop={(e) => {
              e.preventDefault()
              e.stopPropagation()
              handleUpload(e.dataTransfer.files)
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload Videos
              </>
            )}
          </div>
        </div>
      </div>

      {/* Site filter */}
      {sites.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2">
          <span className="text-xs text-muted-foreground">Filter by site:</span>
          <button
            onClick={() => setSiteFilter('')}
            className={cn(
              'text-xs px-2 py-1 rounded-md cursor-pointer transition-colors',
              !siteFilter ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-accent',
            )}
          >
            All
          </button>
          {sites.map((site) => (
            <button
              key={site}
              onClick={() => setSiteFilter(site)}
              className={cn(
                'text-xs px-2 py-1 rounded-md cursor-pointer transition-colors',
                siteFilter === site
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-accent',
              )}
            >
              {site}
            </button>
          ))}
        </div>
      )}

      {/* Video list */}
      <div className="flex-1 px-4 pb-4 space-y-1">
        {videos.length === 0 ? (
          <div className="text-center text-muted-foreground text-sm py-12">
            No videos uploaded yet. Upload surveillance footage to get started.
          </div>
        ) : (
          videos.map((v) => (
            <VideoRow
              key={v.uuid}
              video={v}
              isExpanded={expandedUuid === v.uuid}
              onToggle={() => setExpandedUuid(expandedUuid === v.uuid ? null : v.uuid)}
              onDelete={() => handleDelete(v.uuid)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function VideoRow({
  video,
  isExpanded,
  onToggle,
  onDelete,
}: {
  video: VideoItem
  isExpanded: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <div className="border rounded-lg">
      <div
        className="flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-accent/50 transition-colors"
        onClick={onToggle}
      >
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0" />
        )}
        <Video className="h-4 w-4 shrink-0 text-primary" />
        <span className="text-sm font-medium truncate flex-1">{video.name}</span>

        <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {video.site_name}
          </span>
          <span className="flex items-center gap-1">
            <Camera className="h-3 w-3" />
            {video.camera_id}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDuration(video.duration)}
          </span>
          {video.tags && video.tags.length > 0 && (
            <span className="flex items-center gap-1">
              <Tag className="h-3 w-3" />
              {video.tags.length}
            </span>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
        >
          <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
      </div>

      {isExpanded && (
        <div className="border-t px-4 py-3">
          <VideoDetail uuid={video.uuid} />
        </div>
      )}
    </div>
  )
}

function VideoDetail({ uuid }: { uuid: string }) {
  const [frames, setFrames] = useState<FrameItem[]>([])
  const [scenes, setScenes] = useState<SceneItem[]>([])
  const [transcription, setTranscription] = useState('')
  const [summary, setSummary] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    Promise.all([
      api.getFrames(uuid).catch(() => ({ frames: [] })),
      api.getScenes(uuid).catch(() => ({ scenes: [] })),
      api.getTranscription(uuid).catch(() => ({ full_text: '' })),
      api.getVideoDetail(uuid).catch(() => ({ video_summary: '' })),
    ])
      .then(([f, sc, t, d]) => {
        setFrames('frames' in f ? f.frames : [])
        setScenes('scenes' in sc ? sc.scenes : [])
        setTranscription('full_text' in t ? t.full_text : '')
        setSummary(d.video_summary ?? '')
      })
      .finally(() => setIsLoading(false))
  }, [uuid])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading video analysis...
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Gemini video summary */}
      {summary && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Gemini Video Analysis
          </div>
          <div className="bg-muted/50 rounded-lg p-4 border">
            <FormattedText text={summary} className="text-sm" />
          </div>
        </div>
      )}

      {/* Keyframes with segmentation */}
      {frames.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Frames ({frames.length}) &mdash; DETR Panoptic Segmentation
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {frames.map((f, i) => (
              <div key={i} className="relative group">
                <img
                  src={toDataUrl(f.frame)}
                  alt={`Frame ${i}`}
                  className="w-full aspect-video object-cover rounded border"
                />
                {f.severity && f.severity !== 'info' && (
                  <div className="absolute top-0.5 right-0.5">
                    <SeverityBadge severity={f.severity} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenes */}
      {scenes.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Scenes ({scenes.length}) &mdash; PySceneDetect
          </div>
          <div className="flex flex-wrap gap-2">
            {scenes.map((s, i) => (
              <Badge key={i} variant="purple">
                {s.scene_start.toFixed(1)}s &ndash; {s.scene_end.toFixed(1)}s
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Transcription */}
      {transcription && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Transcription &mdash; Whisper
          </div>
          <div className="bg-muted/50 rounded-lg p-4 border max-h-48 overflow-y-auto">
            <FormattedText text={transcription} className="text-xs" />
          </div>
        </div>
      )}

      {!frames.length && !scenes.length && !transcription && !summary && (
        <div className="text-sm text-muted-foreground">
          Processing... Pixeltable is running the analysis pipeline. Check back shortly.
        </div>
      )}
    </div>
  )
}
