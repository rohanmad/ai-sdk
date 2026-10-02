import type { Source } from '../types'

export const sources: Source[] = [
  {
    id: 'src-police',
    title: 'Police Report',
    kind: 'legal',
    docType: 'Traffic Collision Report #TC-26-01187',
    date: '2026-05-03',
    author: 'Officer R. Delgado, Westbrook PD',
    origin: 'Clio · Documents / Liability',
    sections: [
      {
        heading: 'Narrative',
        body: 'Vehicle 1 (Sapini, 2019 Honda Accord) was stopped at a red signal at Route 9 and Elm St. Vehicle 2 (Hollis, 2021 Ford F-150) failed to stop and struck Vehicle 1 from behind at an estimated 25–30 mph.',
      },
      {
        heading: 'Citation',
        body: 'Driver of Vehicle 2 cited for following too closely (§ 46.2-816). Driver of Vehicle 1 complained of lower-back and neck pain and was transported to St. Mary’s Regional by EMS.',
      },
    ],
    excerpt:
      'Vehicle 2 failed to stop and struck Vehicle 1 from behind. Driver of Vehicle 2 cited for following too closely.',
    usedIn: ['Case Summary', 'Liability', 'Case Story · Accident'],
  },
  {
    id: 'src-er',
    title: 'ER Discharge Summary',
    kind: 'medical',
    docType: 'Emergency Department Record',
    date: '2026-05-03',
    author: 'St. Mary’s Regional Medical Center',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'Chief complaint',
        body: 'Lower-back pain radiating to the left leg; neck stiffness following a rear-end motor vehicle collision.',
      },
      {
        heading: 'Assessment',
        body: 'Acute lumbar strain. Cervical strain. No fracture on lumbar X-ray. Discharged with NSAIDs; follow up with orthopedics within 2 weeks.',
      },
    ],
    excerpt: 'Acute lumbar strain. Cervical strain. Follow up with orthopedics within 2 weeks.',
    usedIn: ['Primary Injuries · Neck', 'Case Story · Accident'],
  },
  {
    id: 'src-mri1',
    title: 'Lumbar MRI Report',
    kind: 'medical',
    docType: 'Radiology Report',
    date: '2026-05-14',
    author: 'Westbrook Imaging Center',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'Findings',
        body: 'At L4–L5 there is a left paracentral disc herniation measuring 5 mm with contact of the traversing left L5 nerve root. Remaining levels unremarkable.',
      },
      {
        heading: 'Impression',
        body: 'L4–L5 disc herniation with nerve-root contact, consistent with the patient’s reported radicular symptoms.',
      },
    ],
    excerpt: 'L4–L5 disc herniation with nerve-root contact, consistent with reported radicular symptoms.',
    usedIn: ['Primary Injuries · Lower back', 'Case Summary', 'Case Story · Injury'],
  },
  {
    id: 'src-ortho',
    title: 'Orthopedic Evaluation',
    kind: 'medical',
    docType: 'Consultation Note',
    date: '2026-05-21',
    author: 'Dr. Sarah Lee, Westbrook Orthopedics',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'History',
        body: 'Patient reports persistent lower-back pain since the May 3 collision, and new right-knee pain after striking the dashboard.',
      },
      {
        heading: 'Plan',
        body: 'Physical therapy 2× weekly for 12 weeks. Right-knee X-ray ordered. Re-image lumbar spine if symptoms persist past 4 months.',
      },
    ],
    excerpt: 'Physical therapy 2× weekly for 12 weeks. Right-knee X-ray ordered.',
    usedIn: ['Primary Injuries · Lower back', 'Primary Injuries · Right knee', 'Case Story · Treatment'],
  },
  {
    id: 'src-xray',
    title: 'Right Knee X-ray',
    kind: 'medical',
    docType: 'Radiology Report',
    date: '2026-05-28',
    author: 'Westbrook Imaging Center',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'Findings',
        body: 'No acute fracture or dislocation. Mild soft-tissue swelling anterior to the patella.',
      },
      {
        heading: 'Impression',
        body: 'Soft-tissue injury. Correlate clinically; MRI if symptoms persist.',
      },
    ],
    excerpt: 'No acute fracture. Mild soft-tissue swelling anterior to the patella.',
    usedIn: ['Primary Injuries · Right knee'],
  },
  {
    id: 'src-pt',
    title: 'Physical Therapy Records',
    kind: 'medical',
    docType: 'Treatment Notes (12 visits)',
    date: '2026-09-29',
    author: 'Dr. Mike Chen, DPT, Core Motion PT',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'Course of care',
        body: '12 visits from June 4 to Sept 29. Lumbar stabilization, McKenzie protocol, knee strengthening.',
      },
      {
        heading: 'Progress',
        body: 'Knee pain improved from 6/10 to 2/10. Lower-back pain plateaued at 5/10 with intermittent left-leg radiation.',
      },
    ],
    excerpt: 'Lower-back pain plateaued at 5/10 with intermittent left-leg radiation.',
    usedIn: ['Treatment signal', 'Primary Injuries · Lower back', 'Primary Injuries · Right knee'],
  },
  {
    id: 'src-pt-appt',
    title: 'PT Appointment · Visit 12',
    kind: 'medical',
    docType: 'Calendar Entry',
    date: '2026-09-29',
    author: 'Core Motion PT',
    origin: 'Clio · Calendar',
    sections: [
      {
        heading: 'Appointment',
        body: 'Physical therapy session with Dr. Mike Chen. Status: Attended. Next session scheduled Oct 6.',
      },
    ],
    excerpt: 'Status: Attended. Next session scheduled Oct 6.',
    usedIn: ['What Changed', 'Treatment signal'],
  },
  {
    id: 'src-lor',
    title: 'Letter of Representation',
    kind: 'legal',
    docType: 'Outgoing Letter',
    date: '2026-06-18',
    author: 'John Smith, Lead Attorney',
    origin: 'Clio · Documents / Correspondence',
    sections: [
      {
        heading: 'To',
        body: 'Jane Doe, Bodily Injury Adjuster, ABC Insurance. Claim #ABC-4471-209.',
      },
      {
        heading: 'Body',
        body: 'Please be advised that this firm represents John Sapini for injuries sustained in the May 3, 2026 collision involving your insured, Derek Hollis.',
      },
    ],
    excerpt: 'This firm represents John Sapini for injuries sustained in the May 3, 2026 collision involving your insured, Derek Hollis.',
    usedIn: ['Case Story · Insurance'],
  },
  {
    id: 'src-policy',
    title: 'Insurance Policy Disclosure',
    kind: 'insurance',
    docType: 'Coverage Disclosure Letter',
    date: '2026-09-14',
    author: 'Jane Doe, ABC Insurance',
    origin: 'Clio · Documents / Insurance',
    sections: [
      {
        heading: 'Policy',
        body: 'Insured: Derek Hollis. Policy #PA-88213-07. Effective 01/01/2026 – 01/01/2027.',
      },
      {
        heading: 'Limits',
        body: 'Bodily injury liability: $500,000 per person / $1,000,000 per accident. Certified declarations page to follow under separate cover.',
      },
    ],
    excerpt: 'Bodily injury liability: $500,000 per person / $1,000,000 per accident.',
    usedIn: ['Coverage signal', 'Case Summary', 'Case Story · Coverage'],
  },
  {
    id: 'src-valuation',
    title: 'Case Valuation Memo',
    kind: 'internal',
    docType: 'Internal Memo',
    date: '2026-09-20',
    author: 'John Smith, Lead Attorney',
    origin: 'Clio · Notes (internal)',
    sections: [
      {
        heading: 'Basis',
        body: 'Specials to date: $38,200 medical. Projected future care: injection series and continued PT. Comparable verdicts in county for single-level lumbar herniation, non-surgical: $180K–$320K.',
      },
      {
        heading: 'Estimate',
        body: 'Working valuation $250,000. Revisit after follow-up MRI and pain-management consult.',
      },
    ],
    excerpt: 'Working valuation $250,000. Revisit after follow-up MRI and pain-management consult.',
    usedIn: ['Case Value signal'],
  },
  {
    id: 'src-ledger',
    title: 'Firm Expense Ledger',
    kind: 'financial',
    docType: 'Clio Expense Report',
    date: '2026-09-30',
    origin: 'Clio · Billing / Expenses',
    sections: [
      {
        heading: 'Totals',
        body: 'Total firm spend: $12,420. September: $2,100 (records retrieval $640, follow-up MRI advance $1,460).',
      },
    ],
    excerpt: 'Total firm spend: $12,420. September: $2,100.',
    usedIn: ['Firm Spend signal'],
  },
  {
    id: 'src-liens',
    title: 'Medical Lien Summary',
    kind: 'financial',
    docType: 'Lien Tracker',
    date: '2026-09-26',
    origin: 'Clio · Documents / Liens',
    sections: [
      {
        heading: 'Balances',
        body: 'St. Mary’s Regional $6,850 · Westbrook Imaging $7,400 · Westbrook Orthopedics $11,950 · Core Motion PT $12,000. Total: $38,200.',
      },
    ],
    excerpt: 'Total outstanding medical liens: $38,200.',
    usedIn: ['Case Summary', 'Financials'],
  },
  {
    id: 'src-call',
    title: 'Communication History',
    kind: 'communication',
    docType: 'Client Call Log',
    date: '2026-09-14',
    author: 'Maria Ortiz, Paralegal',
    origin: 'Clio · Communications',
    sections: [
      {
        heading: 'Last contact',
        body: 'Sept 14 — Phone call with John Sapini (11 min). Client reports back pain unchanged, sleeping poorly. Confirmed PT schedule.',
      },
      {
        heading: 'Since then',
        body: 'No calls, emails, or texts with the client logged after Sept 14. Medical authorization sent by mail Sept 22 — no response.',
      },
    ],
    excerpt: 'No calls, emails, or texts with the client logged after Sept 14.',
    usedIn: ['Last client contact', 'Needs Attention'],
  },
  {
    id: 'src-email-insurer',
    title: 'Email from ABC Insurance',
    kind: 'communication',
    docType: 'Inbound Email',
    date: '2026-09-27',
    author: 'Jane Doe, ABC Insurance',
    origin: 'Clio · Communications',
    sections: [
      {
        heading: 'Subject',
        body: 'Re: Sapini / Claim #ABC-4471-209 — additional records',
      },
      {
        heading: 'Message',
        body: 'To continue our evaluation, please provide updated orthopedic notes and complete physical therapy records through the present. We ask that these be provided within 14 days.',
      },
    ],
    excerpt: 'Please provide updated orthopedic notes and complete physical therapy records through the present.',
    usedIn: ['What Changed', 'Needs Attention', 'Case Summary'],
  },
  {
    id: 'src-mri2',
    title: 'Follow-up Lumbar MRI',
    kind: 'medical',
    docType: 'Radiology Report',
    date: '2026-09-28',
    author: 'Westbrook Imaging Center',
    origin: 'Clio · Documents / Medical',
    sections: [
      {
        heading: 'Comparison',
        body: 'Compared with MRI of May 14, 2026.',
      },
      {
        heading: 'Findings',
        body: 'Persistent L4–L5 left paracentral disc herniation, now 6 mm, with continued contact of the left L5 nerve root.',
      },
      {
        heading: 'Recommendation',
        body: 'Referred by Dr. Lee for pain-management consult regarding epidural steroid injection.',
      },
    ],
    excerpt: 'Persistent L4–L5 disc herniation, now 6 mm, with continued contact of the left L5 nerve root.',
    usedIn: ['What Changed', 'Primary Injuries · Lower back', 'Case Story · Injury'],
  },
  {
    id: 'src-lee-request',
    title: 'Email from Dr. Lee’s Office',
    kind: 'communication',
    docType: 'Inbound Email',
    date: '2026-09-30',
    author: 'Westbrook Orthopedics Billing',
    origin: 'Clio · Communications',
    sections: [
      {
        heading: 'Message',
        body: 'Could you confirm the case is still active and whether coverage has been identified? Our lien balance is $11,950. Updated treatment notes will follow after the Oct 3 visit.',
      },
    ],
    excerpt: 'Could you confirm the case is still active and whether coverage has been identified?',
    usedIn: ['What Changed', 'Needs Attention'],
  },
  {
    id: 'src-auth',
    title: 'Medical Authorization (HIPAA)',
    kind: 'legal',
    docType: 'Outgoing Form',
    date: '2026-09-22',
    author: 'Maria Ortiz, Paralegal',
    origin: 'Clio · Documents / Forms',
    sections: [
      {
        heading: 'Status',
        body: 'Mailed to client Sept 22 for signature. Required to release updated records from Westbrook Orthopedics. Not yet returned.',
      },
    ],
    excerpt: 'Required to release updated records from Westbrook Orthopedics. Not yet returned.',
    usedIn: ['Waiting On'],
  },
  {
    id: 'src-tasks',
    title: 'Clio Task List',
    kind: 'internal',
    docType: 'Tasks',
    date: '2026-10-02',
    origin: 'Clio · Tasks',
    sections: [
      {
        heading: 'Overdue',
        body: 'Client check-in call — due Sept 28 — M. Ortiz. Send updated records to ABC Insurance — due Sept 30 — J. Smith.',
      },
      {
        heading: 'Upcoming',
        body: 'Obtain certified declarations page — due Oct 5 — J. Smith. Respond to Dr. Lee’s office — due Oct 3 — M. Ortiz.',
      },
    ],
    excerpt: '2 tasks overdue: client check-in call (Sept 28), updated records to insurer (Sept 30).',
    usedIn: ['Needs Attention'],
  },
]

export const sourceById = Object.fromEntries(sources.map((s) => [s.id, s])) as Record<string, Source>
