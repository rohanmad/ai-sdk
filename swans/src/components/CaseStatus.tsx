import { Fragment } from 'react'
import type { CaseStage } from '../types'
import { cx, fmtDate } from '../lib/format'

export function CaseStatus({ stages }: { stages: CaseStage[] }) {
  return (
    <nav aria-label="Case stage" className="flex items-stretch px-10 pb-3">
      {stages.map((stage, i) => {
        const current = stage.status === 'current'
        return (
          <Fragment key={stage.id}>
            {i > 0 && (
              <div className="flex min-w-4 flex-1 items-center px-2 pt-0.5">
                <div className={cx('h-px w-full', current ? 'bg-swan/40' : 'bg-line-strong')} />
              </div>
            )}
            <div className="flex shrink-0 items-center gap-2">
              <span
                className={cx(
                  'h-[7px] w-[7px] shrink-0 rounded-full',
                  current ? 'bg-swan ring-[3px] ring-swan/15' : stage.status === 'complete' ? 'bg-ink-2' : 'border border-line-strong',
                )}
              />
              <div className="leading-tight">
                <div
                  className={cx(
                    'font-mono text-[10.5px] tracking-[0.1em] uppercase',
                    current ? 'font-medium text-swan' : 'text-ink-2',
                  )}
                >
                  {stage.label}
                </div>
                <div className={cx('text-[11px] whitespace-nowrap', current ? 'text-ink' : 'text-muted')}>
                  {stage.detail}
                  {stage.date && !current && <span className="text-faint"> · {fmtDate(stage.date)}</span>}
                  {current && <span className="text-swan/70"> · Now</span>}
                </div>
              </div>
            </div>
          </Fragment>
        )
      })}
    </nav>
  )
}
