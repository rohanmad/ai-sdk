import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

interface SourceState {
  activeSourceId: string | null
  openSource: (id: string) => void
  closeSource: () => void
}

const SourceContext = createContext<SourceState | null>(null)

export function SourceProvider({ children }: { children: ReactNode }) {
  const [activeSourceId, setActive] = useState<string | null>(null)
  const openSource = useCallback((id: string) => setActive(id), [])
  const closeSource = useCallback(() => setActive(null), [])
  const value = useMemo(
    () => ({ activeSourceId, openSource, closeSource }),
    [activeSourceId, openSource, closeSource],
  )
  return <SourceContext.Provider value={value}>{children}</SourceContext.Provider>
}

export function useSource() {
  const ctx = useContext(SourceContext)
  if (!ctx) throw new Error('useSource must be used inside SourceProvider')
  return ctx
}
