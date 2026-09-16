import { useState, type FormEvent } from 'react'
import { LoaderCircle, Package, X } from 'lucide-react'
import type { Category, Product, ProductInput, ProductUnit } from '../lib/api'

export type ProductFormInput = ProductInput & { is_active: boolean }

interface ProductDialogProps {
  product: Product | null
  categories: Category[]
  onClose: () => void
  onSubmit: (input: ProductFormInput) => Promise<void>
}

const unitLabels: Record<ProductUnit, string> = {
  piece: 'Pièce',
  pack: 'Paquet',
  kilogram: 'Kilogramme',
  liter: 'Litre',
}

export function ProductDialog({ product, categories, onClose, onSubmit }: ProductDialogProps) {
  const [name, setName] = useState(product?.name ?? '')
  const [sku, setSku] = useState(product?.sku ?? '')
  const [categoryId, setCategoryId] = useState(product?.category_id ?? '')
  const [unit, setUnit] = useState<ProductUnit>(product?.unit ?? 'piece')
  const [description, setDescription] = useState(product?.description ?? '')
  const [isActive, setIsActive] = useState(product?.is_active ?? true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit({
        category_id: categoryId || null,
        name: name.trim(),
        sku: sku.trim().toUpperCase(),
        description: description.trim() || null,
        unit,
        is_active: isActive,
      })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Enregistrement impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="product-dialog" role="dialog" aria-modal="true" aria-labelledby="product-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="dialog-heading">
          <div><p className="eyebrow">CATALOGUE CENTRAL</p><h2 id="product-dialog-title">{product ? 'Modifier le produit' : 'Nouveau produit'}</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer"><X size={19} /></button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="product-name">Nom
            <span className="input-shell"><Package size={17} /><input id="product-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={160} placeholder="Riz parfumé" autoFocus required /></span>
          </label>
          <div className="form-columns equal">
            <label className="field-label" htmlFor="product-sku">SKU
              <input id="product-sku" value={sku} onChange={(event) => setSku(event.target.value.toUpperCase())} minLength={1} maxLength={80} pattern="[A-Za-z0-9_.\-]+" placeholder="RIZ-25KG" required />
            </label>
            <label className="field-label" htmlFor="product-unit">Unité
              <select id="product-unit" value={unit} onChange={(event) => setUnit(event.target.value as ProductUnit)}>
                {(Object.entries(unitLabels) as Array<[ProductUnit, string]>).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <label className="field-label" htmlFor="product-category">Catégorie
            <select id="product-category" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">Sans catégorie</option>
              {categories.filter((category) => category.is_active || category.id === categoryId).map((category) => <option key={category.id} value={category.id}>{category.name}{category.is_active ? '' : ' (inactive)'}</option>)}
            </select>
          </label>
          <label className="field-label" htmlFor="product-description">Description
            <textarea id="product-description" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} rows={3} placeholder="Informations utiles sur le produit" />
          </label>
          {product && <label className="toggle-field"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} /><span><strong>Produit actif</strong><small>Disponible pour les configurations boutique</small></span></label>}
          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending}>{pending && <LoaderCircle className="spin" size={17} />}{pending ? 'Enregistrement…' : product ? 'Enregistrer' : 'Créer le produit'}</button>
          </footer>
        </form>
      </section>
    </div>
  )
}