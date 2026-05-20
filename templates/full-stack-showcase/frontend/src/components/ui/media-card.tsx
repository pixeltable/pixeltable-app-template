import { cn, toDataUrl } from '@/lib/utils'
import { SeverityBadge } from './severity-badge'

interface MediaCardProps {
  thumbnail?: string | null
  title?: string
  subtitle?: string
  severity?: string | null
  labels?: string[] | null
  similarity?: number | null
  onClick?: () => void
  className?: string
}

export function MediaCard({
  thumbnail,
  title,
  subtitle,
  severity,
  labels,
  similarity,
  onClick,
  className,
}: MediaCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-card overflow-hidden transition-shadow hover:shadow-md',
        onClick && 'cursor-pointer',
        className,
      )}
      onClick={onClick}
    >
      {thumbnail && (
        <div className="relative">
          <img
            src={toDataUrl(thumbnail)}
            alt={title ?? 'frame'}
            className="w-full aspect-video object-cover"
          />
          {severity && severity !== 'info' && (
            <div className="absolute top-1.5 right-1.5">
              <SeverityBadge severity={severity} />
            </div>
          )}
          {similarity != null && (
            <div className="absolute bottom-1.5 left-1.5 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
              {(similarity * 100).toFixed(0)}% match
            </div>
          )}
        </div>
      )}
      <div className="p-2.5">
        {title && <p className="text-sm font-medium truncate">{title}</p>}
        {subtitle && <p className="text-xs text-muted-foreground truncate mt-0.5">{subtitle}</p>}
        {labels && labels.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {labels.slice(0, 4).map((l) => (
              <span key={l} className="text-[10px] bg-muted px-1.5 py-0.5 rounded">
                {l}
              </span>
            ))}
            {labels.length > 4 && (
              <span className="text-[10px] text-muted-foreground">+{labels.length - 4}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
