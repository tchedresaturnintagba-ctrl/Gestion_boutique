import { useState, type FormEvent } from 'react'
import { Check, LoaderCircle, Pencil, Plus, Power, PowerOff, X } from 'lucide-react'
import type { Category } from '../lib/api'

interface CategoryDialogProps {
  categories: Category[]
  onClose: () => void
  onCreate: (name: string) => Promise<void>
  onUpdate: (category: Category, changes: { name?: string; is_active?: boolean }) => Promise<void>
}

export function CategoryDialog({ categories, onClose, onCreate, onUpdate }: CategoryDialogProps) {
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function run(id: string, action: () => Promise<void>) {
    setPendingId(id)
    setError(null)
    try {
      await action()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Opération impossible')
    } finally {
      setPendingId(null)
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await run('new', async () => {
      await onCreate(newName.trim())
      setNewName('')
    })
  }

  async function handleRename(category: Category) {
    await run(category.id, async () => {
      await onUpdate(category, { name: editingName.trim() })
      setEditingId(null)
    })
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="category-dialog" role="dialog" aria-modal="true" aria-labelledby="category-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="dialog-heading">
          <div><p className="eyebrow">CATALOGUE CENTRAL</p><h2 id="category-dialog-title">Catégories</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer"><X size={19} /></button>
        </header>
        <div className="category-dialog-body">
          {error && <div className="form-error" role="alert">{error}</div>}
          <form className="category-create" onSubmit={handleCreate}>
            <label className="sr-only" htmlFor="new-category">Nouvelle catégorie</label>
            <input id="new-category" value={newName} onChange={(event) => setNewName(event.target.value)} minLength={2} maxLength={120} placeholder="Nouvelle catégorie" required />
            <button className="primary-button" type="submit" disabled={pendingId === 'new'}>{pendingId === 'new' ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}Ajouter</button>
          </form>
          <div className="category-list">
            {categories.length === 0 && <div className="sale-empty">Aucune catégorie enregistrée.</div>}
            {categories.map((category) => (
              <div className={`category-row ${category.is_active ? '' : 'inactive'}`} key={category.id}>
                {editingId === category.id ? (
                  <input aria-label={`Nouveau nom de ${category.name}`} value={editingName} onChange={(event) => setEditingName(event.target.value)} minLength={2} maxLength={120} autoFocus />
                ) : (
                  <div><strong>{category.name}</strong><span>{category.is_active ? 'Active' : 'Inactive'}</span></div>
                )}
                <div className="category-actions">
                  {editingId === category.id ? (
                    <button type="button" onClick={() => void handleRename(category)} disabled={pendingId === category.id || editingName.trim().length < 2} aria-label={`Enregistrer ${category.name}`} title="Enregistrer"><Check size={15} /></button>
                  ) : (
                    <button type="button" onClick={() => { setEditingId(category.id); setEditingName(category.name) }} aria-label={`Renommer ${category.name}`} title="Renommer"><Pencil size={15} /></button>
                  )}
                  <button type="button" className={category.is_active ? 'danger' : 'activate'} onClick={() => void run(category.id, () => onUpdate(category, { is_active: !category.is_active }))} disabled={pendingId === category.id} aria-label={`${category.is_active ? 'Désactiver' : 'Réactiver'} ${category.name}`} title={category.is_active ? 'Désactiver' : 'Réactiver'}>{category.is_active ? <PowerOff size={15} /> : <Power size={15} />}</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}