import { useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import type { StoryEvent } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { cx, daysBetween, fmtDate, fmtGap } from '../lib/format'

interface Span {
  startEventId: string
  endEventId: string
  label: string
  sourceId: string
}

interface Props {
  events: StoryEvent[]
  treatmentSpan: Span
  lastViewed: string
}

export function CaseStory({ events, treatmentSpan, lastViewed }: Props) {
  const { openSource, activeSourceId } = useSource()
  const [hovered, setHovered] = useState<string | null>(null)
  const n = events.length
  const pos = (i: number) => ((i + 0.5) / n) * 100

  const firstNew = events.findIndex((e) => e.date > lastViewed)
  const spanStart = events.findIndex((e) => e.id === treatmentSpan.startEventId)
  const spanEnd = events.findIndex((e) => e.id === treatmentSpan.endEventId)
  const totalDays = daysBetween(events[0].date, events[n - 1].date)

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="label !text-ink">Case story</h2>
        <span className="text-[11.5px] text-muted">
          {fmtDate(events[0].date)} → today · {Math.round(totalDays / 30)} months · {n - 1} key events of 412 entries
        </span>
      </div>

      <div className="relative mt-6 select-none" onMouseLeave={() => setHovered(null)}>
        {firstNew > 0 && (
          <div
            className="pointer-events-none absolute top-0 bottom-0 rounded-[4px] bg-swan-soft/45"
            style={{ left: `${pos(firstNew) - 50 / n}%`, right: 0 }}
          >
            <span className="absolute -top-5 left-2 font-mono text-[9.5px] tracking-[0.1em] text-swan uppercase">
              Since you last looked · {fmtDate(lastViewed)}
            </span>
          </div>
        )}

        <div className="relative grid" style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
          <div className="absolute top-[40px] h-px bg-line-strong" style={{ left: `${pos(0)}%`, right: `${100 - pos(n - 1)}%` }} />

          {events.slice(1).map((e, i) => (
            <span
              key={`gap-${e.id}`}
              className="tabular absolute top-[26px] -translate-x-1/2 px-1 font-mono text-[9.5px] text-faint"
              style={{ left: `${(pos(i) + pos(i + 1)) / 2}%` }}
            >
              {fmtGap(daysBetween(events[i].date, e.date))}
            </span>
          ))}

          {events.map((e, i) => {
            const isHover = hovered === e.id
            const isActive = activeSourceId === e.sourceId
            const isNew = e.date > lastViewed && !e.isNow
            const align = i === 0 ? 'left' : i === n - 1 ? 'right' : 'center'
            return (
              <div
                key={e.id}
                className="relative flex flex-col items-center px-1.5 pt-1 pb-3 text-center"
                onMouseEnter={() => setHovered(e.id)}
              >
                <div
                  className={cx(
                    'font-mono text-[10px] tracking-[0.1em] uppercase',
                    e.isNow ? 'font-medium text-swan' : 'text-muted',
                  )}
                >
                  {e.category}
                </div>
                <button
                  type="button"
                  onClick={() => openSource(e.sourceId)}
                  aria-label={`${e.title}, ${fmtDate(e.date)}`}
                  className="relative z-10 mt-[11px] flex h-5 w-5 items-center justify-center"
                >
                  <span
                    className={cx(
                      'block rounded-full transition-all duration-150',
                      e.isNow
                        ? 'h-3 w-3 bg-swan ring-4 ring-swan/15'
                        : isHover || isActive
                          ? 'h-3 w-3 bg-ink ring-4 ring-ink/10'
                          : 'h-[9px] w-[9px] border-[1.5px] border-ink bg-paper',
                    )}
                  />
                  {isNew && <span className="absolute -top-0.5 -right-0.5 h-1.5 w-1.5 rounded-full bg-high" />}
                </button>
                <button
                  type="button"
                  onClick={() => openSource(e.sourceId)}
                  className="mt-2 flex flex-col items-center"
                >
                  <span className="tabular font-mono text-[11px] text-ink-2">{fmtDate(e.date)}</span>
                  <span
                    className={cx(
                      'mt-0.5 text-[12.5px] leading-snug font-medium',
                      isHover ? 'text-swan' : 'text-ink',
                    )}
                  >
                    {e.title}
                  </span>
                </button>

                {isHover && <Preview event={e} align={align} onOpen={() => openSource(e.sourceId)} />}
              </div>
            )
          })}
        </div>

        {spanStart >= 0 && spanEnd >= 0 && (
          <button
            type="button"
            onClick={() => openSource(treatmentSpan.sourceId)}
            className="group relative block h-8 w-full"
          >
            <span
              className="absolute top-1 h-[3px] rounded-full bg-ok/40 transition-colors group-hover:bg-ok/70"
              style={{ left: `${pos(spanStart)}%`, right: `${100 - pos(spanEnd)}%` }}
            />
            <span
              className="absolute top-3 text-[11px] text-ok group-hover:underline"
              style={{ left: `${pos(spanStart)}%` }}
            >
              {treatmentSpan.label}
            </span>
          </button>
        )}
      </div>
    </section>
  )
}

function Preview({
  event,
  align,
  onOpen,
}: {
  event: StoryEvent
  align: 'left' | 'center' | 'right'
  onOpen: () => void
}) {
  const src = sourceById[event.sourceId]
  return (
    <div
      className={cx(
        'absolute top-full z-30 w-[280px] pt-1.5 text-left',
        align === 'center' && 'animate-pop-in left-1/2 -translate-x-1/2',
        align === 'left' && 'animate-fade-in left-0',
        align === 'right' && 'animate-fade-in right-0',
      )}
    >
      <div className="rounded-[6px] border border-line-strong bg-surface p-3.5 shadow-[0_8px_30px_-12px_rgba(23,22,15,0.25)]">
        <div className="flex items-baseline justify-between">
          <span className="font-mono text-[10px] tracking-[0.1em] text-muted uppercase">{event.title}</span>
          <span className="tabular font-mono text-[10.5px] text-muted">{fmtDate(event.date)}</span>
        </div>
        <p className="mt-2 text-[12.5px] leading-snug text-ink-2">{event.summary}</p>
        <blockquote className="mt-2.5 border-l-2 border-swan/40 pl-2.5 font-serif text-[13.5px] leading-snug text-ink italic">
          “{src.excerpt}”
        </blockquote>
        <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5">
          <div className="text-[11px] leading-tight text-muted">
            <div className="text-ink-2">{src.title}</div>
            {src.docType} · {fmtDate(src.date)}
          </div>
          <button
            type="button"
            onClick={onOpen}
            className="flex items-center gap-1 rounded-[4px] border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-swan/40 hover:text-swan"
          >
            Open source <ArrowUpRight size={12} />
          </button>
        </div>
      </div>
    </div>
  )
}
