import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  accent?: string
  className?: string
}

export function StatCard({ label, value, icon: Icon, accent, className }: StatCardProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4 flex items-start gap-3', className)}>
      <div className={cn('rounded-md p-2', accent ?? 'bg-primary/10 text-primary')}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}
