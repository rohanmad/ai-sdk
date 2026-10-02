import type { GlanceItem } from '../types'
import { useSource } from '../context/SourceContext'
import { cx } from '../lib/format'

export function CaseGlance({ items }: { items: GlanceItem[] }) {
  const { openSource } = useSource()
  return (
    <section className="rounded-[6px] border border-line bg-surface">
      <h2 className="label border-b border-line px-4 py-2.5 !text-ink">Who & where it stands</h2>
      <dl>
        {items.map((item, i) => {
          const clickable = Boolean(item.sourceId)
          return (
            <div
              key={item.id}
              role={clickable ? 'button' : undefined}
              tabIndex={clickable ? 0 : undefined}
              onClick={() => item.sourceId && openSource(item.sourceId)}
              onKeyDown={(e) => e.key === 'Enter' && item.sourceId && openSource(item.sourceId)}
              className={cx(
                'grid grid-cols-[108px_1fr] items-baseline gap-3 px-4 py-2.5',
                i > 0 && 'border-t border-line/70',
                clickable && 'cursor-pointer transition-colors hover:bg-paper',
              )}
            >
              <dt className="text-[11.5px] text-muted">{item.label}</dt>
              <dd className="min-w-0">
                <div
                  className={cx(
                    'text-[13.5px] font-medium',
                    item.tone === 'high' ? 'text-high' : item.tone === 'warn' ? 'text-warn' : 'text-ink',
                  )}
                >
                  {item.value}
                </div>
                {item.sub && <div className="truncate text-[11.5px] text-muted">{item.sub}</div>}
              </dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
