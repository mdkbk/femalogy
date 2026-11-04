import { useEffect, useState } from 'react'
import { api, localToday, type CheckInInput, type RedFlag } from '../api'
import { CheckIcon, ErrorBox, LockIcon, WarnIcon } from '../components/ui'
import { fmtLong, PHASE, SYMPTOMS, useLoad } from '../lib'

const SCALES: { key: 'mood' | 'energy' | 'sleep_quality'; title: string; words: string[] }[] = [
  { key: 'mood', title: 'Mood', words: ['Very low', 'Low', 'Okay', 'Good', 'Great'] },
  { key: 'energy', title: 'Energy', words: ['Drained', 'Low', 'Okay', 'Good', 'High'] },
  { key: 'sleep_quality', title: 'Sleep last night', words: ['Very poor', 'Poor', 'Okay', 'Good', 'Great'] },
]

const LOCAL_FLAGS: Record<string, string> = {
  very_heavy_bleeding: 'Soaking through a pad or tampon every hour, or passing large clots, is worth getting checked by a doctor.',
  severe_pain: "Pain that stops you doing normal things, or doesn't ease with painkillers, should be checked by a doctor.",
}

export default function Checkin() {
  const day = localToday()
  const existing = useLoad(() => api.checkins())
  const today = useLoad(() => api.today().catch(() => null))
  const [form, setForm] = useState<CheckInInput>({ day, mood: null, energy: null, sleep_quality: null, symptoms: [], notes: null })
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [err, setErr] = useState('')
  const [flags, setFlags] = useState<RedFlag[]>([])

  useEffect(() => {
    const c = existing.data?.find((x) => x.day === day)
    if (c) setForm({ day, mood: c.mood, energy: c.energy, sleep_quality: c.sleep_quality, symptoms: c.symptoms, notes: c.notes })
  }, [existing.data, day])

  const set = (patch: Partial<CheckInInput>) => {
    setForm((f) => ({ ...f, ...patch }))
    setState('idle')
  }
  const toggle = (id: string) =>
    set({ symptoms: form.symptoms.includes(id) ? form.symptoms.filter((s) => s !== id) : [...form.symptoms, id] })

  const live = form.symptoms.filter((s) => LOCAL_FLAGS[s]).map((s) => LOCAL_FLAGS[s])
  const t = today.data
  const already = existing.data?.some((x) => x.day === day)

  return (
    <main className="page narrow">
      <div className="page-head fx-up">
        <p className="muted" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontWeight: 600 }}>
          {fmtLong(day)}
          {t && (
            <span className="badge" style={{ background: PHASE[t.phase].tint, color: PHASE[t.phase].ink, gap: 6 }}>
              <span className="dot" style={{ width: 8, height: 8, background: PHASE[t.phase].color }} aria-hidden="true" />
              {PHASE[t.phase].label} · day {t.cycle_day}
            </span>
          )}
        </p>
        <h1>How are you today?</h1>
        <p className="muted">
          Skip anything you don't feel like answering. After two cycles, this is how your sync plan learns your own pattern.
          {already ? ' You already checked in today, so saving updates it.' : ''}
        </p>
      </div>

      {existing.error && <ErrorBox message={existing.error.message} retry={existing.reload} />}

      <form
        style={{ display: 'flex', flexDirection: 'column', gap: 20 }}
        onSubmit={async (e) => {
          e.preventDefault()
          setState('saving')
          setErr('')
          try {
            const saved = await api.saveCheckin({ ...form, notes: form.notes?.trim() || null })
            setFlags(saved.red_flags)
            setState('saved')
          } catch (x) {
            setErr((x as Error).message)
            setState('idle')
          }
        }}
      >
        {SCALES.map((s, idx) => (
          <fieldset key={s.key} className={`card fx-up fx-d${Math.min(idx + 1, 3)}`}>
            <legend>{s.title}</legend>
            <div className="scale">
              {s.words.map((w, i) => {
                const n = i + 1
                const on = form[s.key] === n
                return (
                  <button key={n} type="button" aria-pressed={on} onClick={() => set({ [s.key]: on ? null : n })}>
                    <span className="n">{n}</span>
                    <span className="w">{w}</span>
                  </button>
                )
              })}
            </div>
          </fieldset>
        ))}

        <fieldset className="card">
          <legend>Anything you noticed?</legend>
          <div className="symptoms">
            {SYMPTOMS.map(([id, label]) => (
              <button key={id} type="button" aria-pressed={form.symptoms.includes(id)} onClick={() => toggle(id)}>{label}</button>
            ))}
          </div>
          {(live.length > 0 || flags.length > 0) && (
            <div className="alert" role="alert">
              <WarnIcon />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {(flags.length ? flags.map((f) => f.text) : live).map((text) => <p key={text}>{text}</p>)}
              </div>
            </div>
          )}
        </fieldset>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label htmlFor="notes" style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 600 }}>Notes</label>
          <textarea id="notes" className="input" rows={4} maxLength={2000} placeholder="Anything else about today"
            value={form.notes ?? ''} onChange={(e) => set({ notes: e.target.value })} />
          <p className="note"><LockIcon />Your notes are encrypted. Only you can read them.</p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16 }}>
          <button className="btn" disabled={state === 'saving'} style={{ minHeight: 52, padding: '0 36px', fontSize: 17 }}>
            {state === 'saving' ? 'Saving…' : 'Save check-in'}
          </button>
          {state === 'saved' && <p role="status" className="success"><CheckIcon />Saved. You can change it any time today.</p>}
          {err && <p role="alert" className="error">{err}</p>}
        </div>
      </form>
    </main>
  )
}
