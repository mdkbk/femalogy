import type { Phase } from '../api'

// Today page effects:
// - FlowBackground: slow rose-red waves rolling along the bottom of the screen.
// - HeroDrips: glossy 3D drops that slide down over the main card, leaving a wet
//   trail, then fall off its bottom edge toward the waves.
// Both are strongest during the period, lighter in other phases, purely decorative,
// and stop completely for anyone with "reduce motion" turned on (see styles.css).

const WAVES = [
  { fill: '#E7A3B1', height: '100%', duration: 38, reverse: false, bob: 0, d: 'M0,70 C320,10 320,130 640,70 S960,10 1280,70 S1600,130 1920,70 S2240,10 2560,70 V200 H0 Z' },
  { fill: '#C0465F', height: '78%', duration: 26, reverse: true, bob: -3, d: 'M0,80 C320,30 320,130 640,80 S960,30 1280,80 S1600,130 1920,80 S2240,30 2560,80 V200 H0 Z' },
  { fill: '#8E2F47', height: '52%', duration: 18, reverse: false, bob: -6, d: 'M0,90 C320,50 320,130 640,90 S960,50 1280,90 S1600,130 1920,90 S2240,50 2560,90 V200 H0 Z' },
]

const strength = (phase: Phase) => (phase === 'menstrual' ? 1 : phase === 'luteal' ? 0.65 : 0.5)

export function FlowBackground({ phase }: { phase: Phase }) {
  return (
    <div className="waves" aria-hidden="true" style={{ opacity: 0.3 * strength(phase) }}>
      {WAVES.map((w, i) => (
        <div key={i} className="wave-bob" style={{ animationDelay: `${w.bob}s` }}>
          <svg className="wave-slide" viewBox="0 0 2560 200" preserveAspectRatio="none"
            style={{ height: w.height, animationDuration: `${w.duration}s`, animationDirection: w.reverse ? 'reverse' : 'normal' }}>
            <path d={w.d} fill={w.fill} />
          </svg>
        </div>
      ))}
    </div>
  )
}

// x position across the card (%), drop size (px), and where it is in the 10s loop
const DRIPS = [
  { x: 92, size: 22, delay: 0.5 },
  { x: 62, size: 18, delay: 4 },
  { x: 4, size: 18, delay: 7.2 },
]

export function HeroDrips({ phase }: { phase: Phase }) {
  return (
    <div className="drips" aria-hidden="true" style={{ opacity: Math.min(1, 0.9 * strength(phase)) }}>
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <radialGradient id="drip3d" cx="35%" cy="58%" r="70%">
            <stop offset="0" stopColor="#EE8DA0" />
            <stop offset="0.5" stopColor="#B83A55" />
            <stop offset="1" stopColor="#5E1526" />
          </radialGradient>
        </defs>
      </svg>
      {DRIPS.map((d, i) => (
        <div key={i} className="drip" style={{ left: `${d.x}%`, animationDelay: `-${d.delay}s` }}>
          <span className="drip-trail" style={{ width: d.size / 2.9, left: d.size / 2 - d.size / 5.8, bottom: d.size * 1.2, animationDelay: `-${d.delay}s` }} />
          <div className="drip-wobble" style={{ animationDelay: `-${i}s` }}>
            <svg width={d.size} height={d.size * 1.36} viewBox="0 0 22 30">
              <path d="M11 0 C11 0 21 13 21 19 A10 10 0 0 1 1 19 C1 13 11 0 11 0 Z" fill="url(#drip3d)" />
              <ellipse cx="7.4" cy="17.5" rx="2" ry="3.6" fill="#fff" opacity="0.8" transform="rotate(18 7.4 17.5)" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  )
}

// Landing page: deeper "blood" waves only, with a thin wet shine along each crest.
const BLOOD = [
  { id: 'back', top: '#D35A72', bottom: '#A3304A', height: '100%', duration: 36, reverse: false, bob: 0, shine: 0.25,
    d: 'M0,70 C320,10 320,130 640,70 S960,10 1280,70 S1600,130 1920,70 S2240,10 2560,70' },
  { id: 'mid', top: '#B0263F', bottom: '#7A1429', height: '80%', duration: 24, reverse: true, bob: -3, shine: 0.22,
    d: 'M0,80 C320,30 320,130 640,80 S960,30 1280,80 S1600,130 1920,80 S2240,30 2560,80' },
  { id: 'front', top: '#8A1530', bottom: '#4A0716', height: '56%', duration: 17, reverse: false, bob: -6, shine: 0.18,
    d: 'M0,90 C320,50 320,130 640,90 S960,50 1280,90 S1600,130 1920,90 S2240,50 2560,90' },
]

export function BloodWaves() {
  return (
    <div className="blood-waves" aria-hidden="true">
      {BLOOD.map((w) => (
        <div key={w.id} className="wave-bob" style={{ animationDelay: `${w.bob}s` }}>
          <svg className="wave-slide" viewBox="0 0 2560 200" preserveAspectRatio="none"
            style={{ height: w.height, animationDuration: `${w.duration}s`, animationDirection: w.reverse ? 'reverse' : 'normal' }}>
            <defs>
              <linearGradient id={`blood-${w.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={w.top} />
                <stop offset="1" stopColor={w.bottom} />
              </linearGradient>
            </defs>
            <path d={`${w.d} V200 H0 Z`} fill={`url(#blood-${w.id})`} />
            <path d={w.d} fill="none" stroke="#fff" strokeOpacity={w.shine} strokeWidth="2" />
          </svg>
        </div>
      ))}
    </div>
  )
}
