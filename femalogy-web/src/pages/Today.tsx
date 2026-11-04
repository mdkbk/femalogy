import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { PeriodSheet } from '../components/PeriodSheet'
import { useAuth } from '../auth'
import { CycleRing, Disclaimer, ErrorBox, FirstPeriod, InfoIcon, InsightCard, Loading, MythCard, TipCard, WarnIcon } from '../components/ui'
import { daysBetween, fmtDayMonth, fmtLong, fmtShort, PHASE, useLoad } from '../lib'

const FLAG_TEXT: Record<string, string> = {
  period_late: 'Your period is later than expected.',
  high_variability: 'Your cycle length has been changing a lot.',
  needs_more_data: 'Log at least 2 cycles for better estimates.',
}

export default function Today() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useLoad(() => Promise.all([api.today(), api.sync()]))
  const [area, setArea] = useState('all')
  const [logging, setLogging] = useState(false)
  const [sheetMonth, setSheetMonth] = useState<string | undefined>(undefined)
  const [gapBusy, setGapBusy] = useState(false)

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

  const [t, s] = data
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
          {t.flags.includes('period_late') && (
            <p style={{ fontWeight: 700, color: ph.ink }}>Has your period started? Log it so your phases stay right.</p>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginTop: 4 }}>
            <Link to="/check-in" className="btn">Check in for today</Link>
            <button type="button" className="btn quiet" onClick={() => { setSheetMonth(undefined); setLogging(true) }}>
              <span className="dot" style={{ background: '#C0465F' }} aria-hidden="true" />
              Log period
            </button>
          </div>
          <Link to="/guide" className="link-strong" style={{ color: ph.ink, alignSelf: 'flex-start' }}>About all four phases</Link>
        </div>
      </section>

      {t.possible_missed_period && t.possible_missed_period_id && (
        <section className="card fx-up" aria-labelledby="gap-title"
          style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16, border: '1.5px dashed #d8bfb7', boxShadow: 'none' }}>
          <div style={{ flex: '999 1 320px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <strong id="gap-title">Did a period start around {fmtShort(t.possible_missed_period)}?</strong>
            <span className="small muted">
              There's a long gap in your log that looks like a period wasn't saved. Your estimates already allow for that,
              but telling us makes them more accurate.
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button type="button" className="btn small" onClick={() => { setSheetMonth(t.possible_missed_period!); setLogging(true) }}>
              Yes, add it
            </button>
            <button type="button" className="btn small quiet" disabled={gapBusy} onClick={async () => {
              setGapBusy(true)
              try { await api.confirmGap(t.possible_missed_period_id!); reload() } finally { setGapBusy(false) }
            }}>
              No, it was one long cycle
            </button>
          </div>
        </section>
      )}

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
            {t.next_period_latest > t.next_period_earliest && (
              <span className="small muted">likely {fmtDayMonth(t.next_period_earliest)} to {fmtDayMonth(t.next_period_latest)}</span>
            )}
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
      <PeriodSheet open={logging} startMonth={sheetMonth} onClose={() => setLogging(false)} onSaved={reload} />
    </main>
  )
}
