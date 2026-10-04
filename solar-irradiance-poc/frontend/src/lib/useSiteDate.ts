import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useSiteForecasts, type Site } from './data'

/** Site + date selection persisted in the URL (?site=&date=) so it carries across pages. */
export function useSiteDate(sites: Site[] | null) {
  const [params, setParams] = useSearchParams()
  const siteId = params.get('site') ?? sites?.[0]?.site_id ?? null
  const forecasts = useSiteForecasts(siteId)

  const dates = useMemo(() => (forecasts.data ? Object.keys(forecasts.data.days).sort() : []), [forecasts.data])
  const requested = params.get('date')
  const date = requested && dates.includes(requested) ? requested : (dates[0] ?? null)

  const update = (next: { site?: string; date?: string }) => {
    const p = new URLSearchParams(params)
    if (next.site) p.set('site', next.site)
    if (next.date) p.set('date', next.date)
    setParams(p, { replace: true })
  }

  return {
    siteId,
    site: sites?.find((s) => s.site_id === siteId) ?? null,
    date,
    dates,
    forecasts,
    day: date && forecasts.data ? forecasts.data.days[date] : null,
    setSite: (site: string) => update({ site }),
    setDate: (date: string) => update({ date }),
  }
}
