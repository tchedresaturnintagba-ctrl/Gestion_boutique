import { useState, type FormEvent } from 'react'
import { LoaderCircle, Plus, ReceiptText, Trash2, X } from 'lucide-react'
import type {
  InventoryBalance,
  Product,
  SaleInput,
  Store,
  StoreProduct,
} from '../lib/api'

interface SaleDialogProps {
  stores: Store[]
  products: Product[]
  configurations: StoreProduct[]
  balances: InventoryBalance[]
  defaultStoreId: string
  onClose: () => void
  onSubmit: (input: SaleInput) => Promise<void>
}

interface DraftLine {
  productId: string
  quantity: string
}

const moneyFormatter = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'XOF',
  maximumFractionDigits: 0,
})
const quantityFormatter = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 3 })

export function SaleDialog({
  stores,
  products,
  configurations,
  balances,
  defaultStoreId,
  onClose,
  onSubmit,
}: SaleDialogProps) {
  const activeStores = stores.filter((store) => store.is_active)
  const initialStoreId = defaultStoreId || activeStores[0]?.id || ''
  const firstProductId = configurations.find(
    (configuration) => configuration.store_id === initialStoreId && configuration.is_active,
  )?.product_id
  const [storeId, setStoreId] = useState(initialStoreId)
  const [lines, setLines] = useState<DraftLine[]>(
    firstProductId ? [{ productId: firstProductId, quantity: '' }] : [],
  )
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const productById = new Map(products.map((product) => [product.id, product]))
  const configurationsForStore = configurations.filter(
    (configuration) => configuration.store_id === storeId && configuration.is_active,
  )
  const configurationByProduct = new Map(
    configurationsForStore.map((configuration) => [configuration.product_id, configuration]),
  )
  const balanceByProduct = new Map(
    balances
      .filter((balance) => balance.store_id === storeId)
      .map((balance) => [balance.product_id, balance]),
  )
  const availableProducts = configurationsForStore
    .map((configuration) => productById.get(configuration.product_id))
    .filter((product): product is Product => Boolean(product?.is_active))
  const selectedProductIds = new Set(lines.map((line) => line.productId))
  const nextProduct = availableProducts.find((product) => !selectedProductIds.has(product.id))
  const total = lines.reduce((sum, line) => {
    const price = configurationByProduct.get(line.productId)?.unit_price ?? 0
    return sum + price * Number(line.quantity || 0)
  }, 0)

  function handleStoreChange(nextStoreId: string) {
    setStoreId(nextStoreId)
    const nextProductId = configurations.find(
      (configuration) => configuration.store_id === nextStoreId && configuration.is_active,
    )?.product_id
    setLines(nextProductId ? [{ productId: nextProductId, quantity: '' }] : [])
    setError(null)
  }

  function updateLine(index: number, changes: Partial<DraftLine>) {
    setLines((current) => current.map((line, lineIndex) => (
      lineIndex === index ? { ...line, ...changes } : line
    )))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit({
        store_id: storeId,
        lines: lines.map((line) => ({
          product_id: line.productId,
          quantity: line.quantity,
        })),
      })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Vente impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="sale-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sale-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="dialog-heading">
          <div><p className="eyebrow">ENCAISSEMENT</p><h2 id="sale-title">Nouvelle vente</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer"><X size={19} /></button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="sale-store">Boutique
            <select id="sale-store" value={storeId} onChange={(event) => handleStoreChange(event.target.value)} required>
              {activeStores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
            </select>
          </label>

          <div className="sale-lines-heading">
            <div><strong>Produits vendus</strong><span>{lines.length} ligne{lines.length > 1 ? 's' : ''}</span></div>
            <button
              className="add-line-button"
              type="button"
              onClick={() => nextProduct && setLines((current) => [...current, { productId: nextProduct.id, quantity: '' }])}
              disabled={!nextProduct}
            >
              <Plus size={15} />Ajouter
            </button>
          </div>

          <div className="sale-lines">
            {lines.length === 0 && <div className="sale-empty"><ReceiptText size={22} /><span>Aucun produit disponible dans cette boutique.</span></div>}
            {lines.map((line, index) => {
              const configuration = configurationByProduct.get(line.productId)
              const availableQuantity = Number(balanceByProduct.get(line.productId)?.quantity ?? 0)
              const lineTotal = (configuration?.unit_price ?? 0) * Number(line.quantity || 0)
              return (
                <div className="sale-line" key={`${index}:${line.productId}`}>
                  <label className="field-label">Produit
                    <select value={line.productId} onChange={(event) => updateLine(index, { productId: event.target.value })} required>
                      {availableProducts
                        .filter((product) => product.id === line.productId || !selectedProductIds.has(product.id))
                        .map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
                    </select>
                  </label>
                  <label className="field-label">Quantité
                    <input
                      type="number"
                      inputMode="decimal"
                      min="0.001"
                      max={availableQuantity}
                      step="0.001"
                      value={line.quantity}
                      onChange={(event) => updateLine(index, { quantity: event.target.value })}
                      placeholder="0,000"
                      required
                    />
                  </label>
                  <div className="sale-line-total">
                    <span>Montant</span>
                    <strong>{moneyFormatter.format(lineTotal)}</strong>
                    <small>{quantityFormatter.format(availableQuantity)} disponible</small>
                  </div>
                  <button
                    className="remove-line-button"
                    type="button"
                    onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}
                    aria-label="Supprimer la ligne"
                    title="Supprimer la ligne"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              )
            })}
          </div>

          <div className="sale-summary"><span>Total à encaisser</span><strong>{moneyFormatter.format(total)}</strong></div>
          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending || lines.length === 0}>
              {pending && <LoaderCircle className="spin" size={17} />}{pending ? 'Validation…' : 'Valider la vente'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
