import { useState, useEffect, useCallback } from 'react'
import {
  Video, ShieldAlert, MapPin, RefreshCw, Frame, Layers, AudioLines, FileText,
  Activity, AlertTriangle, DollarSign, Clock, Tags,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatCard } from '@/components/ui/stat-card'
import { SeverityBadge } from '@/components/ui/severity-badge'

import * as api from '@/lib/api'
import type { DashboardStats, AlertItem, ActivityItem } from '@/types'

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [statsData, alertsData, activityData] = await Promise.all([
        api.getDashboardStats(),
        api.getDashboardAlerts({ limit: 20 }),
        api.getDashboardActivity(15),
      ])
      setStats(statsData)
      setAlerts(alertsData.alerts)
      setActivity(activityData)
    } catch {
      /* empty */
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex items-center justify-between px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Operations Overview</h2>
          <p className="text-sm text-muted-foreground">Asset monitoring, condition-based maintenance insights &amp; ROI</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} disabled={isLoading}>
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* ROI stat cards -- 6 columns */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 px-6">
        <StatCard
          label="Remote Inspections"
          value={stats?.total_videos ?? 0}
          icon={Video}
          accent="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
        />
        <StatCard
          label="Anomalies Detected"
          value={stats?.anomalies_detected ?? 0}
          icon={AlertTriangle}
          accent="bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400"
        />
        <StatCard
          label="Critical Alerts"
          value={stats?.critical_alerts ?? 0}
          icon={ShieldAlert}
          accent="bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
        />
        <StatCard
          label="Sites Monitored"
          value={stats?.sites_monitored ?? 0}
          icon={MapPin}
          accent="bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
        />
        <StatCard
          label="Est. Truck Rolls Saved"
          value={`$${((stats?.est_cost_savings ?? 0) / 1000).toFixed(1)}k`}
          icon={DollarSign}
          accent="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
        />
        <StatCard
          label="Mean Time to Detect"
          value={`${((stats?.avg_processing_time ?? 0)).toFixed(0)}s`}
          icon={Clock}
          accent="bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 px-6 py-6 flex-1 min-h-0">
        {/* Severity breakdown */}
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-semibold mb-3">Severity Breakdown</h3>
          {stats?.severity_counts ? (
            <div className="space-y-3">
              {Object.entries(stats.severity_counts).map(([sev, count]) => (
                <div key={sev} className="flex items-center justify-between">
                  <SeverityBadge severity={sev} />
                  <div className="flex items-center gap-2 flex-1 mx-3">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          sev === 'critical'
                            ? 'bg-red-500'
                            : sev === 'warning'
                              ? 'bg-orange-500'
                              : 'bg-blue-500'
                        }`}
                        style={{
                          width: `${stats.total_segments > 0 ? (count / stats.total_segments) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No data yet</p>
          )}
        </div>

        {/* Top Detected Objects */}
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
            <Tags className="h-3.5 w-3.5 text-emerald-500" />
            Top Detected Objects
          </h3>
          {stats?.top_labels && stats.top_labels.length > 0 ? (
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {stats.top_labels.map((item) => (
                <div key={item.label} className="flex items-center justify-between p-1.5 rounded bg-muted/50 text-xs">
                  <span className="font-medium capitalize">{item.label}</span>
                  <span className="text-muted-foreground font-mono">{item.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Upload videos &mdash; DETR panoptic segmentation runs automatically on every frame.
              </p>
              <p className="text-[10px] text-muted-foreground">
                pixeltable.functions.huggingface.detr_for_segmentation
              </p>
            </div>
          )}
        </div>

        {/* Sites & transcripts */}
        <div className="rounded-lg border bg-card p-4 space-y-4">
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-primary" />
              Sites Monitored
            </h3>
            {stats?.sites && stats.sites.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {stats.sites.map((site) => (
                  <span key={site} className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
                    {site}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No sites yet</p>
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold mb-2">Recent Transcripts</h3>
            {stats?.recent_transcripts && stats.recent_transcripts.length > 0 ? (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {stats.recent_transcripts.map((text, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs p-2 rounded bg-muted/50">
                    <FileText className="h-3 w-3 text-amber-500 shrink-0 mt-0.5" />
                    <span className="text-muted-foreground line-clamp-2">{text}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No transcripts yet</p>
            )}
          </div>
        </div>

        {/* Recent alerts */}
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-semibold mb-3">Recent Alerts</h3>
          {alerts.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {alerts.slice(0, 10).map((alert, i) => (
                <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/50">
                  <ShieldAlert className="h-3.5 w-3.5 mt-0.5 shrink-0 text-red-500" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <SeverityBadge severity={alert.severity} />
                      {alert.site_name && (
                        <span className="text-[10px] text-muted-foreground">{alert.site_name}</span>
                      )}
                    </div>
                    {alert.frame_description && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {alert.frame_description}
                      </p>
                    )}
                    {alert.severity_reason && (
                      <p className="text-[10px] text-muted-foreground/70 truncate">{alert.severity_reason}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No alerts detected yet</p>
          )}
        </div>

        {/* Processing activity */}
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-primary" />
            Processing Activity
          </h3>
          {activity.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {activity.map((item, i) => {
                const iconMap: Record<string, typeof Video> = {
                  upload: Video,
                  analysis: Frame,
                  segments: Layers,
                  audio: AudioLines,
                }
                const IconComp = iconMap[item.type] ?? Activity
                return (
                  <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/50">
                    <IconComp className="h-3.5 w-3.5 mt-0.5 shrink-0 text-primary/70" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium">{item.label}</p>
                      {item.detail && (
                        <p className="text-[10px] text-muted-foreground">{item.detail}</p>
                      )}
                      <div className="flex items-center gap-2 mt-0.5">
                        {item.site_name && (
                          <span className="text-[10px] text-muted-foreground">{item.site_name}</span>
                        )}
                        {item.timestamp && (
                          <span className="text-[10px] text-muted-foreground/60">
                            {new Date(item.timestamp).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No activity yet</p>
          )}
        </div>
      </div>

    </div>
  )
}
