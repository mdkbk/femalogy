import { useCallback, useEffect, useState } from 'react'
import type { Phase, Source, Tip } from './api'

/** Load data once (and again on reload()). Keeps loading/error state in one place. */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<{ status: number; message: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let alive = true
    setLoading(true)
    load()
      .then((d) => {
        if (!alive) return
        setData(d)
        setError(null)
      })
      .catch((e: { status?: number; message?: string }) => {
        if (!alive) return
        setError({ status: e.status ?? 0, message: e.message ?? 'Something went wrong' })
      })
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}

export const PHASES: Phase[] = ['menstrual', 'follicular', 'ovulation', 'luteal']

export const PHASE: Record<Phase, { label: string; name: string; color: string; tint: string; ink: string }> = {
  menstrual: { label: 'Period', name: 'Menstrual phase', color: '#C0465F', tint: '#F7DDE3', ink: '#7E2C40' },
  follicular: { label: 'Follicular', name: 'Follicular phase', color: '#EDBFA8', tint: '#FCEEE6', ink: '#7A3E25' },
  ovulation: { label: 'Ovulation', name: 'Ovulation (estimated)', color: '#E0A549', tint: '#FBEED6', ink: '#6E4709' },
  luteal: { label: 'Luteal', name: 'Luteal phase', color: '#9A7AAA', tint: '#EFE5F2', ink: '#5E4470' },
}

export const GRADE: Record<Tip['grade'], { label: string; bg: string; fg: string }> = {
  strong: { label: 'Strong evidence', bg: '#E4EFE6', fg: '#2D5B3C' },
  moderate: { label: 'Moderate evidence', bg: '#FBEDD5', fg: '#7A4E0C' },
  weak: { label: 'Weak evidence', bg: '#F3E6E2', fg: '#6E4A40' },
  personal: { label: 'Learns from you', bg: '#EFE5F2', fg: '#5E4470' },
}

export const CATEGORY: Record<string, string> = {
  body: 'Body',
  temperature: 'Temperature',
  habits_rest: 'Sleep and rest',
  food_nutrition: 'Food',
  drinks: 'Drinks',
  emotions: 'Mood',
  energy_mood: 'Energy and mood',
  movement: 'Movement',
}

export const SYMPTOMS: [string, string][] = [
  ['cramps', 'Cramps'],
  ['headache', 'Headache'],
  ['bloating', 'Bloating'],
  ['breast_tenderness', 'Breast tenderness'],
  ['acne', 'Acne'],
  ['back_pain', 'Back pain'],
  ['fatigue', 'Tiredness'],
  ['cravings', 'Cravings'],
  ['nausea', 'Nausea'],
  ['very_heavy_bleeding', 'Very heavy bleeding'],
  ['severe_pain', 'Severe pain'],
]

/** "Biggs 2011" from a source's author list. */
export function shortCite(s: Source): string {
  const surname = s.authors.split(',')[0].trim().split(' ')[0]
  return `${surname} ${s.year}`
}

const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const WD_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const MO_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

/** Parse YYYY-MM-DD as a local date (no timezone shift). */
export function parseISO(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
export const fmtShort = (iso: string) => {
  const d = parseISO(iso)
  return `${WD[d.getDay()]} ${d.getDate()} ${MO[d.getMonth()]}`
}
export const fmtDayMonth = (iso: string) => {
  const d = parseISO(iso)
  return `${d.getDate()} ${MO[d.getMonth()]}`
}
export const fmtLong = (iso: string) => {
  const d = parseISO(iso)
  return `${WD_LONG[d.getDay()]}, ${d.getDate()} ${MO_LONG[d.getMonth()]}`
}
export const monthName = (d: Date) => `${MO_LONG[d.getMonth()]} ${d.getFullYear()}`

export function daysBetween(a: string, b: string): number {
  return Math.round((parseISO(b).getTime() - parseISO(a).getTime()) / 86400000)
}
