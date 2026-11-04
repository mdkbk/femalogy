import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, localToday, type Period } from '../api'
import { useAuth } from '../auth'
import { CycleRing, Disclaimer, ErrorBox, FirstPeriod, InfoIcon, InsightCard, Loading, MythCard, TipCard, WarnIcon } from '../components/ui'
import { daysBetween, fmtLong, fmtShort, PHASE, useLoad } from '../lib'

/** Period logging right on Today: everything else is estimated from these dates. */
function PeriodQuick({ periods, late, onSaved }: { periods: Period[]; late: boolean; onSaved: () => void }) {
  const today = localToday()
  const latest = periods.length ? periods[periods.length - 1] : null
  const ongoing = latest && !latest.end_date && daysBetween(latest.start_date, today) <= 14 ? latest : null
  const [open, setOpen] = useState(false)
  const [date, setDate] = useState(today)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const run = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true)
    setMsg(null)
    try {
      await fn()
      setMsg({ ok: true, text: done })
      setOpen(false)
      onSaved()
    } catch (x) {
      setMsg({ ok: false, text: (x as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="period-quick">
      {late && !ongoing && <p style={{ fontWeight: 700 }}>Has your period started? Log it so your phases stay right.</p>}
      {ongoing ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12 }}>
          <span className="small" style={{ fontWeight: 700 }}>
            Period since {fmtShort(ongoing.start_date)} · day {daysBetween(ongoing.start_date, today) + 1}
          </span>
          {!open && (
            <button type="button" className="btn small quiet" disabled={busy}
              onClick={() => run(() => api.updatePeriod(ongoing.id, ongoing.start_date, today), 'Saved. Your period end is logged.')}>
              My period ended today
            </button>
          )}
          {!open && <button type="button" className="linklike" onClick={() => { setDate(today); setOpen(true) }}>Ended another day</button>}
          {open && (
            <form className="row" style={{ alignItems: 'flex-end' }}
              onSubmit={(e) => { e.preventDefault(); run(() => api.updatePeriod(ongoing.id, ongoing.start_date, date), 'Saved. Your period end is logged.') }}>
              <label className="field">Ended on
                <input type="date" required min={ongoing.start_date} max={today} value={date} onChange={(e) => setDate(e.target.value)} />
              </label>
              <button className="btn small" disabled={busy}>Save</button>
              <button type="button" className="btn small quiet" onClick={() => setOpen(false)}>Cancel</button>
            </form>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12 }}>
          {!open && (
            <button type="button" className="btn small quiet" disabled={busy}
              onClick={() => run(() => api.addPeriod(today, null), 'Saved. Your phases are updated.')}>
              <span className="dot" style={{ background: '#C0465F' }} aria-hidden="true" />
              My period started today
            </button>
          )}
          {!open && <button type="button" className="linklike" onClick={() => { setDate(today); setOpen(true) }}>It started another day</button>}
          {open && (
            <form className="row" style={{ alignItems: 'flex-end' }}
              onSubmit={(e) => { e.preventDefault(); run(() => api.addPeriod(date, null), 'Saved. Your phases are updated.') }}>
              <label className="field">Started on
                <input type="date" required max={today} value={date} onChange={(e) => setDate(e.target.value)} />
              </label>
              <button className="btn small" disabled={busy}>Save</button>
              <button type="button" className="btn small quiet" onClick={() => setOpen(false)}>Cancel</button>
            </form>
          )}
          <Link to="/plan" className="small" style={{ fontWeight: 700 }}>All periods</Link>
        </div>
      )}
      {msg && <p role="status" className={msg.ok ? 'success small' : 'error small'}>{msg.text}</p>}
    </div>
  )
}

const FLAG_TEXT: Record<string, string> = {
  period_late: 'Your period is later than expected.',
  high_variability: 'Your cycle length has been changing a lot.',
  needs_more_data: 'Log at least 2 cycles for better estimates.',
}

export default function Today() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => Promise.all([api.today(), api.sync(), api.periods()]))
  const [area, setArea] = useState('all')

  if (loading && !data) {
    return (
      <main className="page">
        <Loading height={380} />
        <Loading height={120} />
      </main>
    )
  }
  if (error?.status === 409) {
    return (
      <main className="page">
        <FirstPeriod onDone={reload} />
      </main>
    )
  }
  if (error || !data) {
    return (
      <main className="page">
        <ErrorBox message={error?.message ?? 'Something went wrong'} retry={reload} />
      </main>
    )
  }

  const [t, s, periods] = data
  const ph = PHASE[t.phase]
  const ovuAgo = daysBetween(t.ovulation_date_estimate, t.date)
  const confidence = { low: 'Low', medium: 'Medium', high: 'High' }[t.confidence]
  const areas = s.areas.filter((a) => a.tips.length || a.personal.length || a.myths.length)
  const shown = area === 'all' ? areas : areas.filter((a) => a.id === area)
  const personalCount = s.areas.reduce((n, a) => n + a.personal.length, 0)
  const progress = Math.min(1, s.cycles_with_checkins / s.cycles_needed)

  return (
    <main className="page">
      <section aria-labelledby="phase-title" className="hero fx-up" style={{ background: ph.tint }}>
        <div className="hero-ring">
          <CycleRing day={t.cycle_day} length={t.cycle_length_estimate} periodLength={t.period_length_estimate}
            ovulationDay={t.ovulation_day_estimate} phase={t.phase} />
        </div>
        <div className="hero-text">
          <p style={{ color: ph.ink, fontWeight: 700 }}>
            {fmtLong(t.date)}
            {user?.display_name ? ` · Hi ${user.display_name}` : ''}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 18, color: 'var(--ink-2)' }}>You're in your</span>
            <h1 id="phase-title">{t.phase_title}</h1>
          </div>
          <p style={{ fontSize: 18, maxWidth: 480 }}>{t.guide.summary}</p>
          <div className="pills">
            <span className="chip" style={{ color: ph.ink }}>
              <span className="dot" style={{ background: ph.color, width: 8, height: 8 }} aria-hidden="true" />
              Cycle day {t.cycle_day}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '12px 20px', marginTop: 4 }}>
            <Link to="/check-in" className="btn">Check in for today</Link>
            <Link to="/guide" className="link-strong" style={{ color: ph.ink }}>About all four phases</Link>
          </div>
          <PeriodQuick periods={periods} late={t.flags.includes('period_late')} onSaved={reload} />
        </div>
      </section>

      {t.red_flags.length > 0 && (
        <div className="alert fx-up" role="alert">
          <WarnIcon />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {t.red_flags.map((r) => <p key={r.id}>{r.text}</p>)}
          </div>
        </div>
      )}

      <section aria-label="Cycle estimates" className="fx-up fx-d1" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="strip">
          <Link to="/plan" className="stat fx-card">
            <span className="label">Next period</span>
            <span className="value" style={{ color: 'var(--accent)' }}>
              {t.days_until_next_period === 0 ? 'any day now' : `in ${t.days_until_next_period} day${t.days_until_next_period === 1 ? '' : 's'}`}
            </span>
            <span className="muted">around {fmtShort(t.next_period_estimate)}</span>
          </Link>
          <Link to="/plan" className="stat fx-card">
            <span className="label">Ovulation (estimate)</span>
            <span className="value">{fmtShort(t.ovulation_date_estimate)}</span>
            <span className="muted">
              {ovuAgo > 0 ? `${ovuAgo} day${ovuAgo === 1 ? '' : 's'} ago` : ovuAgo === 0 ? 'today' : `in ${-ovuAgo} days`}
            </span>
          </Link>
          <Link to="/plan" className="stat fx-card">
            <span className="label">Your cycle</span>
            <span className="value">~{t.cycle_length_estimate} days</span>
            <span className="muted">
              {confidence} confidence · {t.complete_cycles_logged} cycle{t.complete_cycles_logged === 1 ? '' : 's'} logged
            </span>
          </Link>
        </div>
        <p className="note" style={{ margin: '0 8px' }}>
          <InfoIcon />
          {t.flags.filter((f) => FLAG_TEXT[f]).map((f) => FLAG_TEXT[f]).join(' ')} All dates are estimates that improve as you log more cycles. Not for contraception.
        </p>
      </section>

      <section aria-labelledby="sync-title" className="fx-up fx-d2" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div className="section-head">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <h2 id="sync-title">Your sync plan</h2>
            <p className="muted">Your own patterns first, then what research says, then myths worth knowing.</p>
          </div>
          <div role="group" aria-label="Filter by area" className="pills">
            {[{ id: 'all', title: 'All' }, ...areas].map((a) => (
              <button key={a.id} type="button" className="pill" aria-pressed={area === a.id} onClick={() => setArea(a.id)}>
                {a.title}
              </button>
            ))}
          </div>
        </div>

        {s.personal_status === 'learning' && (
          <div className="learning">
            <div style={{ flex: '999 1 320px', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <strong>Femalogy is learning your pattern</strong>
              <span className="muted small">
                Check in through {s.cycles_needed} cycles and your plan starts using your own data, not just general research.
                {' '}{s.cycles_with_checkins} of {s.cycles_needed} cycles so far.
              </span>
            </div>
            <div className="progress" aria-hidden="true"><span style={{ width: `${progress * 100}%` }} /></div>
          </div>
        )}
        {s.personal_status === 'ready' && personalCount === 0 && (
          <p className="note"><InfoIcon />Nothing in your check-ins stands out for this phase. Your days here look like the rest of your cycle.</p>
        )}

        {shown.map((a) => (
          <div key={a.id} className="area">
            <h3>{a.title}</h3>
            <div className="tips">
              {a.personal.map((i) => <InsightCard key={i.id} insight={i} />)}
              {a.tips.map((tip) => <TipCard key={tip.id} tip={tip} />)}
              {a.myths.map((m) => <MythCard key={m.id} myth={m} />)}
            </div>
          </div>
        ))}
      </section>

      <Disclaimer>{s.disclaimer}</Disclaimer>
    </main>
  )
}
