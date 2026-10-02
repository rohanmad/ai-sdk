import { useEffect } from 'react'
import { ExternalLink, FileText, Mail, Receipt, Scale, ShieldCheck, StickyNote, Stethoscope, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { SourceKind } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { fmtDate } from '../lib/format'

const kindMeta: Record<SourceKind, { label: string; icon: LucideIcon }> = {
  medical: { label: 'Medical record', icon: Stethoscope },
  insurance: { label: 'Insurance', icon: ShieldCheck },
  legal: { label: 'Legal', icon: Scale },
  communication: { label: 'Communication', icon: Mail },
  financial: { label: 'Financial', icon: Receipt },
  internal: { label: 'Internal', icon: StickyNote },
}

export function SourceDrawer() {
  const { activeSourceId, closeSource } = useSource()
  const src = activeSourceId ? sourceById[activeSourceId] : null

  useEffect(() => {
    if (!src) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeSource()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [src, closeSource])

  if (!src) return null
  const meta = kindMeta[src.kind]
  const Icon = meta.icon

  return (
    <>
      <div className="animate-fade-in fixed inset-0 z-40 bg-ink/[0.06]" onClick={closeSource} />
      <aside
        key={src.id}
        className="animate-drawer-in fixed top-0 right-0 bottom-0 z-50 flex w-[440px] max-w-[92vw] flex-col border-l border-line-strong bg-surface shadow-[-12px_0_40px_-20px_rgba(23,22,15,0.3)]"
        role="dialog"
        aria-label={`Source: ${src.title}`}
      >
        <div className="border-b border-line px-6 pt-5 pb-4">
          <div className="flex items-center justify-between">
            <span className="label">Source</span>
            <button
              type="button"
              onClick={closeSource}
              aria-label="Close source"
              className="-mr-1.5 flex h-7 w-7 items-center justify-center rounded-[4px] text-muted hover:bg-paper hover:text-ink"
            >
              <X size={15} />
            </button>
          </div>
          <h2 className="mt-2 text-[19px] font-semibold tracking-[-0.01em]">{src.title}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[12px] text-muted">
            <span className="tabular">{fmtDate(src.date, true)}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1">
              <Icon size={12} strokeWidth={1.7} />
              {meta.label}
            </span>
          </div>
          {src.author && <div className="mt-0.5 text-[12px] text-ink-2">{src.author}</div>}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="label mb-2">Relevant excerpt</div>
          <blockquote className="border-l-2 border-swan pl-3 font-serif text-[17px] leading-[1.5] text-ink">
            “{src.excerpt}”
          </blockquote>

          <div className="label mt-6 mb-2">Document preview</div>
          <div className="rounded-[4px] border border-line bg-paper/60 p-4">
            <div className="flex items-center gap-2 border-b border-line pb-2.5">
              <FileText size={13} className="text-muted" />
              <span className="truncate font-mono text-[10.5px] text-muted">{src.docType}</span>
            </div>
            <div className="mt-3 space-y-3">
              {src.sections.map((s) => (
                <div key={s.heading}>
                  <div className="text-[11px] font-semibold tracking-[0.06em] text-ink-2 uppercase">{s.heading}</div>
                  <p className="mt-0.5 font-serif text-[14px] leading-[1.5] text-ink-2">
                    <Highlighted text={s.body} excerpt={src.excerpt} />
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="label mt-6 mb-2">Used in</div>
          <ul className="divide-y divide-line border-y border-line">
            {src.usedIn.map((u) => (
              <li key={u} className="py-2 text-[12.5px] text-ink-2">
                {u}
              </li>
            ))}
          </ul>

          <div className="mt-5 text-[11.5px] text-muted">
            Located in <span className="text-ink-2">{src.origin}</span>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-line px-6 py-3.5">
          <span className="text-[11px] text-faint">Esc to close</span>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-[5px] bg-ink px-3 py-1.5 text-[12.5px] text-paper transition-opacity hover:opacity-90"
          >
            Open original in Clio <ExternalLink size={12} />
          </button>
        </div>
      </aside>
    </>
  )
}

function Highlighted({ text, excerpt }: { text: string; excerpt: string }) {
  const phrases = excerpt
    .split(/[.;]\s*/)
    .map((p) => p.trim())
    .filter((p) => p.length > 12 && text.includes(p))
  if (phrases.length === 0) return <>{text}</>
  const phrase = phrases[0]
  const idx = text.indexOf(phrase)
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded-[2px] bg-swan-soft px-0.5 text-ink">{phrase}</mark>
      {text.slice(idx + phrase.length)}
    </>
  )
}
