import { useState } from 'react'
import { ChevronRight } from 'lucide-react'
import type { Confidence, Injury } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { cx, fmtDate } from '../lib/format'

const confidenceMeta: Record<Confidence, { label: string; filled: number; color: string }> = {
  high: { label: 'High confidence', filled: 3, color: 'bg-ink' },
  medium: { label: 'Medium confidence', filled: 2, color: 'bg-ink-2' },
  low: { label: 'Low confidence', filled: 1, color: 'bg-muted' },
}

export function PrimaryInjuries({ injuries }: { injuries: Injury[] }) {
  const [open, setOpen] = useState<string | null>(injuries[0]?.id ?? null)
  const { openSource, activeSourceId } = useSource()

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="label !text-ink">Primary injuries</h2>
        <span className="text-[11.5px] text-muted">Injury → evidence. Confidence reflects corroborating records.</span>
      </div>

      <ul className="mt-3 border-t border-ink/80">
        {injuries.map((inj) => {
          const meta = confidenceMeta[inj.confidence]
          const isOpen = open === inj.id
          return (
            <li key={inj.id} className="border-b border-line">
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : inj.id)}
                className="grid w-full grid-cols-[16px_150px_1fr_auto] items-center gap-3 py-3 text-left transition-colors hover:bg-surface"
              >
                <ChevronRight
                  size={13}
                  className={cx('text-muted transition-transform duration-150', isOpen && 'rotate-90')}
                />
                <span className="text-[13px] font-semibold tracking-[0.06em] uppercase">{inj.region}</span>
                <span className="truncate text-[12.5px] text-ink-2">{inj.finding}</span>
                <span className="flex items-center gap-2.5">
                  <span className="flex gap-[3px]">
                    {[0, 1, 2].map((k) => (
                      <span
                        key={k}
                        className={cx('h-[10px] w-[4px] rounded-[1px]', k < meta.filled ? meta.color : 'bg-line')}
                      />
                    ))}
                  </span>
                  <span className="w-[118px] text-[11.5px] text-muted">{meta.label}</span>
                </span>
              </button>

              {isOpen && (
                <div className="animate-fade-in grid grid-cols-[16px_150px_1fr] gap-3 pb-4">
                  <span />
                  <span className="pt-1 text-[11.5px] leading-snug text-muted">{inj.rationale}</span>
                  <div>
                    <div className="label mb-1.5">Evidence · {inj.evidence.length}</div>
                    <ul className="divide-y divide-line rounded-[5px] border border-line bg-surface">
                      {inj.evidence.map((id) => {
                        const src = sourceById[id]
                        return (
                          <li key={id}>
                            <button
                              type="button"
                              onClick={() => openSource(id)}
                              className={cx(
                                'group grid w-full grid-cols-[1fr_auto] items-baseline gap-3 px-3 py-2 text-left transition-colors hover:bg-paper',
                                activeSourceId === id && 'bg-paper',
                              )}
                            >
                              <span className="min-w-0">
                                <span className="text-[12.5px] font-medium text-ink group-hover:text-swan">{src.title}</span>
                                <span className="block truncate text-[11.5px] text-muted">“{src.excerpt}”</span>
                              </span>
                              <span className="tabular font-mono text-[10.5px] text-muted">{fmtDate(src.date)}</span>
                            </button>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
