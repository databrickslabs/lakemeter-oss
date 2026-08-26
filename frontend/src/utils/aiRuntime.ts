export type AIRuntimeAcceleratorType =
  | 'GPU_1xA10'
  | 'GPU_1xH100'
  | 'GPU_8xH100'

export interface AIRuntimeAccelerator {
  id: AIRuntimeAcceleratorType
  label: string
  gpuCount: number
  dbuPerGpuHour: number
}

const A10_AWS_DBU_PER_GPU_HOUR = 50 / 13
const A10_AZURE_DBU_PER_GPU_HOUR = 98 / 13
const H100_DBU_PER_GPU_HOUR = 140 / 13

export const AI_RUNTIME_ACCELERATORS: Record<
  'aws' | 'azure',
  AIRuntimeAccelerator[]
> = {
  aws: [
    {
      id: 'GPU_1xA10',
      label: '1x A10 (24 GB)',
      gpuCount: 1,
      dbuPerGpuHour: A10_AWS_DBU_PER_GPU_HOUR,
    },
    {
      id: 'GPU_1xH100',
      label: '1x H100 (80 GB)',
      gpuCount: 1,
      dbuPerGpuHour: H100_DBU_PER_GPU_HOUR,
    },
    {
      id: 'GPU_8xH100',
      label: '8x H100 (640 GB total)',
      gpuCount: 8,
      dbuPerGpuHour: H100_DBU_PER_GPU_HOUR,
    },
  ],
  azure: [
    {
      id: 'GPU_1xA10',
      label: '1x A10 (24 GB)',
      gpuCount: 1,
      dbuPerGpuHour: A10_AZURE_DBU_PER_GPU_HOUR,
    },
    {
      id: 'GPU_1xH100',
      label: '1x H100 (80 GB)',
      gpuCount: 1,
      dbuPerGpuHour: H100_DBU_PER_GPU_HOUR,
    },
    {
      id: 'GPU_8xH100',
      label: '8x H100 (640 GB total)',
      gpuCount: 8,
      dbuPerGpuHour: H100_DBU_PER_GPU_HOUR,
    },
  ],
}

export const getAIRuntimeAccelerators = (
  cloud: string,
): AIRuntimeAccelerator[] =>
  AI_RUNTIME_ACCELERATORS[
    cloud.toLowerCase() as 'aws' | 'azure'
  ] || []

export const getAIRuntimeAccelerator = (
  cloud: string,
  acceleratorType: string | null | undefined,
): AIRuntimeAccelerator | null => {
  const accelerators = getAIRuntimeAccelerators(cloud)
  return (
    accelerators.find(accelerator => accelerator.id === acceleratorType)
    || accelerators[0]
    || null
  )
}

export const calculateAIRuntimeUsage = (
  cloud: string,
  acceleratorType: string | null | undefined,
  runtimeHours: number,
) => {
  const accelerator = getAIRuntimeAccelerator(cloud, acceleratorType)
  if (!accelerator) {
    return {
      accelerator: null,
      runtimeHours: 0,
      monthlyGpuHours: 0,
      dbuPerNodeHour: 0,
      monthlyDBUs: 0,
    }
  }
  const safeHours = Number.isFinite(runtimeHours)
    ? Math.max(0, runtimeHours)
    : 0
  const dbuPerNodeHour = (
    accelerator.gpuCount * accelerator.dbuPerGpuHour
  )
  return {
    accelerator,
    runtimeHours: safeHours,
    monthlyGpuHours: safeHours * accelerator.gpuCount,
    dbuPerNodeHour,
    monthlyDBUs: safeHours * dbuPerNodeHour,
  }
}
