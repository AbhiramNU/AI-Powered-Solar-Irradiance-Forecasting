import { formatDate, type Site } from '../lib/data'

export function SiteDateFields({
  sites,
  siteId,
  date,
  dates,
  setSite,
  setDate,
}: {
  sites: Site[]
  siteId: string | null
  date: string | null
  dates: string[]
  setSite: (s: string) => void
  setDate: (d: string) => void
}) {
  return (
    <>
      <div className="field">
        <label htmlFor="site">Location</label>
        <select id="site" value={siteId ?? ''} onChange={(e) => setSite(e.target.value)}>
          {sites.map((s) => (
            <option key={s.site_id} value={s.site_id}>
              {s.name} — {s.climate_zone}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="date">Date</label>
        <select id="date" value={date ?? ''} onChange={(e) => setDate(e.target.value)} disabled={!dates.length}>
          {dates.map((d) => (
            <option key={d} value={d}>
              {formatDate(d)}
            </option>
          ))}
        </select>
      </div>
    </>
  )
}
