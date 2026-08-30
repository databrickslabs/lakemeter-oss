import geographyCatalog from '../data/region-geographies.json'

export const OTHER_REGIONS_GROUP = 'Other Regions'

type SupportedCloud = keyof typeof geographyCatalog

interface CloudGeographyCatalog {
  group_order: string[]
  regions: Record<string, string>
}

const catalog = geographyCatalog as Record<
  SupportedCloud,
  CloudGeographyCatalog
>

export const REGION_GEOGRAPHY_ORDER = {
  aws: catalog.aws.group_order,
  azure: catalog.azure.group_order,
  gcp: catalog.gcp.group_order,
}

export interface RegionOption {
  value: string
  label: string
  group: string
}

export interface RegionOptionGroup {
  name: string
  options: RegionOption[]
}

function normalizeCloud(cloud: string): SupportedCloud | null {
  const normalized = cloud.trim().toLowerCase()
  return normalized in REGION_GEOGRAPHY_ORDER
    ? (normalized as SupportedCloud)
    : null
}

export function getRegionGeography(cloud: string, regionCode: string): string {
  const normalizedCloud = normalizeCloud(cloud)
  const region = regionCode.trim().toLowerCase()
  return normalizedCloud
    ? catalog[normalizedCloud].regions[region] ?? OTHER_REGIONS_GROUP
    : OTHER_REGIONS_GROUP
}

export function getRegionGeographyOrder(cloud: string): string[] {
  const normalizedCloud = normalizeCloud(cloud)
  return normalizedCloud
    ? [...REGION_GEOGRAPHY_ORDER[normalizedCloud]]
    : [OTHER_REGIONS_GROUP]
}

export function createRegionOptions(
  cloud: string,
  regions: Array<{ region_code: string; sku_region?: string }>,
): RegionOption[] {
  return regions
    .map((region) => ({
      value: region.region_code,
      label: region.sku_region && region.sku_region !== region.region_code
        ? `${region.region_code} (${region.sku_region})`
        : region.region_code,
      group: getRegionGeography(cloud, region.region_code),
    }))
    .sort((left, right) => left.label.localeCompare(right.label))
}

export function createRegionOptionsFromCodes(
  cloud: string,
  regionCodes: string[],
): RegionOption[] {
  return createRegionOptions(
    cloud,
    regionCodes.map((regionCode) => ({ region_code: regionCode })),
  )
}

export function groupRegionOptions(
  cloud: string,
  options: RegionOption[],
): RegionOptionGroup[] {
  const byGroup = new Map<string, RegionOption[]>()
  for (const option of options) {
    const existing = byGroup.get(option.group) ?? []
    existing.push(option)
    byGroup.set(option.group, existing)
  }

  return getRegionGeographyOrder(cloud)
    .filter((groupName) => byGroup.has(groupName))
    .map((groupName) => ({
      name: groupName,
      options: byGroup.get(groupName) ?? [],
    }))
}
