import type { FMAPIRate } from './pricingBundle'

export const TOKEN_RATE_UNIT = 'DBUs / 1M tokens'
export const HOURLY_RATE_UNIT = 'DBUs / hour'
export const EM_DASH = '-'

export type RateType =
  | 'input_token'
  | 'output_token'
  | 'cache_read'
  | 'cache_write'
  | 'batch_inference'

export interface FmapiKey {
  cloud: string
  family: string
  model: string
  geo: string
  contextLength: string
  rateType: RateType
}

export interface FmapiRow {
  cloud: string
  family: string
  model: string
  geo: string
  contextLength: string
  rates: Partial<Record<RateType, FMAPIRate | null>>
}

export interface ReshapeResult {
  rows: FmapiRow[]
  unrecognizedKeys: string[]
}

export function parseFmapiKey(key: string): FmapiKey | null {
  const parts = key.split(':')
  if (parts.length !== 6) return null
  const [cloud, family, model, geo, contextLength, rateType] = parts
  return { cloud, family, model, geo, contextLength, rateType: rateType as RateType }
}

export function reshapeFmapiProprietary(rates: Record<string, FMAPIRate | null>): ReshapeResult {
  const rowMap = new Map<string, FmapiRow>()
  const unrecognizedKeys: string[] = []

  for (const [key, value] of Object.entries(rates ?? {})) {
    const parsed = parseFmapiKey(key)
    if (!parsed) {
      unrecognizedKeys.push(key)
      continue
    }

    const rowKey = `${parsed.cloud}:${parsed.family}:${parsed.model}:${parsed.geo}:${parsed.contextLength}`
    if (!rowMap.has(rowKey)) {
      rowMap.set(rowKey, {
        cloud: parsed.cloud,
        family: parsed.family,
        model: parsed.model,
        geo: parsed.geo,
        contextLength: parsed.contextLength,
        rates: {},
      })
    }
    rowMap.get(rowKey)!.rates[parsed.rateType] = value
  }

  return { rows: Array.from(rowMap.values()), unrecognizedKeys }
}

export function formatTokenRate(rate: FMAPIRate | null | undefined): string {
  if (rate == null) return EM_DASH
  return rate.dbu_rate.toLocaleString('en-US', { maximumFractionDigits: 3 })
}

export function formatHourlyRate(rate: FMAPIRate | null | undefined): string {
  if (rate == null) return EM_DASH
  return rate.dbu_rate.toLocaleString('en-US', { maximumFractionDigits: 3 })
}

export function formatDollarCell(costLocal: number, currencySymbol: string): string {
  if (!Number.isFinite(costLocal)) return EM_DASH
  if (Math.abs(costLocal) < 0.01 && costLocal !== 0) {
    return `${currencySymbol}${costLocal.toExponential(2)}`
  }
  return `${currencySymbol}${costLocal.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`
}
