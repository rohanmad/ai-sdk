import { useEffect, useMemo, useRef, useState } from 'react'
import { CornerDownLeft, Search } from 'lucide-react'
import type { SearchEntry } from '../types'
import { useSource } from '../context/SourceContext'
import { sourceById } from '../data/sources'
import { cx, fmtDate } from '../lib/format'

interface Props {
  open: boolean
  onClose: () => void
  index: SearchEntry[]
}

const suggestions = ['coverage', 'last client contact', 'primary injury', 'what happened last week']

function rank(index: SearchEntry[], query: string) {
  const q = query.trim().toLowerCase()
  if (!q) return []
  const words = q.split(/\s+/).filter((w) => w.length > 2)
  return index
    .map((entry) => {
      const hay = [entry.question, ...entry.keywords].join(' ').toLowerCase()
      let score = entry.keywords.some((k) => k === q) ? 10 : 0
      if (hay.includes(q)) score += 5
      score += words.filter((w) => hay.includes(w)).length
      return { entry, score }
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((r) => r.entry)
}

export function GlobalSearch({ open, onClose, index }: Props) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const { openSource } = useSource()
  const results = useMemo(() => rank(index, query), [index, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  if (!open) return null

  const choose = (entry: SearchEntry) => {
    onClose()
    openSource(entry.sourceId)
  }

  return (
    <div className="animate-fade-in fixed inset-0 z-[60] flex items-start justify-center bg-ink/15 pt-[12vh]" onClick={onClose}>
      <div
        className="w-[620px] max-w-[92vw] overflow-hidden rounded-[8px] border border-line-strong bg-surface shadow-[0_24px_60px_-20px_rgba(23,22,15,0.35)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <Search size={15} className="text-muted" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelected(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose()
              if (e.key === 'ArrowDown') setSelected((s) => Math.min(s + 1, results.length - 1))
              if (e.key === 'ArrowUp') setSelected((s) => Math.max(s - 1, 0))
              if (e.key === 'Enter' && results[selected]) choose(results[selected])
            }}
            placeholder="Search this case…"
            className="h-12 flex-1 bg-transparent text-[15px] outline-none placeholder:text-faint"
          />
          <kbd className="font-mono text-[10px] text-faint">ESC</kbd>
        </div>

        {!query && (
          <div className="px-4 py-3.5">
            <div className="label mb-2">Try</div>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setQuery(s)}
                  className="rounded-[4px] border border-line px-2 py-1 text-[12.5px] text-ink-2 hover:border-line-strong hover:text-ink"
                >
                  “{s}”
                </button>
              ))}
            </div>
          </div>
        )}

        {query && results.length === 0 && (
          <div className="px-4 py-6 text-[13px] text-muted">No answer found in this case file.</div>
        )}

        {results.length > 0 && (
          <ul className="max-h-[420px] overflow-y-auto py-1.5">
            {results.map((r, i) => {
              const src = sourceById[r.sourceId]
              return (
                <li key={r.id}>
                  <button
                    type="button"
                    onMouseEnter={() => setSelected(i)}
                    onClick={() => choose(r)}
                    className={cx(
                      'grid w-full grid-cols-[1fr_auto] gap-4 px-4 py-3 text-left',
                      i === selected && 'bg-paper',
                    )}
                  >
                    <span>
                      <span className="block text-[11.5px] text-muted">{r.question}</span>
                      <span className="mt-1 block text-[14px] leading-snug text-ink">
                        <span className="label mr-2 !text-swan">Answer</span>
                        {r.answer}
                      </span>
                      <span className="mt-1.5 block text-[11.5px] text-muted">
                        Source · <span className="text-ink-2">{src.title}</span> · {fmtDate(src.date)}
                      </span>
                    </span>
                    {i === selected && <CornerDownLeft size={13} className="mt-1 text-faint" />}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
