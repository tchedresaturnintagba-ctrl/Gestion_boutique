import { useState, type FormEvent } from 'react'
import { LoaderCircle, SlidersHorizontal, X } from 'lucide-react'
import type { Product, Store, StoreProduct, StoreProductInput } from '../lib/api'

interface ProductConfigurationDialogProps {
  product: Product
  stores: Store[]
  configurations: StoreProduct[]
  defaultStoreId: string
  onClose: () => void
  onSubmit: (storeId: string, input: StoreProductInput) => Promise<void>
}

const moneyFormatter = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'XOF',
  maximumFractionDigits: 0,
})

export function ProductConfigurationDialog({ product, stores, configurations, defaultStoreId, onClose, onSubmit }: ProductConfigurationDialogProps) {
  const activeStores = stores.filter((store) => store.is_active)
  const initialStoreId = activeStores.some((store) => store.id === defaultStoreId) ? defaultStoreId : activeStores[0]?.id ?? ''
  const initialConfiguration = configurations.find((item) => item.store_id === initialStoreId && item.product_id === product.id)
  const [storeId, setStoreId] = useState(initialStoreId)
  const [unitPrice, setUnitPrice] = useState(String(initialConfiguration?.unit_price ?? ''))
  const [threshold, setThreshold] = useState(initialConfiguration?.low_stock_threshold ?? '0.000')
  const [isActive, setIsActive] = useState(initialConfiguration?.is_active ?? true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleStoreChange(nextStoreId: string) {
    setStoreId(nextStoreId)
    const configuration = configurations.find((item) => item.store_id === nextStoreId && item.product_id === product.id)
    setUnitPrice(String(configuration?.unit_price ?? ''))
    setThreshold(configuration?.low_stock_threshold ?? '0.000')
    setIsActive(configuration?.is_active ?? true)
    setError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit(storeId, {
        unit_price: Number(unitPrice),
        low_stock_threshold: threshold,
        is_active: isActive,
      })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Configuration impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="configuration-dialog" role="dialog" aria-modal="true" aria-labelledby="configuration-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="dialog-heading">
          <div><p className="eyebrow">PRIX & STOCK</p><h2 id="configuration-dialog-title">Configurer {product.name}</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer"><X size={19} /></button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="configuration-store">Boutique
            <select id="configuration-store" value={storeId} onChange={(event) => handleStoreChange(event.target.value)} required>
              {activeStores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
            </select>
          </label>
          <div className="form-columns equal">
            <label className="field-label" htmlFor="configuration-price">Prix unitaire (FCFA)
              <input id="configuration-price" type="number" inputMode="numeric" min="0" step="1" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} placeholder="0" required />
            </label>
            <label className="field-label" htmlFor="configuration-threshold">Seuil de stock faible
              <input id="configuration-threshold" type="number" inputMode="decimal" min="0" step="0.001" value={threshold} onChange={(event) => setThreshold(event.target.value)} required />
            </label>
          </div>
          <div className="configuration-summary"><SlidersHorizontal size={18} /><span>Prix affiché</span><strong>{moneyFormatter.format(Number(unitPrice || 0))}</strong></div>
          <label className="toggle-field"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} /><span><strong>Configuration active</strong><small>Produit disponible pour les opérations de cette boutique</small></span></label>
          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending || !storeId}>{pending && <LoaderCircle className="spin" size={17} />}{pending ? 'Enregistrement…' : 'Enregistrer'}</button>
          </footer>
        </form>
      </section>
    </div>
  )
}