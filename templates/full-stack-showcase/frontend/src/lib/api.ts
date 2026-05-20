import type {
  VideoItem,
  VideoDetail,
  FramesResponse,
  ScenesResponse,
  TranscriptionResponse,
  SearchResponse,
  DashboardStats,
  AlertsResponse,
  ActivityItem,
  BrowseFrameItem,
  BrowseSegmentItem,
  BrowseSceneItem,
  BrowseAudioItem,
  BrowseDetectionItem,
} from '@/types'

const BASE = '/api'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? body.error ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// -- Videos ----------------------------------------------------------------

export async function uploadVideo(file: File, metadata: {
  site_name: string
  camera_id: string
  location: string
  asset_id: string
  gps_lat: string
  gps_lon: string
  tags: string
}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('site_name', metadata.site_name)
  formData.append('camera_id', metadata.camera_id)
  formData.append('location', metadata.location)
  formData.append('asset_id', metadata.asset_id)
  formData.append('gps_lat', metadata.gps_lat)
  formData.append('gps_lon', metadata.gps_lon)
  formData.append('tags', metadata.tags)
  const res = await fetch(`${BASE}/videos/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getVideos(siteName?: string): Promise<VideoItem[]> {
  const params = siteName ? `?site_name=${encodeURIComponent(siteName)}` : ''
  return request<VideoItem[]>(`${BASE}/videos${params}`)
}

export async function getVideoDetail(uuid: string): Promise<VideoDetail> {
  return request<VideoDetail>(`${BASE}/videos/${uuid}`)
}

export async function deleteVideo(uuid: string) {
  return request<{ message: string }>(`${BASE}/videos/${uuid}`, { method: 'DELETE' })
}

export async function getFrames(uuid: string, limit = 24): Promise<FramesResponse> {
  return request<FramesResponse>(`${BASE}/videos/${uuid}/frames?limit=${limit}`)
}

export async function getScenes(uuid: string): Promise<ScenesResponse> {
  return request<ScenesResponse>(`${BASE}/videos/${uuid}/scenes`)
}

export async function getTranscription(uuid: string): Promise<TranscriptionResponse> {
  return request<TranscriptionResponse>(`${BASE}/videos/${uuid}/transcription`)
}

// -- Search ----------------------------------------------------------------

export async function searchText(params: {
  query: string
  types?: string[]
  limit?: number
}): Promise<SearchResponse> {
  return request<SearchResponse>(`${BASE}/search`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function searchByImage(file: File, limit = 20): Promise<SearchResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('limit', String(limit))
  const res = await fetch(`${BASE}/search/by-image`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function searchByVideo(file: File, limit = 20): Promise<SearchResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('limit', String(limit))
  const res = await fetch(`${BASE}/search/by-video`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function searchByAudio(file: File, limit = 20): Promise<SearchResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('limit', String(limit))
  const res = await fetch(`${BASE}/search/by-audio`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getRelatedEvents(params: {
  type: string
  text?: string
  video_url?: string
  uuid?: string
  limit?: number
}): Promise<SearchResponse> {
  return request<SearchResponse>(`${BASE}/search/related`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

// -- Dashboard -------------------------------------------------------------

export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>(`${BASE}/dashboard/stats`)
}

export async function getDashboardAlerts(params?: {
  severity?: string
  site_name?: string
  limit?: number
}): Promise<AlertsResponse> {
  const searchParams = new URLSearchParams()
  if (params?.severity) searchParams.set('severity', params.severity)
  if (params?.site_name) searchParams.set('site_name', params.site_name)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  const qs = searchParams.toString()
  return request<AlertsResponse>(`${BASE}/dashboard/alerts${qs ? `?${qs}` : ''}`)
}

export async function getDashboardActivity(limit = 20): Promise<ActivityItem[]> {
  return request<ActivityItem[]>(`${BASE}/dashboard/activity?limit=${limit}`)
}

// -- Browse ----------------------------------------------------------------

export async function browseDetections(params?: {
  site_name?: string
  label?: string
  limit?: number
  offset?: number
}): Promise<BrowseDetectionItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.site_name) searchParams.set('site_name', params.site_name)
  if (params?.label) searchParams.set('label', params.label)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<BrowseDetectionItem[]>(`${BASE}/browse/detections${qs ? `?${qs}` : ''}`)
}

export async function browseFrames(params?: {
  site_name?: string
  limit?: number
  offset?: number
}): Promise<BrowseFrameItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.site_name) searchParams.set('site_name', params.site_name)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<BrowseFrameItem[]>(`${BASE}/browse/frames${qs ? `?${qs}` : ''}`)
}

export async function browseSegments(params?: {
  site_name?: string
  severity?: string
  alerts_only?: boolean
  limit?: number
  offset?: number
}): Promise<BrowseSegmentItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.site_name) searchParams.set('site_name', params.site_name)
  if (params?.severity) searchParams.set('severity', params.severity)
  if (params?.alerts_only) searchParams.set('alerts_only', 'true')
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<BrowseSegmentItem[]>(`${BASE}/browse/segments${qs ? `?${qs}` : ''}`)
}

export async function browseAudio(params?: {
  site_name?: string
  limit?: number
  offset?: number
}): Promise<BrowseAudioItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.site_name) searchParams.set('site_name', params.site_name)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<BrowseAudioItem[]>(`${BASE}/browse/audio${qs ? `?${qs}` : ''}`)
}

export async function browseScenes(params?: {
  limit?: number
  offset?: number
}): Promise<BrowseSceneItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return request<BrowseSceneItem[]>(`${BASE}/browse/scenes${qs ? `?${qs}` : ''}`)
}

