const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']

export const TODAY = new Date('2026-10-02T10:42:00')

function parse(iso: string) {
  return new Date(iso.length === 10 ? `${iso}T12:00:00` : iso)
}

export function fmtDate(iso: string, withYear = false) {
  const d = parse(iso)
  const base = `${MONTHS[d.getMonth()]} ${d.getDate()}`
  return withYear ? `${base}, ${d.getFullYear()}` : base
}

export function fmtTime(iso: string) {
  const d = parse(iso)
  const h = d.getHours()
  const m = d.getMinutes().toString().padStart(2, '0')
  return `${h % 12 || 12}:${m} ${h < 12 ? 'AM' : 'PM'}`
}

export function daysBetween(a: string, b: string) {
  return Math.round((parse(b).getTime() - parse(a).getTime()) / 86_400_000)
}

export function daysAgo(iso: string) {
  return daysBetween(iso, TODAY.toISOString().slice(0, 10))
}

export function fmtGap(days: number) {
  if (days < 14) return `${days}d`
  if (days < 60) return `${Math.round(days / 7)}w`
  return `${Math.round(days / 30)} mo`
}

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}
