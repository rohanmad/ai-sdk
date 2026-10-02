import { Sparkles } from 'lucide-react'
import type { BriefSegment, CaseData, FactKind } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { cx, fmtDate, fmtTime } from '../lib/format'

const kindStyle: Record<FactKind, { label: string; className: string }> = {
  client: { label: 'Client', className: 'decoration-swan/70 hover:bg-swan-soft' },
  incident: { label: 'Incident', className: 'decoration-ink/40 hover:bg-ink/[0.06]' },
  liability: { label: 'Liability', className: 'decoration-ink/40 hover:bg-ink/[0.06]' },
  treatment: { label: 'Treatment', className: 'decoration-ok/70 hover:bg-ok-soft' },
  injury: { label: 'Injury', className: 'decoration-high/70 hover:bg-high-soft' },
  coverage: { label: 'Coverage', className: 'decoration-swan/70 hover:bg-swan-soft' },
  money: { label: 'Liens', className: 'decoration-warn/70 hover:bg-warn-soft' },
  status: { label: 'Status', className: 'decoration-ok/70 hover:bg-ok-soft' },
  activity: { label: 'Recent', className: 'decoration-warn/70 hover:bg-warn-soft' },
}

export function CaseBrief({ data }: { data: CaseData }) {
  const facts = data.brief.filter((s): s is Exclude<BriefSegment, string> => typeof s !== 'string')
  const { entries, documents, communications } = data.briefCorpus

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="label !text-ink">The case in one minute</h2>
        <span className="flex items-center gap-1.5 text-[11px] text-muted">
          <Sparkles size={12} strokeWidth={1.6} className="text-swan" />
          Synthesized from {entries} Clio entries · {documents} documents · {communications} communications
        </span>
      </div>

      <p className="mt-4 font-serif text-[23px] leading-[1.6] tracking-[-0.005em] text-ink">
        {data.brief.map((seg, i) =>
          typeof seg === 'string' ? <span key={i}>{seg}</span> : <Fact key={i} seg={seg} />,
        )}
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-line pt-3 text-[11.5px] text-muted">
        <span>{facts.length} facts linked to source records</span>
        <span className="text-line-strong">|</span>
        <span>Click any highlighted phrase to verify it</span>
        <span className="ml-auto text-faint">Generated today, {fmtTime(data.lastUpdated)}</span>
      </div>
    </section>
  )
}

function Fact({ seg }: { seg: Exclude<BriefSegment, string> }) {
  const { openSource, activeSourceId } = useSource()
  const style = kindStyle[seg.kind]
  const src = sourceById[seg.sourceId]
  const active = activeSourceId === seg.sourceId
  return (
    <span className="group relative inline">
      <button
        type="button"
        onClick={() => openSource(seg.sourceId)}
        className={cx(
          'cursor-pointer rounded-[2px] font-medium underline decoration-2 underline-offset-[6px] transition-colors [box-decoration-break:clone]',
          style.className,
          active && 'bg-swan-soft',
        )}
      >
        {seg.text}
      </button>
      <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded-[4px] bg-ink px-2 py-1 font-sans text-[11px] leading-tight text-paper shadow-lg group-hover:block">
        <span className="font-mono text-[9.5px] tracking-[0.1em] text-paper/60 uppercase">{style.label}</span>
        <span className="mx-1.5 text-paper/30">·</span>
        {src.title} · {fmtDate(src.date)}
      </span>
    </span>
  )
}
