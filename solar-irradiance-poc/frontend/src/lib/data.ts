import { useEffect, useState } from 'react'

/* Types mirror docs/output_contract.md (exported by scripts/export_frontend_data.py) */

export interface Site {
  site_id: string
  name: string
  latitude: number
  longitude: number
  climate_zone: string
}

export interface ModelMetrics {
  mae: number
  rmse: number
  nrmse: number
  bias: number
  skill: number
}

export interface SiteMetrics {
  name: string
  climate_zone: string
  ml_model_p50: ModelMetrics
  raw_nwp: ModelMetrics
  persistence: ModelMetrics
  coverage: number
}

export interface Metrics {
  overall: {
    ml_model_p50: ModelMetrics
    raw_nwp: ModelMetrics
    persistence: ModelMetrics
    p10_p90_coverage: number
    quantile_crossings?: number
  }
  by_site: Record<string, SiteMetrics>
  by_confidence?: Record<string, { count: number; mae: number }>
}

export interface Monthly {
  months: string[]
  overall: Record<'ml_model_p50' | 'raw_nwp' | 'persistence', (number | null)[]>
  by_site: Record<string, (number | null)[]>
}

export type Confidence = 'High' | 'Medium' | 'Low' | null
type Series = (number | null)[]

export interface DayForecast {
  confidence: Confidence
  actual: Series
  p10: Series
  p50: Series
  p90: Series
  nwp: Series
  persistence: Series
  clearsky: Series
}

export interface SiteForecasts {
  site_id: string
  hours: number[]
  days: Record<string, DayForecast>
}

const cache = new Map<string, Promise<unknown>>()

function fetchJson<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const p = fetch(`${import.meta.env.BASE_URL}data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`Failed to load ${path} (${r.status})`)
      return r.json()
    })
    p.catch(() => cache.delete(path))
    cache.set(path, p)
  }
  return cache.get(path) as Promise<T>
}

export interface Loadable<T> {
  data: T | null
  error: string | null
  loading: boolean
}

function useJson<T>(path: string | null): Loadable<T> {
  const [state, setState] = useState<{ path: string | null; data: T | null; error: string | null }>({
    path: null,
    data: null,
    error: null,
  })
  useEffect(() => {
    if (!path) return
    let alive = true
    fetchJson<T>(path)
      .then((data) => alive && setState({ path, data, error: null }))
      .catch((e: Error) => alive && setState({ path, data: null, error: e.message }))
    return () => {
      alive = false
    }
  }, [path])
  const current = state.path === path
  return {
    data: current ? state.data : null,
    error: current ? state.error : null,
    loading: !!path && !current,
  }
}

export const useSites = () => useJson<Site[]>('sites.json')
export const useMetrics = () => useJson<Metrics>('metrics.json')
export const useMonthly = () => useJson<Monthly>('monthly.json')
export const useSiteForecasts = (siteId: string | null) =>
  useJson<SiteForecasts>(siteId ? `forecasts/${siteId}.json` : null)

/* ---------- Helpers ---------- */

export const sum = (xs: Series) => xs.reduce<number>((a, v) => a + (v ?? 0), 0)

/** Date with the largest clear-sky minus actual GHI gap (i.e. the cloudiest day). */
export function cloudiestDate(f: SiteForecasts): string | null {
  let best: string | null = null
  let bestGap = -Infinity
  for (const [date, d] of Object.entries(f.days)) {
    const gap = sum(d.clearsky) - sum(d.actual)
    if (gap > bestGap) {
      bestGap = gap
      best = date
    }
  }
  return best
}

export const fmt = (v: number | null | undefined, digits = 1) =>
  v == null || Number.isNaN(v)
    ? '—'
    : v.toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export const formatDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

export const formatMonth = (ym: string) =>
  new Date(`${ym}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'short' })

export const hourLabel = (h: number) => `${String(h).padStart(2, '0')}:00`
