import type { AttentionItem, Urgency, WaitingItem } from '../types'
import { useSource } from '../context/SourceContext'
import { cx, daysAgo, fmtDate } from '../lib/format'
import { EvidenceLink } from './EvidenceLink'

const urgencyStyle: Record<Urgency, { label: string; bar: string; text: string }> = {
  overdue: { label: 'Overdue', bar: 'bg-high', text: 'text-high' },
  soon: { label: 'Due soon', bar: 'bg-warn', text: 'text-warn' },
  info: { label: 'FYI', bar: 'bg-line-strong', text: 'text-muted' },
}

export function AttentionCenter({ items }: { items: AttentionItem[] }) {
  const { openSource } = useSource()
  const overdue = items.filter((i) => i.urgency === 'overdue').length

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="label !text-ink">Needs attention</h2>
        <span className="text-[11.5px] text-muted">
          <span className="font-medium text-high">{overdue} overdue</span> · {items.length - overdue} due this week
        </span>
      </div>

      <ul className="mt-3 overflow-hidden rounded-[6px] border border-line bg-surface">
        {items.map((item, i) => {
          const style = urgencyStyle[item.urgency]
          return (
            <li key={item.id} className={cx('relative flex gap-3 py-3 pr-4 pl-4', i > 0 && 'border-t border-line')}>
              <span className={cx('absolute top-3 bottom-3 left-0 w-[2px]', style.bar)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className={cx('font-mono text-[10px] tracking-[0.08em] uppercase', style.text)}>
                    {style.label}
                  </span>
                  <span className="text-[13.5px] font-medium text-ink">{item.title}</span>
                </div>
                <p className="mt-0.5 text-[12.5px] leading-snug text-ink-2">{item.description}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-[11.5px] text-muted">
                  <span className={cx('tabular', item.urgency === 'overdue' && 'text-high')}>{item.dueLabel}</span>
                  {item.owner && <span>· {item.owner}</span>}
                  <span>·</span>
                  <EvidenceLink sourceId={item.sourceId} label={item.sourceLabel} />
                </div>
              </div>
              <button
                type="button"
                onClick={() => openSource(item.sourceId)}
                className="h-fit shrink-0 rounded-[4px] border border-line px-2.5 py-1 text-[11.5px] whitespace-nowrap text-ink-2 transition-colors hover:border-ink/30 hover:text-ink"
              >
                {item.action}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export function WaitingOn({ items }: { items: WaitingItem[] }) {
  const { openSource } = useSource()
  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="label !text-ink">Waiting on</h2>
        <span className="text-[11.5px] text-muted">{items.length} outstanding</span>
      </div>
      <ul className="mt-3 border-t border-ink/80">
        {items.map((w) => {
          const days = daysAgo(w.requested)
          return (
            <li key={w.id} className="border-b border-line">
              <button
                type="button"
                onClick={() => openSource(w.sourceId)}
                className="grid w-full grid-cols-[1fr_auto] items-baseline gap-3 py-2.5 text-left transition-colors hover:bg-surface"
              >
                <span className="min-w-0">
                  <span className="text-[13px] font-medium text-ink">{w.party}</span>
                  <span className="ml-1.5 font-mono text-[10px] tracking-[0.08em] text-muted uppercase">{w.partyRole}</span>
                  <span className="block text-[12.5px] text-ink-2">{w.item}</span>
                </span>
                <span className="text-right">
                  <span className={cx('tabular block text-[12.5px]', days > 14 ? 'text-high' : days > 7 ? 'text-warn' : 'text-ink-2')}>
                    {days} days
                  </span>
                  <span className="block text-[11px] text-muted">since {fmtDate(w.requested)}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
