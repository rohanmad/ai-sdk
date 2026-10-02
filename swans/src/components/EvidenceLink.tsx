import { sourceById } from '../data/sources'
import { useSource } from '../context/SourceContext'
import { cx, fmtDate } from '../lib/format'

interface Props {
  sourceId: string
  label?: string
  className?: string
  showPrefix?: boolean
}

export function EvidenceLink({ sourceId, label, className, showPrefix = true }: Props) {
  const { openSource, activeSourceId } = useSource()
  const src = sourceById[sourceId]
  if (!src) return null
  const text = label ?? `${src.title} · ${fmtDate(src.date)}`
  const active = activeSourceId === sourceId
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        openSource(sourceId)
      }}
      className={cx(
        'group inline-flex items-center gap-1 text-[11.5px] text-muted transition-colors hover:text-swan',
        active && 'text-swan',
        className,
      )}
    >
      {showPrefix && <span className="text-faint group-hover:text-swan/70">Source ·</span>}
      <span className="underline decoration-line-strong decoration-dotted underline-offset-[3px] group-hover:decoration-swan">
        {text}
      </span>
    </button>
  )
}
