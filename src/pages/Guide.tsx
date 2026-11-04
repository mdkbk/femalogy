import { useState } from 'react'
import { api, type Phase } from '../api'
import { Disclaimer, ErrorBox, Loading, MythCard, TipCard } from '../components/ui'
import { PHASE, PHASES, useLoad } from '../lib'

const TOPICS: [string, string, string[]][] = [
  ['all', 'All', []],
  ['body', 'Body', ['body', 'temperature', 'habits_rest']],
  ['food', 'Food', ['food_nutrition', 'drinks']],
  ['mood', 'Mood', ['emotions', 'energy_mood']],
  ['movement', 'Movement', ['movement']],
]

export default function Guide() {
  const now = useLoad(() => api.today().then((t) => t.phase).catch(() => null))
  const [picked, setPicked] = useState<Phase | null>(null)
  const phase: Phase = picked ?? now.data ?? 'menstrual'
  const guide = useLoad(() => api.guide(phase), [phase])
  const myths = useLoad(() => api.myths())
  const [topic, setTopic] = useState('all')
  const cats = TOPICS.find((t) => t[0] === topic)![2]
  const tips = (guide.data?.tips ?? []).filter((t) => topic === 'all' || cats.includes(t.category))
  const ph = PHASE[phase]

  return (
    <main className="page" style={{ gap: 28 }}>
      <div className="page-head fx-up">
        <h1>Phase guide</h1>
        <p className="muted" style={{ maxWidth: 620 }}>
          What's going on in each phase and what can help. Every tip shows how strong the research is and links to the papers it comes from.
        </p>
      </div>

      <div role="tablist" aria-label="Phases" className="tabs fx-up fx-d1">
        {PHASES.map((p) => {
          const on = p === phase
          return (
            <button key={p} type="button" role="tab" aria-selected={on} onClick={() => { setPicked(p); setTopic('all') }}
              style={on ? { background: PHASE[p].tint, borderColor: PHASE[p].color } : undefined}>
              <span className="dot" style={{ background: PHASE[p].color }} aria-hidden="true" />
              {PHASE[p].label}
              {p === now.data && <span className="eyebrow" style={{ fontSize: 12 }}>· now</span>}
            </button>
          )
        })}
      </div>

      {guide.loading && !guide.data && <Loading height={160} />}
      {guide.error && <ErrorBox message={guide.error.message} retry={guide.reload} />}
      {guide.data && (
        <>
          <section className="hero fx-up" style={{ background: ph.tint, borderRadius: 28, padding: '28px 32px', gap: 8, flexDirection: 'column', alignItems: 'flex-start' }}>
            <h2 style={{ fontSize: 30, fontWeight: 600 }}>{guide.data.title}</h2>
            <p style={{ fontSize: 18, maxWidth: 680 }}>{guide.data.summary}</p>
          </section>

          <div role="group" aria-label="Filter by topic" className="pills">
            {TOPICS.map(([id, label]) => (
              <button key={id} type="button" className="pill" aria-pressed={topic === id} onClick={() => setTopic(id)}>{label}</button>
            ))}
          </div>

          <div className="tips">
            {tips.map((t) => <TipCard key={t.id} tip={t} />)}
          </div>
          {tips.length === 0 && <p className="muted">No tips on this topic for this phase yet.</p>}
        </>
      )}

      <section aria-labelledby="myths-title" style={{ display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 12 }}>
        <div className="section-head">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <h2 id="myths-title">Myth checks</h2>
            <p className="muted">Popular cycle claims, and what research actually found.</p>
          </div>
        </div>
        {myths.error && <ErrorBox message={myths.error.message} retry={myths.reload} />}
        <div className="tips">
          {(myths.data ?? []).map((m) => <MythCard key={m.id} myth={m} />)}
        </div>
      </section>

      <Disclaimer />
    </main>
  )
}
