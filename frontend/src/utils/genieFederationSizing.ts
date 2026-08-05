/**
 * T-shirt sizing and cost math for Genie, Genie Code, and Lakehouse Federation.
 *
 * MUST stay in sync with backend/app/services/genie_federation_sizing.py — the parity tests
 * compare the two.
 *
 * Two billing realities drive these models:
 *  - Genie LLM bills in DBUs on the Serverless Realtime Inference (SRTI) SKU, with 150 free
 *    DBUs per identified user per month and a 25% intro promo on paid DBUs.
 *  - Serverless SQL warehouses (underneath both Genie and Federation) bill on warehouse
 *    UPTIME, not query-seconds: auto-stop keeps the warehouse warm between queries.
 */

/** Free LLM allowance per identified user per month (fixed program rule, not an input). */
export const FREE_DBUS_PER_USER = 150

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

export interface GenieTier {
  num_users: number
  dbus_per_user: number
  active_hours: number
  warehouse_size: string
}

/** active_hours: 88 = warm half the workday; 176 = warm all workday (8h x 22d). */
export const GENIE_TIERS: Record<string, GenieTier> = {
  S: { num_users: 10, dbus_per_user: 150, active_hours: 88, warehouse_size: '2X-Small' },
  M: { num_users: 50, dbus_per_user: 250, active_hours: 176, warehouse_size: '2X-Small' },
  L: { num_users: 150, dbus_per_user: 400, active_hours: 176, warehouse_size: 'X-Small' },
  XL: { num_users: 500, dbus_per_user: 600, active_hours: 176, warehouse_size: 'Small' },
}

export interface FederationTier {
  num_users: number
  queries_per_day: number
  warehouse_size: string
}

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

/** Resolve a Genie config from a t-shirt size; explicit values take precedence. */
export function resolveGenieConfig(opts: {
  size?: string | null
  numUsers?: number | null
  dbusPerUser?: number | null
  warehouseSize?: string | null
  activeHours?: number | null
}): { num_users: number; dbus_per_user: number; active_hours: number; warehouse_size: string } {
  const key = (opts.size || 'M').toUpperCase()
  const tier = GENIE_TIERS[key] ?? GENIE_TIERS.M
  return {
    num_users: opts.numUsers ?? tier.num_users,
    dbus_per_user: opts.dbusPerUser ?? tier.dbus_per_user,
    active_hours: opts.activeHours ?? tier.active_hours,
    warehouse_size: opts.warehouseSize || tier.warehouse_size,
  }
}

/** Billable LLM DBUs after the free allowance and intro promo. */
export function calculateGenieLlmDbus(opts: {
  numUsers: number
  dbusPerUser: number
  numServicePrincipals?: number
  dbusPerSp?: number
  applyPromo?: boolean
  promoPct?: number
}): { free_dbus: number; gross_paid_dbus: number; billable_dbus: number } {
  const perUserPaid = Math.max(0, opts.dbusPerUser - FREE_DBUS_PER_USER)
  const userPaid = perUserPaid * opts.numUsers
  const userFree = Math.min(opts.dbusPerUser, FREE_DBUS_PER_USER) * opts.numUsers
  const spPaid = (opts.dbusPerSp ?? 0) * (opts.numServicePrincipals ?? 0)
  const grossPaid = userPaid + spPaid
  const promoFactor = (opts.applyPromo ?? true) ? 1 - (opts.promoPct ?? 25) / 100 : 1
  return { free_dbus: userFree, gross_paid_dbus: grossPaid, billable_dbus: grossPaid * promoFactor }
}

/** Convert a per-day/week/month query volume into queries per active day. */
export function normalizeQueriesPerDay(
  queriesPerPeriod: number, period?: string | null, daysPerMonth = 22,
): number {
  const p = (period || 'day').toLowerCase()
  if (p === 'month') return queriesPerPeriod / Math.max(1, daysPerMonth)
  if (p === 'week') return queriesPerPeriod / 5  // active weekdays
  return queriesPerPeriod
}

/**
 * Warehouse uptime hours/month for a bursty query workload.
 *
 * Takes the smallest of three bounds: per-query hold, continuously-warm ceiling, and an
 * idle-overhead cap (execution time plus one auto-stop tail per busy block). The idle cap
 * prevents a light workload spread across the day from billing an always-on warehouse.
 */
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

/** Resolve a Federation config from a t-shirt size; explicit values take precedence. */
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
