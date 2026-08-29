import type {
  PlatformAddonCatalog,
  PlatformAddonDefinition,
} from './pricingBundle'
import type { PlatformAddonType } from '../types'

export type { PlatformAddonType } from '../types'

export const PLATFORM_ADDON_TYPES: PlatformAddonType[] = [
  'ENHANCED_SECURITY_COMPLIANCE',
  'MISSION_CRITICAL',
]

export interface PlatformAddonRate {
  addonType: PlatformAddonType
  displayName: string
  sku: string
  standardRatePct: number
  appliedRatePct: number
  promotionLabel?: string
  promotionEndDate?: string
  sourceUrl: string
}

export interface PlatformAddonCost extends PlatformAddonRate {
  productSpendAtList: number
  standardCost: number
  costBeforeDiscount: number
  discountPct: number
  discountAmount: number
  cost: number
}

const normalize = (value: string): string => value.toUpperCase()

export function getPlatformAddonDefinition(
  catalog: PlatformAddonCatalog,
  addonType: PlatformAddonType,
): PlatformAddonDefinition | null {
  return catalog.addons[addonType] ?? null
}

export function getPlatformAddonAvailabilityError(
  catalog: PlatformAddonCatalog,
  addonType: PlatformAddonType,
  cloud: string,
  tier: string,
): string | null {
  const definition = getPlatformAddonDefinition(catalog, addonType)
  if (!definition) return 'Platform add-on pricing is unavailable'

  const cloudKey = normalize(cloud)
  const tierKey = normalize(tier)
  const cloudConfig = definition.clouds[cloudKey]
  if (!cloudConfig) {
    return `${definition.display_name} is not available on ${cloudKey}`
  }
  if (!cloudConfig.eligible_tiers.map(normalize).includes(tierKey)) {
    return `${definition.display_name} requires ${cloudConfig.eligible_tiers.join(' or ')} tier on ${cloudKey}`
  }
  return null
}

export function getPlatformAddonRate(
  catalog: PlatformAddonCatalog,
  addonType: PlatformAddonType,
  cloud: string,
  tier: string,
  pricingDate: Date = new Date(),
): PlatformAddonRate | null {
  if (getPlatformAddonAvailabilityError(catalog, addonType, cloud, tier)) {
    return null
  }

  const definition = catalog.addons[addonType]
  const cloudConfig = definition.clouds[normalize(cloud)]
  const standardRatePct = cloudConfig.standard_rate_pct
  let appliedRatePct = standardRatePct
  let promotionLabel: string | undefined
  let promotionEndDate: string | undefined

  if (cloudConfig.promotion) {
    const endDate = new Date(`${cloudConfig.promotion.end_date}T23:59:59Z`)
    if (pricingDate.getTime() <= endDate.getTime()) {
      appliedRatePct = cloudConfig.promotion.rate_pct
      promotionLabel = cloudConfig.promotion.label
      promotionEndDate = cloudConfig.promotion.end_date
    }
  }

  return {
    addonType,
    displayName: definition.display_name,
    sku: definition.sku,
    standardRatePct,
    appliedRatePct,
    promotionLabel,
    promotionEndDate,
    sourceUrl: catalog.source_url,
  }
}

export function calculatePlatformAddonCost(
  catalog: PlatformAddonCatalog,
  addonType: PlatformAddonType | null,
  cloud: string,
  tier: string,
  productSpendAtList: number,
  discountPct: number = 0,
  pricingDate: Date = new Date(),
): PlatformAddonCost | null {
  if (!addonType) return null
  const rate = getPlatformAddonRate(
    catalog,
    addonType,
    cloud,
    tier,
    pricingDate,
  )
  if (!rate) return null

  const spend = Number.isFinite(productSpendAtList)
    ? Math.max(0, productSpendAtList)
    : 0
  const discount = Number.isFinite(discountPct)
    ? Math.min(100, Math.max(0, discountPct))
    : 0
  const costBeforeDiscount = spend * rate.appliedRatePct / 100
  const discountAmount = costBeforeDiscount * discount / 100
  return {
    ...rate,
    productSpendAtList: spend,
    standardCost: spend * rate.standardRatePct / 100,
    costBeforeDiscount,
    discountPct: discount,
    discountAmount,
    cost: costBeforeDiscount - discountAmount,
  }
}

export function getPlatformAddonDiscountPct(
  discountConfig: unknown,
): number {
  if (!discountConfig || typeof discountConfig !== 'object') return 0
  const globalDiscounts = (discountConfig as Record<string, unknown>).global
  if (!globalDiscounts || typeof globalDiscounts !== 'object') return 0
  const value = Number(
    (globalDiscounts as Record<string, unknown>).platform_addon_discount ?? 0,
  )
  return Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0
}
