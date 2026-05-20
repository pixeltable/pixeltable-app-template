import { useState, useEffect, useCallback } from 'react'
import { ShieldAlert, RefreshCw, Loader2, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SeverityBadge } from '@/components/ui/severity-badge'
import { cn, toDataUrl } from '@/lib/utils'
import * as api from '@/lib/api'
import type { AlertItem } from '@/types'

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState('')
  const [siteFilter, setSiteFilter] = useState('')

  const loadAlerts = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.getDashboardAlerts({
        severity: severityFilter || undefined,
        site_name: siteFilter || undefined,
        limit: 100,
      })
      setAlerts(data.alerts)
    } catch {
      /* empty */
    } finally {
      setIsLoading(false)
    }
  }, [severityFilter, siteFilter])

  useEffect(() => {
    loadAlerts()
  }, [loadAlerts])

  const sites = [...new Set(alerts.map((a) => a.site_name).filter(Boolean))] as string[]

  const handleExport = () => {
    const csv = [
      'severity,site,camera,labels',
      ...alerts.map(
        (a) =>
          `${a.severity},${a.site_name ?? ''},${a.camera_id ?? ''},"${a.segment_labels.join(', ')}"`,
      ),
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'alerts-export.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h2 className="text-lg font-semibold">Safety &amp; Compliance Alerts</h2>
          <p className="text-sm text-muted-foreground">
            {alerts.length} anomalies detected across all inspection footage
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport} disabled={!alerts.length}>
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={loadAlerts} disabled={isLoading}>
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 px-6 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Severity:</span>
          {['', 'critical', 'warning', 'info'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={cn(
                'text-xs px-2 py-1 rounded-md cursor-pointer transition-colors',
                severityFilter === sev
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-accent',
              )}
            >
              {sev || 'All'}
            </button>
          ))}
        </div>

        {sites.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Site:</span>
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
      </div>

      {/* Alert feed */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading alerts...
          </div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-12">
            <ShieldAlert className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No alerts detected</p>
            <p className="text-xs text-muted-foreground mt-1">
              Upload surveillance videos and the analysis pipeline will detect potential issues
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {alerts.map((alert, i) => (
              <AlertCard key={i} alert={alert} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function AlertCard({ alert }: { alert: AlertItem }) {
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      {alert.frame && (
        <div className="relative">
          <img
            src={toDataUrl(alert.frame)}
            alt="Alert frame"
            className="w-full aspect-video object-cover"
          />
          <div className="absolute top-1.5 right-1.5">
            <SeverityBadge severity={alert.severity} />
          </div>
        </div>
      )}
      <div className="p-3 space-y-1.5">
        {alert.segment_labels.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {alert.segment_labels.map((l) => (
              <span key={l} className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-medium">
                {l}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {alert.site_name && <span>{alert.site_name}</span>}
          {alert.camera_id && <span>&middot; {alert.camera_id}</span>}
        </div>
        {alert.frame_description && (
          <p className="text-xs text-muted-foreground line-clamp-2">{alert.frame_description}</p>
        )}
      </div>
    </div>
  )
}
