import { MoreHorizontal, Search, Share } from 'lucide-react'
import type { CaseData } from '../types'
import { fmtTime } from '../lib/format'
import { CaseStatus } from './CaseStatus'

interface Props {
  data: CaseData
  onSearch: () => void
}

export function CaseHeader({ data, onSearch }: Props) {
  return (
    <header className="border-b border-line bg-paper/90 backdrop-blur supports-[backdrop-filter]:bg-paper/75">
      <div className="flex items-start justify-between gap-6 px-10 pt-5 pb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="truncate text-[17px] font-semibold tracking-[0.04em] uppercase">{data.title}</h1>
            <span className="inline-flex items-center gap-1.5 rounded-[3px] border border-ok/25 bg-ok-soft px-1.5 py-[1px] font-mono text-[10px] tracking-[0.08em] text-ok uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-ok" />
              {data.status}
            </span>
          </div>
          <dl className="mt-2 flex flex-wrap items-baseline gap-x-6 gap-y-1 text-[12.5px]">
            <HeaderMeta label="Client" value={data.clientName} />
            <HeaderMeta label="Case" value={`#${data.id}`} mono />
            <HeaderMeta label="Last updated" value={`Today, ${fmtTime(data.lastUpdated)}`} />
          </dl>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onSearch}
            className="flex h-8 w-[240px] items-center gap-2 rounded-[5px] border border-line bg-surface px-2.5 text-[12.5px] text-muted transition-colors hover:border-line-strong hover:text-ink-2"
          >
            <Search size={14} strokeWidth={1.7} />
            <span className="flex-1 text-left">Search this case…</span>
            <kbd className="font-mono text-[10px] text-faint">⌘K</kbd>
          </button>
          <button
            type="button"
            className="flex h-8 items-center gap-1.5 rounded-[5px] border border-line bg-surface px-3 text-[12.5px] text-ink-2 transition-colors hover:border-line-strong hover:text-ink"
          >
            <Share size={13} strokeWidth={1.7} />
            Share
          </button>
          <button
            type="button"
            aria-label="More"
            className="flex h-8 w-8 items-center justify-center rounded-[5px] border border-line bg-surface text-ink-2 transition-colors hover:border-line-strong hover:text-ink"
          >
            <MoreHorizontal size={15} strokeWidth={1.7} />
          </button>
        </div>
      </div>
      <CaseStatus stages={data.stages} />
    </header>
  )
}

function HeaderMeta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-muted">{label}</dt>
      <dd className={mono ? 'tabular font-mono text-[12px] text-ink-2' : 'text-ink-2'}>{value}</dd>
    </div>
  )
}
