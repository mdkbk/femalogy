import { useEffect, useMemo, useRef, useState } from 'react'
import { api, localToday, toISO, type Period } from '../api'
import { fmtDayMonth, monthName, parseISO } from '../lib'

// One way to log periods, like Flo / Apple Health / Clue: tap the days you bled.
// Start and end are worked out from runs of consecutive days.

const ONGOING_DAYS = 5 // how many days to show for a period with no end logged yet
const MAX_DAYS = 15 // same limit as the backend

const addDays = (iso: string, n: number) => {
  const d = parseISO(iso)
  d.setDate(d.getDate() + n)
  return toISO(d)
}

function expand(p: Period, today: string): string[] {
  let end = p.end_date
  if (!end) {
    end = addDays(p.start_date, ONGOING_DAYS - 1)
    if (end > today) end = today
  }
  const out: string[] = []
  for (let d = p.start_date; d <= end; d = addDays(d, 1)) out.push(d)
  return out
}

function runs(days: Set<string>): { start: string; end: string }[] {
  const sorted = [...days].sort()
  const out: { start: string; end: string }[] = []
  for (const d of sorted) {
    const last = out[out.length - 1]
    if (last && addDays(last.end, 1) === d) last.end = d
    else out.push({ start: d, end: d })
  }
  return out
}

/** Turn the tapped days into the API calls that make the server match them. */
async function save(periods: Period[], days: Set<string>, today: string) {
  const want = runs(days)
  const expanded = periods.map((p) => ({ p, days: new Set(expand(p, today)) }))
  const used = new Set<string>()
  const patches: { p: Period; start: string; end: string | null }[] = []
  const posts: { start: string; end: string | null }[] = []

  for (const r of want) {
    const match = expanded.find((e) => !used.has(e.p.id) && [...e.days].some((d) => d >= r.start && d <= r.end))
    // a run that reaches today may still be going, so leave its end open
    const end = r.end === today ? null : r.end
    if (!match) {
      posts.push({ start: r.start, end })
      continue
    }
    used.add(match.p.id)
    const shownEnd = [...match.days].sort().pop()
    const unchanged = match.p.start_date === r.start && (match.p.end_date ?? shownEnd) === r.end
    if (!unchanged) patches.push({ p: match.p, start: r.start, end })
  }
  const deletes = periods.filter((p) => !used.has(p.id))

  for (const p of deletes) await api.deletePeriod(p.id)
  for (const x of patches) await api.updatePeriod(x.p.id, x.start, x.end)
  for (const x of posts) await api.addPeriod(x.start, x.end)
  return deletes.length + patches.length + posts.length
}

export function PeriodSheet({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const today = localToday()
  const ref = useRef<HTMLDialogElement>(null)
  const [periods, setPeriods] = useState<Period[] | null>(null)
  const [days, setDays] = useState<Set<string>>(new Set())
  const [month, setMonth] = useState(() => { const d = parseISO(today); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    const dlg = ref.current
    if (!dlg) return
    if (open && !dlg.open) {
      dlg.showModal()
      setErr('')
      const d = parseISO(today)
      setMonth(new Date(d.getFullYear(), d.getMonth(), 1))
      setPeriods(null)
      api.periods().then((ps) => {
        setPeriods(ps)
        setDays(new Set(ps.flatMap((p) => expand(p, today))))
      }).catch((e: Error) => setErr(e.message))
    }
    if (!open && dlg.open) dlg.close()
  }, [open, today])

  const grid = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1)
    const start = new Date(first)
    start.setDate(1 - ((first.getDay() + 6) % 7))
    const cells: (string | null)[] = []
    for (let i = 0; i < 42; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      cells.push(d.getMonth() === month.getMonth() ? toISO(d) : null)
    }
    while (cells.length > 35 && cells.slice(-7).every((c) => c === null)) cells.splice(-7)
    return cells
  }, [month])

  const toggle = (iso: string) => {
    const next = new Set(days)
    if (next.has(iso)) next.delete(iso)
    else next.add(iso)
    setDays(next)
    setErr('')
  }

  const thisMonth = month.getFullYear() === parseISO(today).getFullYear() && month.getMonth() === parseISO(today).getMonth()
  const visibleRuns = runs(days).filter((r) => {
    const m = parseISO(r.start)
    const e = parseISO(r.end)
    const inMonth = (d: Date) => d.getFullYear() === month.getFullYear() && d.getMonth() === month.getMonth()
    return inMonth(m) || inMonth(e)
  })
  const tooLong = runs(days).find((r) => Math.round((parseISO(r.end).getTime() - parseISO(r.start).getTime()) / 86400000) + 1 > MAX_DAYS)

  return (
    <dialog ref={ref} className="sheet" aria-labelledby="sheet-title" onClose={onClose}
      onClick={(e) => { if (e.target === ref.current) onClose() }}>
      <div className="sheet-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <h2 id="sheet-title" style={{ fontSize: 26, fontWeight: 600 }}>Period days</h2>
          <p className="muted small">Tap each day you had your period. Femalogy works out the start and end from these.</p>
        </div>

        <div className="cal-head">
          <button type="button" className="round" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <h3 aria-live="polite" style={{ fontSize: 20, fontWeight: 600 }}>{monthName(month)}</h3>
          <button type="button" className="round" aria-label="Next month" disabled={thisMonth} style={{ opacity: thisMonth ? 0.35 : 1 }}
            onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>

        <div className="week" aria-hidden="true">
          {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => <span key={i} className="wd">{d}</span>)}
        </div>
        <div className="week" style={{ opacity: periods ? 1 : 0.4 }}>
          {grid.map((iso, i) => {
            if (!iso) return <span key={i} />
            const on = days.has(iso)
            const future = iso > today
            return (
              <button key={iso} type="button" className={`pday${on ? ' on' : ''}${iso === today ? ' today' : ''}`}
                aria-pressed={on} disabled={future || !periods}
                aria-label={`${fmtDayMonth(iso)}${iso === today ? ', today' : ''}`}
                onClick={() => toggle(iso)}>
                {parseISO(iso).getDate()}
              </button>
            )
          })}
        </div>

        <p className="small" aria-live="polite" style={{ minHeight: 21, fontWeight: 600 }}>
          {visibleRuns.length
            ? visibleRuns.map((r) => {
                const n = Math.round((parseISO(r.end).getTime() - parseISO(r.start).getTime()) / 86400000) + 1
                return `${fmtDayMonth(r.start)}${n > 1 ? ` to ${fmtDayMonth(r.end)}` : ''} · ${n} day${n === 1 ? '' : 's'}${r.end === today ? ', still going' : ''}`
              }).join('   ')
            : <span className="muted">No period days this month</span>}
        </p>
        {tooLong && <p className="error small" role="alert">A period can't be longer than {MAX_DAYS} days. Check the days from {fmtDayMonth(tooLong.start)}.</p>}
        {err && <p className="error small" role="alert">{err}</p>}

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button type="button" className="btn" disabled={busy || !periods || !!tooLong} onClick={async () => {
            if (!periods) return
            setBusy(true)
            setErr('')
            try {
              await save(periods, days, today)
              onSaved()
              onClose()
            } catch (x) {
              setErr((x as Error).message)
              api.periods().then(setPeriods).catch(() => {})
            } finally {
              setBusy(false)
            }
          }}>{busy ? 'Saving…' : 'Save'}</button>
          <button type="button" className="btn quiet" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </dialog>
  )
}
