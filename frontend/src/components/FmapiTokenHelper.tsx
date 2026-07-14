import { Fragment, useMemo, useState } from 'react'
import { useStore } from '../store/useStore'
import {
  EM_DASH,
  HOURLY_RATE_UNIT,
  TOKEN_RATE_UNIT,
  formatDollarCell,
  formatHourlyRate,
  formatTokenRate,
  reshapeFmapiProprietary,
  type FmapiRow,
  type RateType,
} from '../utils/fmapiProprietary'
import type { FMAPIRate } from '../utils/pricingBundle'

const ALL = 'all'
const TOKEN_RATE_TYPES: RateType[] = ['input_token', 'output_token', 'cache_write', 'cache_read']

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  AUD: 'A$',
  EUR: 'EUR ',
  GBP: 'GBP ',
  CAD: 'C$',
  SGD: 'S$',
}

interface GroupedRow {
  cloud: string
  family: string
  model: string
  contextLength: string
  byGeo: Record<string, Partial<Record<RateType, FMAPIRate | null>>>
}

type DisplayMode = 'dbu' | 'dollars'

function renderCloud(value: string): string {
  if (value === 'aws') return 'AWS'
  if (value === 'azure') return 'Azure'
  if (value === 'gcp') return 'GCP'
  return value
}

function renderFamily(value: string): string {
  if (value === 'anthropic') return 'Anthropic'
  if (value === 'google') return 'Google'
  if (value === 'openai') return 'OpenAI'
  return value
}

function renderGeo(value: string): string {
  if (value === 'global') return 'Global'
  if (value === 'in_geo') return 'In-geo'
  return value
}

function renderContext(value: string): string {
  if (value === 'all') return 'All'
  if (value === 'long') return 'Long'
  if (value === 'short') return 'Short'
  return value
}

function currencySymbolFor(code: string): string {
  return CURRENCY_SYMBOLS[code] ?? `${code} `
}

function rateTypeLabel(rateType: RateType): string {
  switch (rateType) {
    case 'input_token':
      return 'Input'
    case 'output_token':
      return 'Output'
    case 'cache_write':
      return 'Cache write'
    case 'cache_read':
      return 'Cache read'
    case 'batch_inference':
      return 'Batch'
  }
}

function uniqueOptions(rows: FmapiRow[], field: keyof Pick<FmapiRow, 'cloud' | 'family' | 'geo' | 'contextLength'>) {
  return Array.from(new Set(rows.map((row) => String(row[field])))).sort()
}

function groupRowsForDollars(rows: FmapiRow[]): GroupedRow[] {
  const map = new Map<string, GroupedRow>()
  for (const row of rows) {
    const key = `${row.cloud}:${row.family}:${row.model}:${row.contextLength}`
    let group = map.get(key)
    if (!group) {
      group = {
        cloud: row.cloud,
        family: row.family,
        model: row.model,
        contextLength: row.contextLength,
        byGeo: {},
      }
      map.set(key, group)
    }
    group.byGeo[row.geo] = row.rates
  }
  return Array.from(map.values())
}

function SelectFilter({
  label,
  value,
  options,
  render,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  render: (value: string) => string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-[var(--text-muted)]">{label}</label>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="text-sm">
        <option value={ALL}>All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {render(option)}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function FmapiTokenHelper({ fxRate = 1 }: { fxRate?: number }) {
  const pricingBundle = useStore((state) => state.pricingBundle)
  const isPricingBundleLoaded = useStore((state) => state.isPricingBundleLoaded)
  const loadPricingBundle = useStore((state) => state.loadPricingBundle)
  const [displayMode, setDisplayMode] = useState<DisplayMode>('dbu')
  const [cloud, setCloud] = useState(ALL)
  const [family, setFamily] = useState(ALL)
  const [modelQuery, setModelQuery] = useState('')
  const [geo, setGeo] = useState(ALL)
  const [context, setContext] = useState(ALL)
  const [dollarCloud, setDollarCloud] = useState('aws')
  const [dollarRegion, setDollarRegion] = useState('us-east-1')
  const [dollarTier, setDollarTier] = useState('ENTERPRISE')
  const [discountPct, setDiscountPct] = useState(0)
  const currency = 'USD'
  const currencySymbol = currencySymbolFor(currency)

  const { rows, unrecognizedKeys } = useMemo(
    () => reshapeFmapiProprietary(pricingBundle.fmapiProprietaryRates ?? {}),
    [pricingBundle.fmapiProprietaryRates],
  )

  const visibleRows = useMemo(() => {
    return rows.filter((row) => {
      if (displayMode === 'dollars') {
        if (row.cloud !== dollarCloud) return false
      } else if (cloud !== ALL && row.cloud !== cloud) {
        return false
      }
      if (family !== ALL && row.family !== family) return false
      if (geo !== ALL && row.geo !== geo) return false
      if (context !== ALL && row.contextLength !== context) return false
      const query = modelQuery.trim().toLowerCase()
      if (query && !row.model.toLowerCase().includes(query)) return false
      return true
    })
  }, [rows, displayMode, dollarCloud, cloud, family, geo, context, modelQuery])

  const groupedDollarRows = useMemo(
    () => (displayMode === 'dollars' ? groupRowsForDollars(visibleRows) : []),
    [displayMode, visibleRows],
  )

  const dbuRateKey = `${dollarCloud}:${dollarRegion}:${dollarTier.toUpperCase()}`
  const renderDollarCell = (rate: FMAPIRate | null | undefined) => {
    if (!rate) return EM_DASH
    const dollarPerDbu = pricingBundle.dbuRates?.[dbuRateKey]?.[rate.sku_product_type]
    if (dollarPerDbu == null) return EM_DASH
    const usd = rate.dbu_rate * dollarPerDbu * (1 - discountPct / 100)
    return formatDollarCell(usd * fxRate, currencySymbol)
  }

  const regionOptions = useMemo(() => {
    const prefix = `${dollarCloud}:`
    const regions = new Set<string>()
    for (const key of Object.keys(pricingBundle.dbuRates ?? {})) {
      if (key.startsWith(prefix)) {
        const [, region] = key.split(':')
        if (region) regions.add(region)
      }
    }
    return Array.from(regions).sort()
  }, [pricingBundle.dbuRates, dollarCloud])

  const tierOptions = useMemo(() => {
    const prefix = `${dollarCloud}:${dollarRegion}:`
    const tiers = new Set<string>()
    for (const key of Object.keys(pricingBundle.dbuRates ?? {})) {
      if (key.startsWith(prefix)) {
        const [, , tier] = key.split(':')
        if (tier) tiers.add(tier)
      }
    }
    return Array.from(tiers).sort()
  }, [pricingBundle.dbuRates, dollarCloud, dollarRegion])

  return (
    <div>
      <div className="mb-4 space-y-1">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">FMAPI token pricing</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Per-region DBU rates for proprietary Foundation Model Serving. Token rates are quoted in{' '}
          <strong>DBUs per 1 million tokens</strong>; batch inference is quoted in{' '}
          <strong>DBUs per hour</strong>. Cells showing {EM_DASH} indicate the rate is not published
          for that combination.
        </p>
      </div>

      {!isPricingBundleLoaded && (
        <button type="button" className="btn btn-secondary mb-4" onClick={() => loadPricingBundle()}>
          Reload pricing bundle
        </button>
      )}

      <div className="mb-4 flex items-center gap-3">
        <span className="text-xs font-medium text-[var(--text-muted)]">Display</span>
        <button
          type="button"
          role="switch"
          aria-checked={displayMode === 'dollars'}
          onClick={() => setDisplayMode(displayMode === 'dbu' ? 'dollars' : 'dbu')}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--border-primary)] bg-[var(--bg-secondary)] px-2 py-1 text-sm"
        >
          <span className={displayMode === 'dbu' ? 'rounded-full bg-[var(--bg-tertiary)] px-2 py-0.5 font-semibold' : 'px-2 py-0.5 text-[var(--text-muted)]'}>
            DBU
          </span>
          <span className={displayMode === 'dollars' ? 'rounded-full bg-[var(--bg-tertiary)] px-2 py-0.5 font-semibold' : 'px-2 py-0.5 text-[var(--text-muted)]'}>
            $
          </span>
        </button>
      </div>

      {unrecognizedKeys.length > 0 && (
        <div className="mb-4 rounded border border-amber-400 bg-amber-50 p-3 text-sm text-amber-900">
          {unrecognizedKeys.length} rate entries could not be parsed.
        </div>
      )}

      {displayMode === 'dollars' && (
        <div className="mb-4 flex flex-wrap items-end gap-4 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-3">
          <SelectFilter label="Cloud" value={dollarCloud} onChange={setDollarCloud} options={['aws', 'azure', 'gcp']} render={renderCloud} />
          <SelectFilter label="Region" value={dollarRegion} onChange={setDollarRegion} options={regionOptions} render={(value) => value} />
          <SelectFilter label="Tier" value={dollarTier} onChange={setDollarTier} options={tierOptions} render={(value) => value} />
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-muted)]">Discount %</label>
            <input
              type="number"
              min={0}
              max={100}
              value={discountPct}
              onChange={(event) => setDiscountPct(Number(event.target.value))}
              className="w-24 text-sm"
            />
          </div>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-4">
        {displayMode === 'dbu' && (
          <SelectFilter label="Cloud" value={cloud} onChange={setCloud} options={uniqueOptions(rows, 'cloud')} render={renderCloud} />
        )}
        <SelectFilter label="Family" value={family} onChange={setFamily} options={uniqueOptions(rows, 'family')} render={renderFamily} />
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-[var(--text-muted)]">Model contains</label>
          <input
            type="search"
            value={modelQuery}
            onChange={(event) => setModelQuery(event.target.value)}
            placeholder="e.g. opus or 4-6"
            className="w-40 text-sm"
          />
        </div>
        {displayMode === 'dbu' && (
          <SelectFilter label="Geo" value={geo} onChange={setGeo} options={uniqueOptions(rows, 'geo')} render={renderGeo} />
        )}
        <SelectFilter label="Context length" value={context} onChange={setContext} options={uniqueOptions(rows, 'contextLength')} render={renderContext} />
      </div>

      <div className="overflow-x-auto rounded-lg border border-[var(--border-primary)]">
        {displayMode === 'dbu' ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)]">
                <th colSpan={5} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Model context</th>
                <th colSpan={4} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)] border-l-2 border-[var(--border-secondary)]">Token rates ({TOKEN_RATE_UNIT})</th>
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)] border-l-2 border-[var(--border-secondary)]">Batch ({HOURLY_RATE_UNIT})</th>
              </tr>
              <tr className="bg-[var(--bg-tertiary)]">
                {['Cloud', 'Family', 'Model', 'Geo', 'Context'].map((header) => <th key={header} className="px-3 py-2 text-left text-xs font-medium">{header}</th>)}
                {['Input', 'Output', 'Cache writes', 'Cache reads'].map((header, index) => (
                  <th key={header} className={`px-3 py-2 text-right text-xs font-medium ${index === 0 ? 'border-l-2 border-[var(--border-secondary)]' : ''}`}>{header}</th>
                ))}
                <th className="px-3 py-2 text-right text-xs font-medium border-l-2 border-[var(--border-secondary)]">Batch inference</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={`${row.cloud}:${row.family}:${row.model}:${row.geo}:${row.contextLength}`} className="border-t border-[var(--border-primary)]">
                  <td className="px-3 py-2">{renderCloud(row.cloud)}</td>
                  <td className="px-3 py-2">{renderFamily(row.family)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.model}</td>
                  <td className="px-3 py-2">{renderGeo(row.geo)}</td>
                  <td className="px-3 py-2">{renderContext(row.contextLength)}</td>
                  <td className="px-3 py-2 text-right tabular-nums border-l-2 border-[var(--border-secondary)]">{formatTokenRate(row.rates.input_token)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTokenRate(row.rates.output_token)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTokenRate(row.rates.cache_write)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTokenRate(row.rates.cache_read)}</td>
                  <td className="px-3 py-2 text-right tabular-nums border-l-2 border-[var(--border-secondary)]">{formatHourlyRate(row.rates.batch_inference)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)]">
                <th colSpan={4} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Model context</th>
                <th colSpan={8} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)] border-l-2 border-[var(--border-secondary)]">Token rates ({currency} / 1M tokens)</th>
                <th colSpan={2} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)] border-l-2 border-[var(--border-secondary)]">Batch ({currency} / hour)</th>
              </tr>
              <tr className="bg-[var(--bg-tertiary)]">
                {['Cloud', 'Family', 'Model', 'Context'].map((header) => <th key={header} className="px-3 py-2 text-left text-xs font-medium">{header}</th>)}
                {TOKEN_RATE_TYPES.map((rateType, index) => (
                  <Fragment key={rateType}>
                    <th className={`px-3 py-2 text-right text-xs font-medium ${index === 0 ? 'border-l-2 border-[var(--border-secondary)]' : ''}`}>{rateTypeLabel(rateType)} Global</th>
                    <th className="px-3 py-2 text-right text-xs font-medium">{rateTypeLabel(rateType)} In-geo</th>
                  </Fragment>
                ))}
                <th className="px-3 py-2 text-right text-xs font-medium border-l-2 border-[var(--border-secondary)]">Batch Global</th>
                <th className="px-3 py-2 text-right text-xs font-medium">Batch In-geo</th>
              </tr>
            </thead>
            <tbody>
              {groupedDollarRows.map((row) => (
                <tr key={`${row.cloud}:${row.family}:${row.model}:${row.contextLength}`} className="border-t border-[var(--border-primary)]">
                  <td className="px-3 py-2">{renderCloud(row.cloud)}</td>
                  <td className="px-3 py-2">{renderFamily(row.family)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.model}</td>
                  <td className="px-3 py-2">{renderContext(row.contextLength)}</td>
                  {TOKEN_RATE_TYPES.map((rateType, index) => (
                    <Fragment key={rateType}>
                      <td className={`px-3 py-2 text-right tabular-nums ${index === 0 ? 'border-l-2 border-[var(--border-secondary)]' : ''}`}>{renderDollarCell(row.byGeo.global?.[rateType])}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{renderDollarCell(row.byGeo.in_geo?.[rateType])}</td>
                    </Fragment>
                  ))}
                  <td className="px-3 py-2 text-right tabular-nums border-l-2 border-[var(--border-secondary)]">{renderDollarCell(row.byGeo.global?.batch_inference)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{renderDollarCell(row.byGeo.in_geo?.batch_inference)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
