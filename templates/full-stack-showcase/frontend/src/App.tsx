import { useState } from 'react'
import { LayoutDashboard, Video, Layers, Search, ShieldAlert, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DashboardPage } from '@/components/dashboard/dashboard-page'
import { VideosPage } from '@/components/videos/videos-page'
import { BrowsePage } from '@/components/browse/browse-page'
import { SearchPage } from '@/components/search/search-page'
import { AlertsPage } from '@/components/alerts/alerts-page'

const TABS = [
  { id: 'dashboard', label: 'Operations', icon: LayoutDashboard },
  { id: 'videos', label: 'Inspections', icon: Video },
  { id: 'browse', label: 'Browse', icon: Layers },
  { id: 'search', label: 'Investigate', icon: Search },
  { id: 'alerts', label: 'Alerts', icon: ShieldAlert },
] as const

type TabId = (typeof TABS)[number]['id']

const STACK_ITEMS = [
  {
    label: 'Pixeltable',
    role: 'Data Infrastructure',
    lines: '~370 lines',
    url: 'https://github.com/pixeltable/pixeltable',
  },
  {
    label: 'FastAPI',
    role: 'Backend API',
    lines: '~1,120 lines',
    url: 'https://fastapi.tiangolo.com',
  },
  {
    label: 'Gemini',
    role: 'LLM + Embeddings',
    url: 'https://ai.google.dev',
  },
  {
    label: 'DETR',
    role: 'Computer Vision',
    url: 'https://huggingface.co/facebook/detr-resnet-50-panoptic',
  },
]

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between border-b px-6 h-14 shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <div>
              <h1 className="text-base font-semibold tracking-tight leading-none">SiteWatch</h1>
              <p className="text-[10px] text-muted-foreground leading-none mt-0.5">AI-Powered Asset Monitoring &amp; Compliance</p>
            </div>
          </div>

          <nav className="flex items-center gap-1 bg-muted rounded-lg p-1">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer',
                  activeTab === id
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>
        </div>

        <a
          href="https://github.com/pixeltable/pixeltable"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Powered by Pixeltable
          <ExternalLink className="h-3 w-3" />
        </a>
      </header>

      <main className="flex-1 overflow-hidden">
        {activeTab === 'dashboard' && <DashboardPage />}
        {activeTab === 'videos' && <VideosPage />}
        {activeTab === 'browse' && <BrowsePage />}
        {activeTab === 'search' && <SearchPage />}
        {activeTab === 'alerts' && <AlertsPage />}
      </main>

      <footer className="border-t bg-card/50 px-6 py-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <span className="font-medium text-foreground/70 mr-1">Built with</span>
            {STACK_ITEMS.map((item, i) => (
              <span key={item.label} className="flex items-center">
                {i > 0 && <span className="mx-1.5 text-muted-foreground/40">|</span>}
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
                >
                  <span className="font-medium text-foreground/80">{item.label}</span>
                  <span className="text-muted-foreground/60">{item.role}</span>
                  {'lines' in item && (
                    <span className="text-primary/70 font-mono text-[10px]">{item.lines}</span>
                  )}
                </a>
              </span>
            ))}
          </div>
          <span className="text-[10px] text-muted-foreground/50">
            Condition-Based Maintenance &middot; Digital Twin &middot; Single Source of Truth
          </span>
        </div>
      </footer>
    </div>
  )
}
