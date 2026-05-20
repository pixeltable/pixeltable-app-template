// -- Videos ----------------------------------------------------------------

export interface VideoItem {
  uuid: string
  name: string
  site_name: string
  camera_id: string
  location: string
  asset_id: string | null
  gps_lat: number | null
  gps_lon: number | null
  duration: number | null
  recorded_at: string | null
  timestamp: string | null
  tags: string[] | null
  video_summary: string | null
  alert_count: number
}

export interface VideoDetail {
  uuid: string
  name: string
  site_name: string
  camera_id: string
  location: string
  asset_id: string | null
  gps_lat: number | null
  gps_lon: number | null
  duration: number | null
  recorded_at: string | null
  tags: string[] | null
  video_summary: string | null
  metadata: Record<string, unknown> | null
}

// -- Frames ----------------------------------------------------------------

export interface FrameItem {
  frame: string
}

export interface FramesResponse {
  uuid: string
  frames: FrameItem[]
  total: number
}

// -- Segments --------------------------------------------------------------

export interface SegmentItem {
  segment_start: number
  segment_end: number
  uuid: string
}

export interface SegmentsResponse {
  uuid: string
  segments: SegmentItem[]
  total: number
}

// -- Scenes ----------------------------------------------------------------

export interface SceneItem {
  scene_start: number
  scene_end: number
}

export interface ScenesResponse {
  uuid: string
  scenes: SceneItem[]
  total: number
}

// -- Transcription ---------------------------------------------------------

export interface TranscriptionResponse {
  uuid: string
  sentences: string[]
  full_text: string
}

// -- Search ----------------------------------------------------------------

export interface SearchResult {
  type: 'video_segment' | 'frame' | 'transcript'
  uuid: string
  similarity: number
  text?: string
  thumbnail?: string | null
  video_url?: string | null
  metadata?: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
}

// -- Dashboard -------------------------------------------------------------

export interface DashboardStats {
  total_videos: number
  total_frames: number
  total_segments: number
  total_audio_chunks: number
  total_transcripts: number
  total_alerts: number
  anomalies_detected: number
  critical_alerts: number
  sites_monitored: number
  est_cost_savings: number
  avg_processing_time: number
  sites: string[]
  severity_counts: Record<string, number>
  recent_transcripts: string[]
  top_labels: LabelCount[]
}

export interface AlertItem {
  uuid: string
  frame: string
  segment_labels: string[]
  severity: string
  frame_description: string | null
  site_name: string | null
  camera_id: string | null
  video_url: string | null
  severity_reason: string | null
  timestamp: string | null
}

export interface AlertsResponse {
  alerts: AlertItem[]
  total: number
}

// -- Browse ----------------------------------------------------------------

export interface BrowseFrameItem {
  uuid: string
  frame: string
  site_name: string | null
  camera_id: string | null
  asset_id: string | null
}

export interface BrowseDetectionItem {
  uuid: string
  segmentation_overlay: string
  detected_labels: string[]
  segments_info: Array<{
    id: number
    label_id: number
    label_text: string
    score: number
    was_fused: boolean
  }>
  site_name: string | null
  camera_id: string | null
  asset_id: string | null
}

export interface LabelCount {
  label: string
  count: number
}

export interface BrowseSegmentItem {
  uuid: string
  segment_start: number
  segment_end: number
  video_url: string | null
  description: string | null
  severity: string | null
  severity_reason: string | null
  ppe_status: string | null
  ppe_details: string | null
  equipment: string[]
  hazards: string[]
  site_name: string | null
  camera_id: string | null
  asset_id: string | null
}

export interface BrowseSceneItem {
  uuid: string
  scene_start: number
  scene_end: number
  source: string
  video_url: string | null
  site_name: string | null
  camera_id: string | null
}

export interface BrowseAudioItem {
  uuid: string
  audio_url: string | null
  duration: number | null
  transcription: string | null
  site_name: string | null
  camera_id: string | null
}

// -- Activity ---------------------------------------------------------------

export interface ActivityItem {
  type: string
  label: string
  detail: string | null
  site_name: string | null
  timestamp: string | null
}
