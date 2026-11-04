import { useState } from 'react'
import { api, localToday, toISO, type CalendarDay } from '../api'
import { PeriodSheet } from '../components/PeriodSheet'
import { ErrorBox, FirstPeriod, Loading, PhaseLegend } from '../components/ui'
import { daysBetween, fmtDayMonth, fmtShort, monthName, parseISO, PHASE, useLoad } from '../lib'

function monthGrid(month: Date): { start: string; days: number } {
  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const last = new Date(month.getFullYear(), month.getMonth() + 1, 0)
  const start = new Date(first)
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7)) // back to Monday
  const end = new Date(last)
  end.setDate(last.getDate() + (6 - ((last.getDay() + 6) % 7))) // forward to Sunday
  return { start: toISO(start), days: daysBetween(toISO(start), toISO(end)) + 1 }
}

function Calendar({ month, setMonth, today }: { month: Date; setMonth: (d: Date) => void; today: string }) {
  const grid = monthGrid(month)
  const { data, loading } = useLoad<CalendarDay[]>(
    () => api.calendar(grid.start, grid.days).catch(() => []),
    [grid.start, grid.days],
  )
  const [selected, setSelected] = useState(today)
  const byDate = new Map((data ?? []).map((d) => [d.date, d.phase]))
  const cells: string[] = []
  for (let i = 0; i < grid.days; i++) {
    const d = parseISO(grid.start)
    d.setDate(d.getDate() + i)
    cells.push(toISO(d))
  }
  const sel = byDate.get(selected)
  const shift = (n: number) => setMonth(new Date(month.getFullYear(), month.getMonth() + n, 1))

  return (
    <section className="card cal" aria-labelledby="month-title" style={{ padding: 24 }}>
      <div className="cal-head">
        <button type="button" className="round" aria-label="Previous month" onClick={() => shift(-1)}>
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
        <h2 id="month-title" aria-live="polite">{monthName(month)}</h2>
        <button type="button" className="round" aria-label="Next month" onClick={() => shift(1)}>
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>
      <div className="week" aria-hidden="true">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <span key={d} className="wd">{d}</span>)}
      </div>
      <div className="week" style={{ opacity: loading ? 0.5 : 1, transition: 'opacity .2s' }}>
        {cells.map((iso) => {
          const p = byDate.get(iso)
          const inMonth = parseISO(iso).getMonth() === month.getMonth()
          const cls = ['day', iso > today && p ? 'predicted' : '', iso === today ? 'today' : '', inMonth ? '' : 'other'].join(' ')
          return (
            <button key={iso} type="button" className={cls} aria-pressed={iso === selected}
              aria-label={`${fmtShort(iso)}${p ? `, ${PHASE[p].label}` : ''}${iso > today && p ? ', predicted' : ''}${iso === today ? ', today' : ''}`}
              onClick={() => setSelected(iso)}
              style={{ background: p ? PHASE[p].tint : '#fff' }}>
              <span>{parseISO(iso).getDate()}</span>
              <span className="dot" style={{ width: 8, height: 8, background: p ? PHASE[p].color : 'transparent' }} aria-hidden="true" />
            </button>
          )
        })}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 12, paddingTop: 4 }}>
        <PhaseLegend />
        <p className="small muted" aria-live="polite">
          <strong style={{ color: 'var(--ink)' }}>{fmtShort(selected)}</strong>
          {sel ? ` · ${PHASE[sel].name}${selected > today ? ' (prediction)' : ''}` : ' · no data'}
        </p>
      </div>
    </section>
  )
}

export default function Plan() {
  const today = localToday()
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [version, setVersion] = useState(0)
  const plan = useLoad(() => api.plan(today, 56), [version])
  const periods = useLoad(() => api.periods(), [version])
  const [logging, setLogging] = useState(false)
  const refresh = () => setVersion((v) => v + 1)

  if (plan.error?.status === 409) {
    return <main className="page"><FirstPeriod onDone={refresh} /></main>
  }

  return (
    <main className="page" style={{ maxWidth: 1120, gap: 24 }}>
      <div className="page-head">
        <h1>Plan ahead</h1>
        <p className="muted">Your coming phases, and what you usually notice in each one. Past days come from what you logged; dashed days are predictions.</p>
      </div>

      <div className="two-col">
        <div className="main" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <Calendar key={version} month={month} setMonth={setMonth} today={today} />

          <section aria-labelledby="next-title" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 id="next-title" style={{ fontSize: 26, fontWeight: 600 }}>The next 8 weeks</h2>
            {plan.loading && !plan.data && <Loading height={240} />}
            {plan.error && plan.error.status !== 409 && <ErrorBox message={plan.error.message} retry={plan.reload} />}
            {plan.data && (
              <ol className="timeline">
                {plan.data.blocks.map((b, idx, all) => {
                  const ph = PHASE[b.phase]
                  // show her patterns once per phase, not on every repeat of it
                  const firstOfPhase = all.findIndex((x) => x.phase === b.phase) === idx
                  return (
                    <li key={b.start} className="block fx-card" style={{ background: ph.tint }}>
                      <div className="block-top">
                        <strong style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className="dot" style={{ background: ph.color }} aria-hidden="true" />{b.title}
                        </strong>
                        <span className="small" style={{ color: ph.ink, fontWeight: 700 }}>
                          {fmtShort(b.start)}{b.days > 1 ? ` to ${fmtShort(b.end)}` : ''} · {b.days} day{b.days === 1 ? '' : 's'}
                          {b.is_prediction ? ' · estimate' : b.start === today ? ' · now' : ''}
                        </span>
                      </div>
                      {firstOfPhase && b.personal.map((i) => (
                        <p key={i.id} className="small"><strong>{i.text}</strong> {i.suggestion}</p>
                      ))}
                    </li>
                  )
                })}
              </ol>
            )}
            {plan.data?.personal_status === 'learning' && (
              <p className="note small">Once you've checked in through 2 cycles, each phase here shows what you usually notice in it.</p>
            )}
          </section>
        </div>

        <div className="side">
          <section className="card" aria-labelledby="hist-title" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 id="hist-title" style={{ fontSize: 22, fontWeight: 600 }}>Your periods</h2>
            <p className="small muted">Every estimate comes from these dates, so the more you log, the better it gets.</p>
            <button type="button" className="btn" onClick={() => setLogging(true)}>
              <span className="dot" style={{ background: '#fff' }} aria-hidden="true" />
              Edit period days
            </button>
            {periods.data && periods.data.length === 0 && <p className="muted small">Nothing logged yet.</p>}
            <ul className="history">
              {[...(periods.data ?? [])].reverse().map((p) => {
                const len = p.end_date ? daysBetween(p.start_date, p.end_date) + 1 : null
                return (
                  <li key={p.id}>
                    <strong>{fmtDayMonth(p.start_date)}{p.end_date && p.end_date !== p.start_date ? ` to ${fmtDayMonth(p.end_date)}` : ''}</strong>
                    <span className="small muted">{len ? `${len} day${len === 1 ? '' : 's'}` : 'still going'}</span>
                  </li>
                )
              })}
            </ul>
          </section>
        </div>
      </div>
      <PeriodSheet open={logging} onClose={() => setLogging(false)} onSaved={refresh} />
    </main>
  )
}
