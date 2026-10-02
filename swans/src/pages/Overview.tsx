import { attention, caseData, changeStats, changes, injuries, storyEvents, treatmentSpan, waitingOn } from '../data/case'
import { AttentionCenter, WaitingOn } from '../components/AttentionCenter'
import { CaseBrief } from '../components/CaseBrief'
import { CaseGlance } from '../components/CaseGlance'
import { CaseSignals } from '../components/CaseSignals'
import { CaseStory } from '../components/CaseStory'
import { ChangeFeed } from '../components/ChangeFeed'
import { PrimaryInjuries } from '../components/PrimaryInjuries'

export function Overview({ onViewAllActivity }: { onViewAllActivity: () => void }) {
  return (
    <div className="mx-auto max-w-[1400px] px-10 pt-8 pb-24">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-[30px] leading-none font-semibold tracking-[-0.025em]">Case Overview</h1>
          <p className="mt-2 text-[13.5px] text-muted">A 90-second view of the Sapini matter.</p>
        </div>
      </div>

      <div className="mt-6">
        <CaseSignals signals={caseData.signals} />
      </div>

      <div className="mt-10 grid grid-cols-[minmax(0,1fr)_320px] gap-12 max-[1240px]:grid-cols-[minmax(0,1fr)_280px] max-[1240px]:gap-8">
        <CaseBrief data={caseData} />
        <CaseGlance items={caseData.glance} />
      </div>

      <div className="mt-14">
        <CaseStory events={storyEvents} treatmentSpan={treatmentSpan} lastViewed={caseData.lastViewed} />
      </div>

      <div className="mt-12 grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] gap-12 max-[1240px]:gap-8">
        <ChangeFeed
          items={changes}
          lastViewed={caseData.lastViewed}
          totalSinceLastViewed={changeStats.totalSinceLastViewed}
          onViewAll={onViewAllActivity}
        />
        <AttentionCenter items={attention} />
      </div>

      <div className="mt-12 grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] gap-12 max-[1240px]:gap-8">
        <PrimaryInjuries injuries={injuries} />
        <WaitingOn items={waitingOn} />
      </div>
    </div>
  )
}
