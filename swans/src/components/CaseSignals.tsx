import type { CaseSignal } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { cx, fmtDate } from '../lib/format'

export function CaseSignals({ signals }: { signals: CaseSignal[] }) {
  const { openSource } = useSource()
  return (
    <div className="grid grid-cols-4 border-y border-ink/80">
      {signals.map((s, i) => {
        const src = sourceById[s.sourceId]
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => openSource(s.sourceId)}
            className={cx(
              'group relative px-5 py-4 text-left transition-colors hover:bg-surface',
              i > 0 && 'border-l border-line',
            )}
          >
            <div className="label">{s.label}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span
                className={cx(
                  'tabular text-[28px] leading-none font-medium tracking-[-0.02em]',
                  s.tone === 'ok' && 'text-ok',
                )}
              >
                {s.value}
              </span>
            </div>
            <div className="mt-2 text-[12.5px] text-ink-2">{s.qualifier}</div>
            {s.sub && <div className="text-[12px] text-muted">{s.sub}</div>}
            <div className="mt-2.5 truncate text-[11px] text-faint transition-colors group-hover:text-swan">
              Source · {src.title} · {fmtDate(src.date)}
            </div>
          </button>
        )
      })}
    </div>
  )
}
