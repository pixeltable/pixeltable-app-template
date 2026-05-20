import { useState, useRef, useEffect } from 'react'
import {
  Search, ImageIcon, Video, FileText, Film, AudioLines, Loader2,
  Upload, Play, ArrowLeft, MapPin, Camera, Clock, Tag, Hash, ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SeverityBadge } from '@/components/ui/severity-badge'
import { cn, toDataUrl } from '@/lib/utils'
import * as api from '@/lib/api'
import type { SearchResult } from '@/types'

type SearchMode = 'text' | 'image' | 'video' | 'audio'

const TYPE_OPTIONS = [
  { id: 'video_segment', label: 'Video Segments', icon: Film },
  { id: 'frame', label: 'Frames', icon: ImageIcon },
  { id: 'transcript', label: 'Transcripts', icon: FileText },
]

export function SearchPage() {
  const [mode, setMode] = useState<SearchMode>('text')
  const [query, setQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState(['video_segment', 'frame', 'transcript'])
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchInfo, setSearchInfo] = useState('')
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)
  const [relatedEvents, setRelatedEvents] = useState<SearchResult[]>([])
  const [isLoadingRelated, setIsLoadingRelated] = useState(false)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const videoInputRef = useRef<HTMLInputElement>(null)
  const audioInputRef = useRef<HTMLInputElement>(null)

  const toggleType = (typeId: string) => {
    setSelectedTypes((prev) =>
      prev.includes(typeId) ? prev.filter((t) => t !== typeId) : [...prev, typeId],
    )
  }

  useEffect(() => {
    if (!selectedResult) {
      setRelatedEvents([])
      return
    }
    let cancelled = false
    setIsLoadingRelated(true)
    api.getRelatedEvents({
      type: selectedResult.type,
      text: selectedResult.text ?? undefined,
      video_url: selectedResult.video_url ?? undefined,
      uuid: selectedResult.uuid,
      limit: 10,
    }).then((res) => {
      if (!cancelled) setRelatedEvents(res.results)
    }).catch(() => {
      if (!cancelled) setRelatedEvents([])
    }).finally(() => {
      if (!cancelled) setIsLoadingRelated(false)
    })
    return () => { cancelled = true }
  }, [selectedResult])

  const handleTextSearch = async () => {
    if (!query.trim()) return
    setIsSearching(true)
    setSelectedResult(null)
    try {
      const res = await api.searchText({ query, types: selectedTypes, limit: 30 })
      setResults(res.results)
      setSearchInfo(`${res.results.length} results for "${res.query}"`)
    } catch {
      setSearchInfo('Search failed')
    } finally {
      setIsSearching(false)
    }
  }

  const handleFileSearch = async (
    searchFn: (file: File, limit: number) => Promise<{ results: SearchResult[]; query: string }>,
    file: File,
    label: string,
  ) => {
    setIsSearching(true)
    setSelectedResult(null)
    try {
      const res = await searchFn(file, 30)
      setResults(res.results)
      setSearchInfo(`${res.results.length} results for ${label}: ${file.name}`)
    } catch {
      setSearchInfo(`${label} search failed`)
    } finally {
      setIsSearching(false)
    }
  }

  if (selectedResult) {
    return (
      <EventDetailView
        result={selectedResult}
        relatedEvents={relatedEvents}
        isLoadingRelated={isLoadingRelated}
        query={query}
        onBack={() => setSelectedResult(null)}
        onSelectRelated={(r) => setSelectedResult(r)}
      />
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Incident Investigation</h2>
          <p className="text-sm text-muted-foreground">
            Search your entire media archive by text, reference image, video, or audio.
            Click any result to see event details and discover related events across your archive.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Search by:</span>
          {([
            { id: 'text' as const, label: 'Text', icon: Search },
            { id: 'image' as const, label: 'Image', icon: ImageIcon },
            { id: 'video' as const, label: 'Video Clip', icon: Video },
            { id: 'audio' as const, label: 'Audio', icon: AudioLines },
          ]).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer',
                mode === id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-accent',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        {mode === 'text' && (
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder='Search all media... (e.g. "person near transformer", "vehicle at gate", "alarm sound")'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleTextSearch()}
                className="w-full border rounded-md pl-9 pr-3 py-2 text-sm bg-background"
              />
            </div>
            <Button onClick={handleTextSearch} disabled={isSearching || !query.trim()}>
              {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
            </Button>
          </div>
        )}

        {mode === 'image' && (
          <DropZone
            inputRef={imageInputRef}
            accept="image/*"
            isSearching={isSearching}
            searchingLabel="Searching frames & video segments by image..."
            icon={ImageIcon}
            label="Upload a reference image to find similar frames and video segments"
            sublabel="Cross-modal: image → frames + video segments via Gemini embeddings"
            onFile={(f) => handleFileSearch(api.searchByImage, f, 'image')}
          />
        )}

        {mode === 'video' && (
          <DropZone
            inputRef={videoInputRef}
            accept="video/*"
            isSearching={isSearching}
            searchingLabel="Searching segments & frames by video..."
            icon={Video}
            label="Upload a reference video clip to find similar segments and frames"
            sublabel="Cross-modal: video → video segments + frames via Gemini embeddings"
            onFile={(f) => handleFileSearch(api.searchByVideo, f, 'video')}
          />
        )}

        {mode === 'audio' && (
          <DropZone
            inputRef={audioInputRef}
            accept="audio/*"
            isSearching={isSearching}
            searchingLabel="Searching video segments by audio..."
            icon={AudioLines}
            label="Upload a reference audio clip to find matching video segments"
            sublabel="Cross-modal: audio → video segments via Gemini embeddings"
            onFile={(f) => handleFileSearch(api.searchByAudio, f, 'audio')}
          />
        )}

        {mode === 'text' && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Search in:</span>
            {TYPE_OPTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => toggleType(id)}
                className={cn(
                  'flex items-center gap-1 text-xs px-2 py-1 rounded-md cursor-pointer transition-colors',
                  selectedTypes.includes(id)
                    ? 'bg-primary/10 text-primary border border-primary/30'
                    : 'bg-muted text-muted-foreground',
                )}
              >
                <Icon className="h-3 w-3" />
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {searchInfo && (
          <p className="text-sm text-muted-foreground mb-4">{searchInfo}</p>
        )}

        {results.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {results.map((r, i) => (
              <SearchResultCard key={i} result={r} onClick={() => setSelectedResult(r)} />
            ))}
          </div>
        ) : !isSearching && searchInfo ? (
          <div className="text-center text-muted-foreground py-12 text-sm">
            No results found. Try a different query or search mode.
          </div>
        ) : !searchInfo ? (
          <div className="text-center text-muted-foreground py-12 text-sm">
            Enter a search query, upload a reference image, video clip, or audio file to search your surveillance footage.
          </div>
        ) : null}
      </div>
    </div>
  )
}


function EventDetailView({
  result,
  relatedEvents,
  isLoadingRelated,
  query,
  onBack,
  onSelectRelated,
}: {
  result: SearchResult
  relatedEvents: SearchResult[]
  isLoadingRelated: boolean
  query: string
  onBack: () => void
  onSelectRelated: (r: SearchResult) => void
}) {
  const meta = result.metadata ?? {}
  const typeLabel = result.type === 'video_segment' ? 'Video Segment'
    : result.type === 'frame' ? 'Frame' : 'Transcript'

  return (
    <div className="flex h-full">
      {/* Main event detail */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-3 border-b">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to results
          </button>
        </div>

        <div className="p-6 max-w-4xl mx-auto space-y-6">
          {/* Media */}
          {result.type === 'video_segment' && result.video_url ? (
            <video
              src={result.video_url}
              controls
              autoPlay
              className="w-full rounded-lg bg-black aspect-video"
            />
          ) : result.type === 'frame' && result.thumbnail ? (
            <img
              src={toDataUrl(result.thumbnail)}
              alt="Event frame"
              className="w-full rounded-lg object-cover max-h-[480px]"
            />
          ) : null}

          {/* Match + description */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="text-xs">
                {(result.similarity * 100).toFixed(0)}% match
              </Badge>
              {typeof meta.severity === 'string' && meta.severity !== 'info' && (
                <SeverityBadge severity={meta.severity as string} />
              )}
            </div>
            {result.text && (
              <p className="text-lg font-medium leading-snug">{result.text}</p>
            )}
          </div>

          {/* Event details grid */}
          <div className="border rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">Event Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <DetailCell
                icon={Tag}
                label="Type"
                value={typeLabel}
              />
              <DetailCell
                icon={Camera}
                label="Source"
                value={meta.source as string ?? meta.camera_id as string}
              />
              <DetailCell
                icon={MapPin}
                label="Site"
                value={meta.site_name as string}
              />
              <DetailCell
                icon={Clock}
                label="Duration"
                value={meta.duration ? `${meta.duration}s` : undefined}
              />
              <DetailCell
                icon={Hash}
                label="Event ID"
                value={result.uuid?.slice(0, 8).toUpperCase()}
              />
              <DetailCell
                icon={Camera}
                label="Camera"
                value={meta.camera_id as string}
              />
              {meta.segment_start != null && (
                <DetailCell
                  icon={Clock}
                  label="Time Range"
                  value={`${(meta.segment_start as number).toFixed(1)}s - ${(meta.segment_end as number).toFixed(1)}s`}
                />
              )}
            </div>
          </div>

          {/* Original query context */}
          {query && (
            <div className="flex items-center gap-2 border rounded-lg px-4 py-2.5 bg-muted/30">
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="text-sm text-muted-foreground">{query}</span>
            </div>
          )}
        </div>
      </div>

      {/* Related Events sidebar */}
      <div className="w-80 border-l bg-card/50 flex flex-col shrink-0">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h3 className="text-sm font-semibold">Related Events</h3>
          {relatedEvents.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {relatedEvents.length} found
            </span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoadingRelated ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : relatedEvents.length > 0 ? (
            <div className="divide-y">
              {relatedEvents.map((r, i) => (
                <RelatedEventCard key={i} result={r} onClick={() => onSelectRelated(r)} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-xs text-muted-foreground">
              No related events found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


function DetailCell({ icon: Icon, label, value }: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value?: string | null
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className="text-sm font-medium truncate">
        {value || '—'}
      </p>
    </div>
  )
}


function RelatedEventCard({ result, onClick }: { result: SearchResult; onClick: () => void }) {
  const meta = result.metadata ?? {}
  const similarity = (result.similarity * 100).toFixed(0)

  return (
    <button
      onClick={onClick}
      className="w-full flex gap-3 p-3 hover:bg-accent/50 transition-colors cursor-pointer text-left"
    >
      {/* Thumbnail / play indicator */}
      <div className="w-20 h-14 rounded bg-muted shrink-0 overflow-hidden relative">
        {result.type === 'frame' && result.thumbnail ? (
          <img src={toDataUrl(result.thumbnail)} alt="" className="w-full h-full object-cover" />
        ) : result.type === 'video_segment' ? (
          <div className="w-full h-full flex items-center justify-center">
            <Play className="h-4 w-4 text-muted-foreground" />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <FileText className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
        <div className="absolute top-1 left-1">
          <span className="text-[9px] font-bold bg-primary text-primary-foreground px-1 py-0.5 rounded">
            {similarity}%
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-[10px] text-muted-foreground">
          Related event
        </p>
        <p className="text-xs font-medium leading-tight line-clamp-2">
          {result.text || result.type}
        </p>
        {typeof meta.site_name === 'string' && (
          <p className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-0.5">
            <MapPin className="h-2.5 w-2.5" />
            {meta.site_name}
          </p>
        )}
      </div>

      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 self-center" />
    </button>
  )
}


function SearchResultCard({ result, onClick }: { result: SearchResult; onClick: () => void }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const meta = result.metadata ?? {}

  const typeLabel =
    result.type === 'video_segment'
      ? 'Video Segment'
      : result.type === 'frame'
        ? 'Frame'
        : 'Transcript'

  const typeVariant =
    result.type === 'video_segment'
      ? 'purple'
      : result.type === 'frame'
        ? 'blue'
        : ('green' as const)

  return (
    <div
      className="rounded-lg border bg-card overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/30 transition-all"
      onClick={onClick}
    >
      {result.type === 'video_segment' && result.video_url ? (
        isPlaying ? (
          <video
            src={result.video_url}
            controls
            autoPlay
            className="w-full aspect-video bg-black"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <button
            onClick={(e) => { e.stopPropagation(); setIsPlaying(true) }}
            className="w-full aspect-video bg-muted/50 flex items-center justify-center cursor-pointer hover:bg-muted transition-colors"
          >
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              <div className="rounded-full bg-primary/10 p-2">
                <Play className="h-5 w-5 text-primary fill-primary" />
              </div>
              <span className="text-[10px]">{result.text}</span>
            </div>
          </button>
        )
      ) : result.type === 'frame' && result.thumbnail ? (
        <img
          src={toDataUrl(result.thumbnail)}
          alt="frame"
          className="w-full aspect-video object-cover"
        />
      ) : null}

      <div className="p-3">
        <div className="flex items-center gap-2 mb-1">
          <Badge variant={typeVariant}>{typeLabel}</Badge>
          <span className="text-xs text-muted-foreground">
            {(result.similarity * 100).toFixed(0)}%
          </span>
          {typeof meta.severity === 'string' && meta.severity !== 'info' && (
            <SeverityBadge severity={meta.severity as string} />
          )}
        </div>

        {result.type === 'transcript' && result.text && (
          <p className="text-xs line-clamp-3 text-muted-foreground mt-1">{result.text}</p>
        )}

        {typeof meta.site_name === 'string' && (
          <p className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-0.5">
            <MapPin className="h-2.5 w-2.5 inline" />
            {meta.site_name}
          </p>
        )}

        {typeof meta.source === 'string' && (
          <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
            {meta.source}
          </p>
        )}
      </div>
    </div>
  )
}


function DropZone({
  inputRef,
  accept,
  isSearching,
  searchingLabel,
  icon: _Icon,
  label,
  sublabel,
  onFile,
}: {
  inputRef: React.RefObject<HTMLInputElement | null>
  accept: string
  isSearching: boolean
  searchingLabel: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  sublabel: string
  onFile: (file: File) => void
}) {
  return (
    <div
      className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
        }}
      />
      {isSearching ? (
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          {searchingLabel}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1 text-muted-foreground">
          <Upload className="h-6 w-6" />
          <span className="text-sm">{label}</span>
          <span className="text-xs">{sublabel}</span>
        </div>
      )}
    </div>
  )
}
