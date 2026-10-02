export type SourceKind =
  | 'medical'
  | 'insurance'
  | 'legal'
  | 'communication'
  | 'financial'
  | 'internal'

export interface SourceSection {
  heading: string
  body: string
}

export interface Source {
  id: string
  title: string
  kind: SourceKind
  docType: string
  date: string
  author?: string
  origin: string
  sections: SourceSection[]
  excerpt: string
  usedIn: string[]
}

export type StageStatus = 'complete' | 'current' | 'upcoming'

export interface CaseStage {
  id: string
  label: string
  detail: string
  date?: string
  status: StageStatus
}

export interface CaseSignal {
  id: string
  label: string
  value: string
  qualifier: string
  sub?: string
  tone?: 'default' | 'ok' | 'warn' | 'high'
  sourceId: string
}

export type FactKind =
  | 'client'
  | 'incident'
  | 'liability'
  | 'treatment'
  | 'injury'
  | 'coverage'
  | 'money'
  | 'status'
  | 'activity'

export type BriefSegment =
  | string
  | { text: string; kind: FactKind; sourceId: string }

export interface GlanceItem {
  id: string
  label: string
  value: string
  sub?: string
  tone?: 'default' | 'high' | 'warn' | 'ok'
  sourceId?: string
}

export interface CaseData {
  id: string
  title: string
  status: 'active' | 'closed'
  clientName: string
  defendantName: string
  lastUpdated: string
  lastViewed: string
  stages: CaseStage[]
  signals: CaseSignal[]
  brief: BriefSegment[]
  briefCorpus: { entries: number; documents: number; communications: number }
  glance: GlanceItem[]
}

export interface StoryEvent {
  id: string
  date: string
  category: string
  title: string
  summary: string
  sourceId: string
  isNow?: boolean
}

export type Impact = 'high' | 'attention' | 'activity'

export interface ChangeItem {
  id: string
  impact: Impact
  title: string
  detail: string
  date: string
  channel: string
  sourceId: string
}

export type Urgency = 'overdue' | 'soon' | 'info'

export interface AttentionItem {
  id: string
  urgency: Urgency
  title: string
  description: string
  dueLabel: string
  owner?: string
  sourceId: string
  sourceLabel: string
  action: string
}

export interface WaitingItem {
  id: string
  party: string
  partyRole: string
  item: string
  requested: string
  sourceId: string
}

export type Confidence = 'high' | 'medium' | 'low'

export interface Injury {
  id: string
  region: string
  finding: string
  confidence: Confidence
  rationale: string
  evidence: string[]
}

export interface SearchEntry {
  id: string
  question: string
  keywords: string[]
  answer: string
  sourceId: string
}
