import { useEffect, useState } from 'react'
import { caseData, searchIndex } from './data/case'
import { SourceProvider } from './context/SourceContext'
import { Sidebar } from './components/Sidebar'
import type { PageId } from './components/Sidebar'
import { CaseHeader } from './components/CaseHeader'
import { SourceDrawer } from './components/SourceDrawer'
import { GlobalSearch } from './components/GlobalSearch'
import { Overview } from './pages/Overview'

const pageTitles: Record<PageId, string> = {
  overview: 'Overview',
  timeline: 'Timeline',
  people: 'People',
  financials: 'Financials',
  documents: 'Documents',
  tasks: 'Tasks',
  providers: 'Providers',
  'provider-portal': 'Provider Portal',
  settings: 'Settings',
}

export default function App() {
  const [page, setPage] = useState<PageId>('overview')
  const [searchOpen, setSearchOpen] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <SourceProvider>
      <div className="flex min-h-screen min-w-[1100px]">
        <Sidebar current={page} onNavigate={setPage} />
        <main className="min-w-0 flex-1">
          <div className="sticky top-0 z-30">
            <CaseHeader data={caseData} onSearch={() => setSearchOpen(true)} />
          </div>
          {page === 'overview' ? (
            <Overview onViewAllActivity={() => setPage('timeline')} />
          ) : (
            <Placeholder title={pageTitles[page]} onBack={() => setPage('overview')} />
          )}
        </main>
      </div>
      <SourceDrawer />
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} index={searchIndex} />
    </SourceProvider>
  )
}

function Placeholder({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="mx-auto max-w-[1400px] px-10 pt-8">
      <h1 className="text-[30px] leading-none font-semibold tracking-[-0.025em]">{title}</h1>
      <p className="mt-3 text-[13.5px] text-muted">
        This view is next on the build list.{' '}
        <button type="button" onClick={onBack} className="text-swan hover:underline">
          Back to Overview
        </button>
      </p>
    </div>
  )
}
