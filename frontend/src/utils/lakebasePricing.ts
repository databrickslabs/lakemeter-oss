import type { LineItem } from '../types'

export const LAKEBASE_ALWAYS_ON_HOURS_PER_MONTH = 730
export const LAKEBASE_ALWAYS_ON_DISCOUNT_PCT = 25
export const LAKEBASE_AUTOSCALE_CU_OPTIONS = [
  0.5, 1, 2, 4, 8, 12, 16, 24, 28, 32, 40, 48, 56, 64,
] as const
export const LAKEBASE_MAX_AUTOSCALE_SPREAD_CU = 16

export function capMaxCu(minCu: number, maxCu?: number): number {
  let capped = minCu
  for (const cu of LAKEBASE_AUTOSCALE_CU_OPTIONS) {
    if (cu >= minCu && cu - minCu <= LAKEBASE_MAX_AUTOSCALE_SPREAD_CU) {
      capped = cu
    }
  }
  if (maxCu != null && maxCu >= minCu) {
    return Math.min(maxCu, capped)
  }
  return capped
}

export interface LakebaseAutoscaleConfig {
  computeMode: 'autoscale' | 'fixed'
  minCu: number
  maxCu: number
  scaleToZeroEnabled: boolean
  activeHoursPerMonth: number
  scaleUpHoursPerMonth: number
  alwaysOnDiscountPct: number
}

export interface LakebaseComputeUsage {
  baselineCu: number
  baselineHours: number
  baselineDiscountPct: number
  baselineEffectiveDbuPerCuHour: number
  scaleUpEffectiveDbuPerCuHour: number
  baselineDbu: number
  billableBaselineDbu: number
  scaleUpCu: number
  scaleUpHours: number
  scaleUpDbu: number
  totalRawDbu: number
  totalBillableDbu: number
  rawEquivalentDbuPerHour: number
  equivalentDbuPerHour: number
}

function asNumber(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function asBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return ['1', 'true', 'yes', 'y', 'on'].includes(value.toLowerCase())
  if (value == null) return fallback
  return Boolean(value)
}

function configValue(config: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (key in config) return config[key]
  }
  return undefined
}

export function resolveLakebaseAutoscaleConfig(item: Partial<LineItem>): LakebaseAutoscaleConfig {
  const config = item.workload_config || {}
  const legacyCu = asNumber(item.lakebase_cu, 1)
  const computeMode = (
    configValue(config, 'lakebase_compute_mode', 'compute_mode') ||
    item.lakebase_compute_mode ||
    (legacyCu > 64 ? 'fixed' : 'autoscale')
  ) === 'fixed' ? 'fixed' : 'autoscale'
  const minCu = Math.max(
    0,
    asNumber(configValue(config, 'lakebase_min_cu', 'min_cu'), asNumber(item.lakebase_min_cu, legacyCu)),
  )
  let maxCu = Math.max(
    minCu,
    asNumber(configValue(config, 'lakebase_max_cu', 'max_cu'), asNumber(item.lakebase_max_cu, minCu)),
  )
  let normalizedMinCu = minCu
  if (computeMode === 'fixed' || normalizedMinCu > 64 || maxCu > 64) {
    const fixedCu = maxCu > 64 ? maxCu : normalizedMinCu
    normalizedMinCu = fixedCu
    maxCu = fixedCu
  } else if (maxCu - normalizedMinCu > LAKEBASE_MAX_AUTOSCALE_SPREAD_CU) {
    maxCu = capMaxCu(normalizedMinCu)
  }
  const scaleToZeroEnabled = asBoolean(
    configValue(config, 'lakebase_scale_to_zero_enabled', 'scale_to_zero_enabled'),
    asBoolean(item.lakebase_scale_to_zero_enabled, false),
  )
  const activeHours = Math.max(
    0,
    asNumber(
      configValue(config, 'lakebase_active_hours_per_month', 'active_hours_per_month'),
      asNumber(item.lakebase_active_hours_per_month, asNumber(item.hours_per_month, LAKEBASE_ALWAYS_ON_HOURS_PER_MONTH)),
    ),
  )
  const scaleUpHours = Math.max(
    0,
    Math.min(
      asNumber(
        configValue(config, 'lakebase_scale_up_hours_per_month', 'scale_up_hours_per_month'),
        asNumber(item.lakebase_scale_up_hours_per_month, 0),
      ),
      activeHours,
    ),
  )
  const alwaysOnDiscountPct = Math.max(
    0,
    Math.min(
      asNumber(
        configValue(config, 'lakebase_always_on_discount_pct', 'always_on_discount_pct'),
        asNumber(item.lakebase_always_on_discount_pct, LAKEBASE_ALWAYS_ON_DISCOUNT_PCT),
      ),
      100,
    ),
  )

  return {
    computeMode,
    minCu: normalizedMinCu,
    maxCu,
    scaleToZeroEnabled,
    activeHoursPerMonth: activeHours,
    scaleUpHoursPerMonth: scaleUpHours,
    alwaysOnDiscountPct,
  }
}

export function calculateLakebaseComputeUsage(
  config: LakebaseAutoscaleConfig,
  dbuPerCuHour: number,
  nodes: number,
): LakebaseComputeUsage {
  const nodeCount = Math.max(1, nodes || 1)
  const scaleUpCu = config.maxCu
  const baselineHours = config.scaleToZeroEnabled
    ? Math.max(0, config.activeHoursPerMonth - config.scaleUpHoursPerMonth)
    : Math.max(0, LAKEBASE_ALWAYS_ON_HOURS_PER_MONTH - config.scaleUpHoursPerMonth)
  const baselineDiscountPct = config.scaleToZeroEnabled ? 0 : config.alwaysOnDiscountPct
  const baselineEffectiveDbuPerCuHour = dbuPerCuHour * (1 - baselineDiscountPct / 100)
  const scaleUpEffectiveDbuPerCuHour = dbuPerCuHour
  const baselineDbu = config.minCu * dbuPerCuHour * nodeCount * baselineHours
  const billableBaselineDbu = config.minCu * baselineEffectiveDbuPerCuHour * nodeCount * baselineHours
  const scaleUpDbu = scaleUpCu * dbuPerCuHour * nodeCount * config.scaleUpHoursPerMonth
  const totalRawDbu = baselineDbu + scaleUpDbu
  const totalBillableDbu = billableBaselineDbu + scaleUpDbu
  const denominatorHours = config.scaleToZeroEnabled
    ? config.activeHoursPerMonth
    : LAKEBASE_ALWAYS_ON_HOURS_PER_MONTH

  return {
    baselineCu: config.minCu,
    baselineHours,
    baselineDiscountPct,
    baselineEffectiveDbuPerCuHour,
    scaleUpEffectiveDbuPerCuHour,
    baselineDbu,
    billableBaselineDbu,
    scaleUpCu,
    scaleUpHours: config.scaleUpHoursPerMonth,
    scaleUpDbu,
    totalRawDbu,
    totalBillableDbu,
    rawEquivalentDbuPerHour: denominatorHours > 0 ? totalRawDbu / denominatorHours : 0,
    equivalentDbuPerHour: denominatorHours > 0 ? totalBillableDbu / denominatorHours : 0,
  }
}
