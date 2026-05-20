import { Badge } from './badge'

const severityConfig: Record<string, { variant: 'red' | 'orange' | 'blue'; label: string }> = {
  critical: { variant: 'red', label: 'Critical' },
  warning: { variant: 'orange', label: 'Warning' },
  info: { variant: 'blue', label: 'Info' },
}

interface SeverityBadgeProps {
  severity: string | null | undefined
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = severityConfig[severity ?? 'info'] ?? severityConfig.info
  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  )
}
