import {
  CalendarRange,
  CheckSquare,
  FileText,
  LayoutGrid,
  Settings,
  Share2,
  Stethoscope,
  Users,
  Wallet,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cx } from '../lib/format'

export type PageId =
  | 'overview'
  | 'timeline'
  | 'people'
  | 'financials'
  | 'documents'
  | 'tasks'
  | 'providers'
  | 'provider-portal'
  | 'settings'

interface NavItem {
  id: PageId
  label: string
  icon: LucideIcon
  badge?: string
}

const caseNav: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'timeline', label: 'Timeline', icon: CalendarRange },
  { id: 'people', label: 'People', icon: Users },
  { id: 'financials', label: 'Financials', icon: Wallet },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'tasks', label: 'Tasks', icon: CheckSquare, badge: '2' },
]

const providerNav: NavItem[] = [
  { id: 'providers', label: 'Providers', icon: Stethoscope },
  { id: 'provider-portal', label: 'Provider Portal', icon: Share2 },
]

interface Props {
  current: PageId
  onNavigate: (id: PageId) => void
}

export function Sidebar({ current, onNavigate }: Props) {
  const renderItem = (item: NavItem) => {
    const active = item.id === current
    const Icon = item.icon
    return (
      <li key={item.id}>
        <button
          type="button"
          onClick={() => onNavigate(item.id)}
          className={cx(
            'relative flex w-full items-center gap-2.5 rounded-[5px] px-2.5 py-[7px] text-[13px] transition-colors',
            active ? 'bg-ink/[0.055] font-medium text-ink' : 'text-ink-2 hover:bg-ink/[0.03] hover:text-ink',
          )}
        >
          {active && <span className="absolute top-1.5 bottom-1.5 -left-3 w-[2px] rounded-full bg-swan" />}
          <Icon size={15} strokeWidth={1.6} className={active ? 'text-ink' : 'text-muted'} />
          <span className="flex-1 text-left">{item.label}</span>
          {item.badge && (
            <span className="tabular rounded-[3px] bg-high-soft px-1.5 font-mono text-[10px] leading-[16px] text-high">
              {item.badge}
            </span>
          )}
        </button>
      </li>
    )
  }

  return (
    <aside className="sticky top-0 flex h-screen w-[212px] shrink-0 flex-col border-r border-line bg-paper-2/60 px-3 py-5">
      <div className="mb-7 px-2.5">
        <div className="flex items-center gap-2">
          <SwanMark />
          <span className="text-[14px] font-semibold tracking-[0.18em]">SWANS</span>
        </div>
        <div className="mt-1 pl-[26px] text-[11.5px] text-muted">Case Intelligence</div>
      </div>

      <ul className="space-y-0.5">{caseNav.map(renderItem)}</ul>

      <div className="mx-2.5 my-4 border-t border-line" />
      <ul className="space-y-0.5">{providerNav.map(renderItem)}</ul>

      <div className="mx-2.5 my-4 border-t border-line" />
      <ul>{renderItem({ id: 'settings', label: 'Settings', icon: Settings })}</ul>

      <div className="mt-auto border-t border-line px-2.5 pt-4">
        <div className="label">Sapini Matter</div>
        <div className="mt-1.5 flex items-center gap-1.5 text-[12.5px] text-ink-2">
          <span className="h-1.5 w-1.5 rounded-full bg-ok" />
          Active
          <span className="ml-auto font-mono text-[10.5px] text-faint">SP-20491</span>
        </div>
      </div>
    </aside>
  )
}

function SwanMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <path
        d="M4 13.5c2.2 1.6 7.6 1.8 10-1.2 1.2-1.5.6-3.4-1.4-3.6-1.7-.2-2.6 1.3-4.1 1.2C6.3 9.8 6 7.2 7.6 5.6c1-1 2.6-1.1 3.3-.3"
        stroke="var(--color-swan)"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="11.6" cy="4.6" r="1" fill="var(--color-swan)" />
    </svg>
  )
}
