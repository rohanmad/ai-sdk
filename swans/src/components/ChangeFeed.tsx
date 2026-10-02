import { ArrowRight, ArrowUpRight } from 'lucide-react'
import type { ChangeItem, Impact } from '../types'
import { useSource } from '../context/SourceContext'
import { cx, fmtDate } from '../lib/format'

const impactStyle: Record<Impact, { label: string; dot: string; text: string }> = {
  high: { label: 'High impact', dot: 'bg-high', text: 'text-high' },
  attention: { label: 'Attention', dot: 'bg-warn', text: 'text-warn' },
  activity: { label: 'Activity', dot: 'bg-ok', text: 'text-ok' },
}

interface Props {
  items: ChangeItem[]
  lastViewed: string
  totalSinceLastViewed: number
  onViewAll: () => void
}

export function ChangeFeed({ items, lastViewed, totalSinceLastViewed, onViewAll }: Props) {
  const { openSource, activeSourceId } = useSource()
  return (
    <section>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="label !text-ink">What changed since you last looked?</h2>
        <span className="text-[11.5px] whitespace-nowrap text-muted">
          Last viewed {fmtDate(lastViewed)} ·{' '}
          <span className="text-ink-2">
            {items.length} of {totalSinceLastViewed} updates matter
          </span>
        </span>
      </div>

      <ul className="mt-3 border-t border-ink/80">
        {items.map((item) => {
          const style = impactStyle[item.impact]
          const active = activeSourceId === item.sourceId
          return (
            <li key={item.id} className="border-b border-line">
              <button
                type="button"
                onClick={() => openSource(item.sourceId)}
                className={cx(
                  'group grid w-full grid-cols-[112px_1fr_auto] items-start gap-4 py-3.5 text-left transition-colors hover:bg-surface',
                  active && 'bg-surface',
                )}
              >
                <span className={cx('flex items-center gap-2 pt-[3px] font-mono text-[10px] tracking-[0.08em] uppercase', style.text)}>
                  <span className={cx('h-[7px] w-[7px] rounded-full', style.dot)} />
                  {style.label}
                </span>
                <span className="min-w-0">
                  <span className="block text-[14px] font-medium text-ink">{item.title}</span>
                  <span className="mt-0.5 block text-[12.5px] leading-snug text-ink-2">{item.detail}</span>
                  <span className="mt-1.5 block text-[11.5px] text-muted">
                    <span className="tabular">{fmtDate(item.date)}</span> · {item.channel}
                  </span>
                </span>
                <span className="flex items-center gap-1 pt-[2px] text-[11.5px] text-muted opacity-60 transition-opacity group-hover:text-swan group-hover:opacity-100">
                  Open source <ArrowUpRight size={12} />
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <button
        type="button"
        onClick={onViewAll}
        className="mt-3 flex items-center gap-1.5 text-[12.5px] text-ink-2 transition-colors hover:text-swan"
      >
        View all activity <ArrowRight size={13} />
      </button>
    </section>
  )
}
