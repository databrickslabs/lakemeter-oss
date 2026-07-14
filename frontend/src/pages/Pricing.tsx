import { Suspense, lazy, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import SkuExplorer from '../components/SkuExplorer'

const FmapiTokenHelper = lazy(() => import('../components/FmapiTokenHelper'))

type PricingView = 'skus' | 'fmapi-tokens'

function PricingTabNav({
  value,
  onChange,
}: {
  value: PricingView
  onChange: (value: PricingView) => void
}) {
  const tab = (key: PricingView, label: string) => (
    <button
      key={key}
      type="button"
      role="tab"
      aria-selected={value === key}
      onClick={() => onChange(key)}
      className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
        value === key
          ? 'border-lava-600 text-[var(--text-primary)]'
          : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div role="tablist" aria-label="Pricing views" className="flex items-center gap-1">
      {tab('skus', 'SKU Explorer')}
      {tab('fmapi-tokens', 'FMAPI Tokens')}
    </div>
  )
}

function FxRateField({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <div className="flex items-center gap-2 pb-1.5">
      <label
        htmlFor="pricing-fx-rate"
        className="text-xs font-medium text-[var(--text-muted)] whitespace-nowrap"
        title="Multiplies all displayed prices. 1 = USD list prices."
      >
        USD -&gt; local FX
      </label>
      <input
        id="pricing-fx-rate"
        type="number"
        min={0}
        step="0.01"
        value={value}
        onChange={(event) => onChange(Number(event.target.value) || 1)}
        className="w-24 text-right text-sm"
      />
    </div>
  )
}

export default function Pricing() {
  const [params, setParams] = useSearchParams()
  const view: PricingView = params.get('view') === 'fmapi-tokens' ? 'fmapi-tokens' : 'skus'
  const [fxRate, setFxRate] = useState(1)

  const setView = (next: PricingView) => {
    const nextParams = new URLSearchParams(params)
    if (next === 'skus') {
      nextParams.delete('view')
    } else {
      nextParams.set('view', next)
    }
    setParams(nextParams, { replace: false })
  }

  return (
    <div className="max-w-7xl xl:max-w-[1400px] 2xl:max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-8">
      <div className="flex items-end justify-between gap-4 border-b border-[var(--border-primary)] mb-6">
        <PricingTabNav value={view} onChange={setView} />
        <FxRateField value={fxRate} onChange={setFxRate} />
      </div>

      {view === 'skus' && <SkuExplorer fxRate={fxRate} />}
      {view === 'fmapi-tokens' && (
        <Suspense fallback={<div className="py-12 text-center text-sm text-[var(--text-muted)]">Loading FMAPI rates...</div>}>
          <FmapiTokenHelper fxRate={fxRate} />
        </Suspense>
      )}
    </div>
  )
}
