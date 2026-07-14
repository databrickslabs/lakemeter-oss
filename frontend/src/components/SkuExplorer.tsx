import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronDownIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline'
import { useStore } from '../store/useStore'
import SearchableSelect from './SearchableSelect'
import type { DBUMultiplier } from '../utils/pricingBundle'
import { getAvailableRegionsFromBundle } from '../utils/pricingBundle'
import {
  EXCLUDED_PRODUCT_TYPES,
  GROUP_ORDER,
  SKU_GROUPS,
  formatFeatureName,
  formatProductName,
  formatRate,
  getSkuGroup,
} from '../utils/skuGroups'

const CLOUDS = ['AWS', 'AZURE', 'GCP']
const LAKEBASE_DBU_PER_CU_HOUR = 0.213
const LAKEBASE_CU_TO_DAILY_DBU = 24 * LAKEBASE_DBU_PER_CU_HOUR

interface PricingRow {
  key: string
  productType: string
  displayName: string
  variant: string
  price: number
  discount: number
  netRate: number
  quantity: number
  dailyCost: number
  monthlyCost: number
  group: string
  isExcluded: boolean
  billingUnit: 'dbu' | 'cu'
}

interface MultiplierRow {
  feature: string
  displayFeature: string
  multiplier: number
  effectiveRate: number
  netRate: number
  quantity: number
  dailyCost: number
  monthlyCost: number
}

function formatCost(value: number): string {
  if (value === 0) return '$0'
  if (Math.abs(value) < 1) return `$${value.toFixed(3)}`
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatDBUs(value: number): string {
  if (value === 0) return '0'
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

function isAccountingVariant(productType: string): boolean {
  return productType.includes('_(PHOTON)') || productType.includes('_(DLT)')
}

function inferVariant(productType: string): string {
  if (productType.includes('SERVERLESS') || productType.includes('INTERACTIVE_SERVERLESS')) return 'Serverless'
  if (productType.includes('STORAGE')) return 'Storage'
  if (productType.includes('EGRESS') || productType.includes('NETWORK')) return 'Networking'
  return 'Classic'
}

function isLakebaseCompute(productType: string): boolean {
  return productType === 'DATABASE_SERVERLESS_COMPUTE' || productType === 'LAKEBASE_COMPUTE'
}

function getProductTypes(
  dbuRates: Record<string, Record<string, number>>,
  cloud: string,
  region: string,
  tier: string,
): Record<string, number> {
  const key = `${cloud.toLowerCase()}:${region}:${tier.toUpperCase()}`
  const raw = dbuRates[key] || {}
  const filtered: Record<string, number> = {}
  for (const [productType, rate] of Object.entries(raw)) {
    if (!isAccountingVariant(productType)) filtered[productType] = rate
  }
  return filtered
}

function getMultipliersForProduct(
  multipliers: Record<string, DBUMultiplier>,
  cloud: string,
  productType: string,
): Array<{ feature: string; data: DBUMultiplier }> {
  const prefix = `${cloud.toLowerCase()}:${productType}:`
  const results: Array<{ feature: string; data: DBUMultiplier }> = []
  for (const [key, value] of Object.entries(multipliers)) {
    if (key.startsWith(prefix)) {
      results.push({ feature: key.slice(prefix.length), data: value })
    }
  }
  return results.sort((a, b) => b.data.multiplier - a.data.multiplier)
}

export default function SkuExplorer({ fxRate = 1 }: { fxRate?: number }) {
  const regionsMap = useStore((state) => state.regionsMap)
  const isReferenceDataLoaded = useStore((state) => state.isReferenceDataLoaded)
  const fetchReferenceData = useStore((state) => state.fetchReferenceData)
  const pricingBundle = useStore((state) => state.pricingBundle)
  const isPricingBundleLoaded = useStore((state) => state.isPricingBundleLoaded)
  const loadPricingBundle = useStore((state) => state.loadPricingBundle)

  const [viewMode, setViewMode] = useState<'simple' | 'advanced'>('simple')
  const [cloud, setCloud] = useState('AWS')
  const [region, setRegion] = useState('')
  const [tier, setTier] = useState('ENTERPRISE')
  const [defaultDiscount, setDefaultDiscount] = useState(0)
  const [discounts, setDiscounts] = useState<Record<string, number>>({})
  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [multiplierQuantities, setMultiplierQuantities] = useState<Record<string, number>>({})
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!isReferenceDataLoaded) fetchReferenceData()
  }, [fetchReferenceData, isReferenceDataLoaded])

  useEffect(() => {
    if (!isPricingBundleLoaded) loadPricingBundle()
  }, [isPricingBundleLoaded, loadPricingBundle])

  useEffect(() => {
    const cloudRegions = regionsMap[cloud.toLowerCase()] || []
    if (cloudRegions.length > 0) {
      const preferred = cloudRegions.find((item) => item.region_code === 'us-east-1' || item.region_code === 'us-west-2')
      setRegion(preferred?.region_code || cloudRegions[0].region_code)
      return
    }

    if (isPricingBundleLoaded) {
      const bundleRegions = getAvailableRegionsFromBundle(pricingBundle, cloud)
      const preferred = bundleRegions.find((item) => item === 'us-east-1' || item === 'us-west-2')
      if (bundleRegions.length > 0) setRegion(preferred || bundleRegions[0])
    }
  }, [cloud, regionsMap, isPricingBundleLoaded, pricingBundle])

  const tierOptions = useMemo(() => {
    const prefix = `${cloud.toLowerCase()}:${region}:`
    const tiers = new Set<string>()
    for (const key of Object.keys(pricingBundle.dbuRates || {})) {
      if (key.startsWith(prefix)) {
        const [, , tierName] = key.split(':')
        if (tierName) tiers.add(tierName)
      }
    }
    const result = Array.from(tiers).sort()
    return result.length > 0 ? result : ['PREMIUM', 'ENTERPRISE']
  }, [pricingBundle.dbuRates, cloud, region])

  useEffect(() => {
    if (tierOptions.length > 0 && !tierOptions.includes(tier)) {
      setTier(tierOptions[0])
    }
  }, [tierOptions, tier])

  const regionOptions = useMemo(() => {
    const cloudRegions = regionsMap[cloud.toLowerCase()] || []
    if (cloudRegions.length > 0) {
      return cloudRegions.map((item) => ({
        value: item.region_code,
        label: `${item.region_code}${item.sku_region && item.sku_region !== item.region_code ? ` (${item.sku_region})` : ''}`,
      }))
    }
    return getAvailableRegionsFromBundle(pricingBundle, cloud).map((item) => ({ value: item, label: item }))
  }, [cloud, regionsMap, pricingBundle])

  const productTypes = useMemo(
    () => getProductTypes(pricingBundle.dbuRates, cloud, region, tier),
    [pricingBundle.dbuRates, cloud, region, tier],
  )

  const simpleRows = useMemo<PricingRow[]>(() => {
    return Object.entries(productTypes)
      .map(([productType, rate]) => {
        const isExcluded = EXCLUDED_PRODUCT_TYPES.has(productType)
        const discount = isExcluded ? 0 : discounts[productType] ?? defaultDiscount
        const price = rate * fxRate
        const netRate = price * (1 - discount / 100)
        const quantity = quantities[productType] ?? 0
        const lakebase = isLakebaseCompute(productType)
        const billingUnit: PricingRow['billingUnit'] = lakebase ? 'cu' : 'dbu'
        const effectiveDaily = lakebase ? quantity * LAKEBASE_CU_TO_DAILY_DBU : quantity
        const dailyCost = netRate * effectiveDaily
        return {
          key: productType,
          productType,
          displayName: formatProductName(productType),
          variant: inferVariant(productType),
          price,
          discount,
          netRate,
          quantity,
          dailyCost,
          monthlyCost: dailyCost * 30,
          group: getSkuGroup(productType),
          isExcluded,
          billingUnit,
        }
      })
      .sort((a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) || a.displayName.localeCompare(b.displayName))
  }, [productTypes, discounts, defaultDiscount, quantities, fxRate])

  const rowsByGroup = useMemo(() => {
    const map = new Map<string, PricingRow[]>()
    for (const row of simpleRows) {
      if (!map.has(row.group)) map.set(row.group, [])
      map.get(row.group)!.push(row)
    }
    return map
  }, [simpleRows])

  const multipliersByProduct = useMemo(() => {
    if (viewMode !== 'advanced') return new Map<string, MultiplierRow[]>()
    const map = new Map<string, MultiplierRow[]>()
    for (const row of simpleRows) {
      const multiplierRows = getMultipliersForProduct(pricingBundle.dbuMultipliers, cloud, row.productType).map(({ feature, data }) => {
        const effectiveRate = row.price * data.multiplier
        const netRate = effectiveRate * (1 - row.discount / 100)
        const key = `${row.productType}:${feature}`
        const quantity = multiplierQuantities[key] ?? 0
        const dailyCost = netRate * quantity
        return {
          feature,
          displayFeature: formatFeatureName(feature),
          multiplier: data.multiplier,
          effectiveRate,
          netRate,
          quantity,
          dailyCost,
          monthlyCost: dailyCost * 30,
        }
      })
      if (multiplierRows.length > 0) map.set(row.productType, multiplierRows)
    }
    return map
  }, [viewMode, simpleRows, pricingBundle.dbuMultipliers, cloud, multiplierQuantities])

  const summary = useMemo(() => {
    let dailyVolume = simpleRows.filter((row) => row.billingUnit === 'dbu').reduce((sum, row) => sum + row.quantity, 0)
    let dailyCost = simpleRows.reduce((sum, row) => sum + row.dailyCost, 0)
    let monthlyCost = simpleRows.reduce((sum, row) => sum + row.monthlyCost, 0)
    if (viewMode === 'advanced') {
      for (const multiplierRows of multipliersByProduct.values()) {
        for (const row of multiplierRows) {
          dailyVolume += row.quantity
          dailyCost += row.dailyCost
          monthlyCost += row.monthlyCost
        }
      }
    }
    return { dailyVolume, dailyCost, monthlyCost, annualCost: monthlyCost * 12 }
  }, [simpleRows, viewMode, multipliersByProduct])

  const handleCopyPrices = useCallback(async () => {
    const lines = [
      `Databricks SKU pricing - ${cloud} ${region} ${tier}${fxRate !== 1 ? ` (FX ${fxRate})` : ''}`,
      ['Group', 'Product', 'Variant', 'List rate', 'Discount %', 'Net rate', 'Unit'].join('\t'),
    ]
    for (const groupName of GROUP_ORDER) {
      for (const row of rowsByGroup.get(groupName) ?? []) {
        lines.push([
          groupName,
          row.displayName,
          row.variant,
          formatRate(row.price),
          row.isExcluded ? 'N/A' : String(row.discount),
          formatRate(row.netRate),
          row.billingUnit === 'cu' ? '/CU' : '/DBU',
        ].join('\t'))
      }
    }
    await navigator.clipboard.writeText(lines.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [cloud, region, tier, fxRate, rowsByGroup])

  const toggleExpanded = (key: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const hasData = simpleRows.length > 0

  return (
    <div className="max-w-7xl xl:max-w-[1400px] 2xl:max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">SKU Pricing Explorer</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Explore Databricks DBU pricing by cloud, region, and tier</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative inline-flex rounded-lg p-0.5 bg-[var(--bg-tertiary)]">
            <button
              type="button"
              onClick={() => setViewMode('simple')}
              className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors ${viewMode === 'simple' ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)]'}`}
            >
              Simple
            </button>
            <button
              type="button"
              onClick={() => setViewMode('advanced')}
              className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors ${viewMode === 'advanced' ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)]'}`}
            >
              Advanced
            </button>
          </div>
          <button type="button" onClick={handleCopyPrices} disabled={!hasData} className="btn btn-secondary">
            {copied ? <CheckIcon className="w-4 h-4" /> : <ClipboardDocumentIcon className="w-4 h-4" />}
            {copied ? 'Copied' : 'Copy Prices'}
          </button>
        </div>
      </div>

      <div className="rounded-xl border p-4 mb-6 bg-[var(--bg-secondary)] border-[var(--border-primary)]">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-36">
            <label className="block text-[10px] font-semibold uppercase tracking-wider mb-1 text-[var(--text-muted)]">Cloud</label>
            <select value={cloud} onChange={(event) => setCloud(event.target.value)} className="w-full">
              {CLOUDS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[240px]">
            <label className="block text-[10px] font-semibold uppercase tracking-wider mb-1 text-[var(--text-muted)]">Region</label>
            <SearchableSelect
              options={regionOptions}
              value={region}
              onChange={setRegion}
              placeholder="Select region..."
              searchPlaceholder="Search regions..."
              isLoading={!isReferenceDataLoaded && !isPricingBundleLoaded}
            />
          </div>
          <div className="w-40">
            <label className="block text-[10px] font-semibold uppercase tracking-wider mb-1 text-[var(--text-muted)]">Tier</label>
            <select value={tier} onChange={(event) => setTier(event.target.value)} className="w-full">
              {tierOptions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div className="w-28">
            <label className="block text-[10px] font-semibold uppercase tracking-wider mb-1 text-[var(--text-muted)]">Discount %</label>
            <input
              type="number"
              min={0}
              max={100}
              value={defaultDiscount}
              onChange={(event) => setDefaultDiscount(Number(event.target.value))}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {!hasData ? (
        <div className="text-center py-16 text-sm text-[var(--text-muted)]">No pricing data for this configuration.</div>
      ) : (
        <div className="space-y-4">
          {GROUP_ORDER.map((groupName) => {
            const rows = rowsByGroup.get(groupName)
            const style = SKU_GROUPS[groupName]
            if (!rows || rows.length === 0 || !style) return null
            return (
              <div key={groupName} className="rounded-lg overflow-hidden border border-[var(--border-primary)]">
                <div className={`flex items-center gap-2 px-4 py-2.5 border-l-4 ${style.borderColor} ${style.bgColor}`}>
                  <span className={`text-sm font-bold uppercase tracking-wider ${style.color}`}>{style.label}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium text-[var(--text-muted)] bg-[var(--bg-tertiary)]">{rows.length}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[var(--bg-secondary)]">
                        {viewMode === 'advanced' && <th className="w-7" />}
                        <th className="text-left py-2 px-4 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Product</th>
                        <th className="text-right py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">List rate</th>
                        <th className="text-right py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Discount</th>
                        <th className={`text-right py-2 px-3 text-[10px] font-semibold uppercase tracking-wider ${style.color}`}>Net rate</th>
                        <th className="text-right py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Volume</th>
                        <th className="text-right py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Daily cost</th>
                        <th className={`text-right py-2 px-4 text-[10px] font-semibold uppercase tracking-wider ${style.color}`}>Monthly cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, index) => {
                        const multiplierRows = multipliersByProduct.get(row.productType) ?? []
                        const canExpand = viewMode === 'advanced' && multiplierRows.length > 0
                        const isExpanded = expandedRows.has(row.key)
                        return (
                          <Fragment key={row.key}>
                            <tr
                              className={`border-t border-[var(--border-primary)] ${canExpand ? 'cursor-pointer hover:bg-[var(--bg-hover)]' : ''} ${index % 2 ? 'bg-black/[0.015] dark:bg-white/[0.015]' : ''}`}
                              onClick={canExpand ? () => toggleExpanded(row.key) : undefined}
                            >
                              {viewMode === 'advanced' && (
                                <td className="py-2.5 pl-3 pr-0">
                                  {canExpand && <ChevronDownIcon className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform ${isExpanded ? '' : '-rotate-90'}`} />}
                                </td>
                              )}
                              <td className="py-2.5 px-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-[var(--text-primary)]">{row.displayName}</span>
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-muted)]">{row.variant}</span>
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums text-xs text-[var(--text-secondary)]">{formatRate(row.price)}</td>
                              <td className="py-2.5 px-3 text-right">
                                {row.isExcluded ? (
                                  <span className="text-[10px] text-[var(--text-muted)]">N/A</span>
                                ) : (
                                  <input
                                    type="number"
                                    min={0}
                                    max={100}
                                    value={row.discount}
                                    onClick={(event) => event.stopPropagation()}
                                    onChange={(event) => setDiscounts((prev) => ({ ...prev, [row.key]: Number(event.target.value) }))}
                                    className="w-20 text-right text-sm"
                                  />
                                )}
                              </td>
                              <td className={`py-2.5 px-3 text-right tabular-nums font-bold ${style.color}`}>{formatRate(row.netRate)}</td>
                              <td className="py-2.5 px-3 text-right">
                                <div className="inline-flex items-center gap-1">
                                  <input
                                    type="number"
                                    min={0}
                                    value={row.quantity}
                                    onClick={(event) => event.stopPropagation()}
                                    onChange={(event) => setQuantities((prev) => ({ ...prev, [row.key]: Number(event.target.value) }))}
                                    className="w-24 text-right text-sm"
                                  />
                                  <span className="text-[10px] text-[var(--text-muted)] w-10 text-left">{row.billingUnit === 'cu' ? 'CU' : 'DBU/d'}</span>
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums text-sm text-[var(--text-secondary)]">{formatCost(row.dailyCost)}</td>
                              <td className={`py-2.5 px-4 text-right tabular-nums font-bold ${row.monthlyCost > 0 ? style.color : 'text-[var(--text-muted)]'}`}>{formatCost(row.monthlyCost)}</td>
                            </tr>
                            {canExpand && isExpanded && multiplierRows.map((multiplierRow) => (
                              <tr key={`${row.key}:${multiplierRow.feature}`} className="border-t border-[var(--border-primary)] bg-[var(--bg-secondary)]">
                                <td className="py-2 pl-3 pr-0" />
                                <td className="py-2 px-4 pl-7 text-xs font-medium text-[var(--text-secondary)]">{multiplierRow.displayFeature}</td>
                                <td className="py-2 px-3 text-right tabular-nums text-xs">{formatRate(multiplierRow.effectiveRate)}</td>
                                <td className="py-2 px-3 text-right text-xs text-[var(--text-muted)]">-</td>
                                <td className="py-2 px-3 text-right tabular-nums text-xs font-semibold">{formatRate(multiplierRow.netRate)}</td>
                                <td className="py-2 px-3 text-right">
                                  <input
                                    type="number"
                                    min={0}
                                    value={multiplierRow.quantity}
                                    onChange={(event) => setMultiplierQuantities((prev) => ({ ...prev, [`${row.productType}:${multiplierRow.feature}`]: Number(event.target.value) }))}
                                    className="w-24 text-right text-xs"
                                  />
                                </td>
                                <td className="py-2 px-3 text-right tabular-nums text-xs">{formatCost(multiplierRow.dailyCost)}</td>
                                <td className="py-2 px-4 text-right tabular-nums text-xs font-semibold">{formatCost(multiplierRow.monthlyCost)}</td>
                              </tr>
                            ))}
                          </Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {summary.dailyVolume > 0 && (
        <div className="sticky bottom-4 mt-6 rounded-xl overflow-hidden shadow-lg bg-[var(--bg-secondary)]">
          <div className="h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-red-500" />
          <div className="p-4 flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Daily DBUs</div>
              <div className="text-xl font-bold text-[var(--text-primary)] tabular-nums">{formatDBUs(summary.dailyVolume)}</div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Daily</div>
                <div className="text-lg font-bold text-[var(--text-secondary)] tabular-nums">{formatCost(summary.dailyCost)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Monthly</div>
                <div className="text-xl font-bold text-[var(--text-primary)] tabular-nums">{formatCost(summary.monthlyCost)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Annual</div>
                <div className="text-2xl font-extrabold text-lava-600 tabular-nums">{formatCost(summary.annualCost)}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
