/**
 * T-shirt sizing and cost math for Lakehouse Federation.
 *
 * MUST stay in sync with backend/app/services/lakehouse_federation_sizing.py — the tests
 * compare the two.
 *
 * Serverless SQL warehouses bill on warehouse UPTIME, not query-seconds: auto-stop keeps the
 * warehouse warm between queries. Modeling a federated workload as a fixed number of "hours of
 * querying" therefore massively overstates cost.
 */

export const WAREHOUSE_DBU_PER_HOUR: Record<string, number> = {
  '2X-Small': 4,
  'X-Small': 6,
  'Small': 12,
  'Medium': 24,
  'Large': 40,
  'X-Large': 80,
  '2X-Large': 144,
  '3X-Large': 272,
  '4X-Large': 528,
}

export interface FederationTier {
  num_users: number
  queries_per_day: number
  warehouse_size: string
}

/** Sized by number of users running federated queries. */
export const FEDERATION_TIERS: Record<string, FederationTier> = {
  S: { num_users: 10, queries_per_day: 20, warehouse_size: '2X-Small' },
  M: { num_users: 50, queries_per_day: 100, warehouse_size: '2X-Small' },
  L: { num_users: 150, queries_per_day: 500, warehouse_size: 'X-Small' },
  XL: { num_users: 500, queries_per_day: 2000, warehouse_size: 'Small' },
}

export const TIER_LABELS: Record<string, string> = {
  S: 'Small', M: 'Medium', L: 'Large', XL: 'Extra Large', custom: 'Custom',
}

export function warehouseDbuPerHour(size?: string | null): number {
  return WAREHOUSE_DBU_PER_HOUR[size || '2X-Small'] ?? 4
}

export function normalizeQueriesPerDay(
  queriesPerPeriod: number, period?: string | null, daysPerMonth = 22,
): number {
  const p = (period || 'day').toLowerCase()
  if (p === 'month') return queriesPerPeriod / Math.max(1, daysPerMonth)
  if (p === 'week') return queriesPerPeriod / 5  // active weekdays
  return queriesPerPeriod
}

export function federationWarehouseHours(opts: {
  queriesPerDay: number
  avgQuerySeconds?: number
  autoStopMinutes?: number
  activeHoursPerDay?: number
  daysPerMonth?: number
}): { hours_per_month: number; saturated: boolean; queries_per_month: number; execution_hours_per_month: number; regime: string } {
  const qd = opts.queriesPerDay
  const sec = opts.avgQuerySeconds ?? 10
  const autoStop = opts.autoStopMinutes ?? 10
  const activeH = opts.activeHoursPerDay ?? 8
  const days = opts.daysPerMonth ?? 22

  if (qd <= 0) {
    return { hours_per_month: 0, saturated: false, queries_per_month: 0, execution_hours_per_month: 0, regime: 'none' }
  }

  const queriesPerMonth = qd * days
  const executionHours = (queriesPerMonth * sec) / 3600
  const ceiling = activeH * days
  const minutesBetween = (activeH * 60) / qd

  const perQueryHours = (queriesPerMonth * (autoStop + sec / 60)) / 60
  const burstsPerDay = Math.min(qd, Math.max(1, activeH))
  const idleCappedHours = executionHours + (burstsPerDay * days * autoStop) / 60

  if (minutesBetween < autoStop) {
    const hours = Math.min(ceiling, idleCappedHours)
    const regime = hours >= ceiling - 1e-9 ? 'continuously_warm' : 'idle_capped'
    return {
      hours_per_month: hours, saturated: regime === 'continuously_warm',
      queries_per_month: queriesPerMonth, execution_hours_per_month: executionHours, regime,
    }
  }

  const hours = Math.min(ceiling, perQueryHours, idleCappedHours)
  return {
    hours_per_month: hours, saturated: false, queries_per_month: queriesPerMonth,
    execution_hours_per_month: executionHours, regime: 'bursty',
  }
}

export function resolveFederationConfig(opts: {
  size?: string | null
  numUsers?: number | null
  queriesPerPeriod?: number | null
  queryPeriod?: string | null
  warehouseSize?: string | null
  daysPerMonth?: number
}): { num_users: number; queries_per_day: number; warehouse_size: string } {
  const key = (opts.size || 'M').toUpperCase()
  const tier = FEDERATION_TIERS[key] ?? FEDERATION_TIERS.M
  const queriesPerDay = opts.queriesPerPeriod == null
    ? tier.queries_per_day
    : normalizeQueriesPerDay(opts.queriesPerPeriod, opts.queryPeriod, opts.daysPerMonth ?? 22)
  return {
    num_users: opts.numUsers ?? tier.num_users,
    queries_per_day: queriesPerDay,
    warehouse_size: opts.warehouseSize || tier.warehouse_size,
  }
}
