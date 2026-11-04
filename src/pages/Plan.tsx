import { useState } from 'react'
import { api, localToday, toISO, type CalendarDay, type Period } from '../api'
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

function PeriodRow({ p, onChange }: { p: Period; onChange: () => void }) {
  const [editing, setEditing] = useState(false)
  const [start, setStart] = useState(p.start_date)
  const [end, setEnd] = useState(p.end_date ?? '')
  const [err, setErr] = useState('')
  const len = p.end_date ? daysBetween(p.start_date, p.end_date) + 1 : null
  if (!editing) {
    return (
      <li>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <strong>{fmtDayMonth(p.start_date)}{p.end_date ? ` to ${fmtDayMonth(p.end_date)}` : ''}</strong>
          <span className="small muted">{len ? `${len} days` : 'End not logged yet'}</span>
        </div>
        <button type="button" className="btn small quiet" aria-label={`Edit period starting ${fmtDayMonth(p.start_date)}`} onClick={() => setEditing(true)}>Edit</button>
      </li>
    )
  }
  return (
    <li style={{ flexDirection: 'column', alignItems: 'stretch' }}>
      <div className="row">
        <label className="field">Started<input type="date" value={start} max={localToday()} onChange={(e) => setStart(e.target.value)} /></label>
        <label className="field">Ended<input type="date" value={end} min={start} max={localToday()} onChange={(e) => setEnd(e.target.value)} /></label>
      </div>
      {err && <p className="error small" role="alert">{err}</p>}
      <div className="row">
        <button type="button" className="btn small" onClick={async () => {
          try { await api.updatePeriod(p.id, start, end || null); setEditing(false); onChange() } catch (x) { setErr((x as Error).message) }
        }}>Save</button>
        <button type="button" className="btn small quiet" onClick={() => setEditing(false)}>Cancel</button>
        <button type="button" className="btn small quiet" style={{ color: '#9c3a2a' }} onClick={async () => {
          await api.deletePeriod(p.id); onChange()
        }}>Delete</button>
      </div>
    </li>
  )
}

export default function Plan() {
  const today = localToday()
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [version, setVersion] = useState(0)
  const plan = useLoad(() => api.plan(today, 56), [version])
  const periods = useLoad(() => api.periods(), [version])
  const [start, setStart] = useState(today)
  const [end, setEnd] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
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
          <section className="card" aria-labelledby="log-title" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <h2 id="log-title" style={{ fontSize: 22, fontWeight: 600 }}>Log a period</h2>
            <form style={{ display: 'flex', flexDirection: 'column', gap: 14 }} onSubmit={async (e) => {
              e.preventDefault()
              try {
                await api.addPeriod(start, end || null)
                setMsg({ ok: true, text: 'Saved. Your phases are updated.' })
                setEnd('')
                refresh()
              } catch (x) {
                setMsg({ ok: false, text: (x as Error).message })
              }
            }}>
              <div className="row">
                <label className="field">Started<input type="date" required value={start} max={today} onChange={(e) => setStart(e.target.value)} /></label>
                <label className="field">Ended (optional)<input type="date" value={end} min={start} max={today} onChange={(e) => setEnd(e.target.value)} /></label>
              </div>
              <button className="btn">Save period</button>
            </form>
            {msg && <p role="status" className={msg.ok ? 'success small' : 'error small'}>{msg.text}</p>}
            <p className="small muted">Still bleeding? Leave the end empty and add it later.</p>
          </section>

          <section className="card" aria-labelledby="hist-title" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <h2 id="hist-title" style={{ fontSize: 22, fontWeight: 600 }}>Your periods</h2>
            {periods.data && periods.data.length === 0 && <p className="muted small">Nothing logged yet.</p>}
            <ul className="history">
              {[...(periods.data ?? [])].reverse().map((p) => <PeriodRow key={p.id + p.start_date + p.end_date} p={p} onChange={refresh} />)}
            </ul>
          </section>
        </div>
      </div>
    </main>
  )
}
