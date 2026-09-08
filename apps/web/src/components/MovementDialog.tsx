import { useState, type FormEvent } from 'react'
import { ArrowDownToLine, ArrowUpFromLine, LoaderCircle, X } from 'lucide-react'
import type { ManualStockMovementType, Product, StockMovementInput, Store, StoreProduct } from '../lib/api'

interface MovementDialogProps {
  stores: Store[]
  products: Product[]
  configurations: StoreProduct[]
  defaultStoreId: string
  onClose: () => void
  onSubmit: (storeId: string, input: StockMovementInput) => Promise<void>
}

const movementLabels: Record<ManualStockMovementType, string> = {
  entry: 'Entrée de stock',
  adjustment_in: 'Ajustement positif',
  adjustment_out: 'Ajustement négatif',
}

export function MovementDialog({ stores, products, configurations, defaultStoreId, onClose, onSubmit }: MovementDialogProps) {
  const initialStoreId = defaultStoreId || stores[0]?.id || ''
  const initialProducts = configurations.filter((configuration) => configuration.store_id === initialStoreId && configuration.is_active)
  const [storeId, setStoreId] = useState(initialStoreId)
  const [productId, setProductId] = useState(initialProducts[0]?.product_id ?? '')
  const [movementType, setMovementType] = useState<ManualStockMovementType>('entry')
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const availableProductIds = new Set(configurations.filter((configuration) => configuration.store_id === storeId && configuration.is_active).map((configuration) => configuration.product_id))
  const availableProducts = products.filter((product) => product.is_active && availableProductIds.has(product.id))

  function handleStoreChange(nextStoreId: string) {
    setStoreId(nextStoreId)
    const firstConfiguration = configurations.find((configuration) => configuration.store_id === nextStoreId && configuration.is_active)
    setProductId(firstConfiguration?.product_id ?? '')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit(storeId, { product_id: productId, movement_type: movementType, quantity, reason })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Mouvement impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="movement-dialog" role="dialog" aria-modal="true" aria-labelledby="movement-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="dialog-heading">
          <div><p className="eyebrow">INVENTAIRE</p><h2 id="movement-title">Nouveau mouvement</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer"><X size={19} /></button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="movement-store">Boutique
            <select id="movement-store" value={storeId} onChange={(event) => handleStoreChange(event.target.value)} required>
              {stores.filter((store) => store.is_active).map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
            </select>
          </label>
          <label className="field-label" htmlFor="movement-product">Produit
            <select id="movement-product" value={productId} onChange={(event) => setProductId(event.target.value)} required>
              {availableProducts.length === 0 && <option value="">Aucun produit configuré</option>}
              {availableProducts.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
            </select>
          </label>
          <fieldset className="movement-kind">
            <legend>Type de mouvement</legend>
            {(Object.keys(movementLabels) as ManualStockMovementType[]).map((type) => (
              <label key={type} className={movementType === type ? 'selected' : ''}>
                <input type="radio" name="movement-type" value={type} checked={movementType === type} onChange={() => setMovementType(type)} />
                {type === 'adjustment_out' ? <ArrowUpFromLine size={17} /> : <ArrowDownToLine size={17} />}
                <span>{movementLabels[type]}</span>
              </label>
            ))}
          </fieldset>
          <div className="form-columns">
            <label className="field-label" htmlFor="movement-quantity">Quantité
              <input id="movement-quantity" type="number" inputMode="decimal" min="0.001" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="0,000" required />
            </label>
            <label className="field-label" htmlFor="movement-reason">Motif
              <input id="movement-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Livraison, inventaire…" minLength={2} maxLength={255} required />
            </label>
          </div>
          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending || !productId}>
              {pending && <LoaderCircle className="spin" size={17} />}{pending ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}