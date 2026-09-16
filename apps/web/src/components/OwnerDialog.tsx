import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, LoaderCircle, Mail, UserRound, X } from 'lucide-react'
import type { Owner, Store } from '../lib/api'

export interface OwnerFormInput {
  email: string
  full_name: string
  password?: string
  new_password?: string
  store_ids: string[]
}

interface OwnerDialogProps {
  owner: Owner | null
  stores: Store[]
  onClose: () => void
  onSubmit: (input: OwnerFormInput) => Promise<void>
}

export function OwnerDialog({ owner, stores, onClose, onSubmit }: OwnerDialogProps) {
  const [fullName, setFullName] = useState(owner?.full_name ?? '')
  const [email, setEmail] = useState(owner?.email ?? '')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [selectedStoreIds, setSelectedStoreIds] = useState(() => new Set(owner?.store_ids ?? []))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggleStore(storeId: string) {
    setSelectedStoreIds((current) => {
      const next = new Set(current)
      if (next.has(storeId)) next.delete(storeId)
      else next.add(storeId)
      return next
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit({
        email: email.trim().toLowerCase(),
        full_name: fullName.trim(),
        password: owner ? undefined : password,
        new_password: owner && password ? password : undefined,
        store_ids: [...selectedStoreIds],
      })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Enregistrement impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="owner-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="owner-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="dialog-heading">
          <div>
            <p className="eyebrow">ACCÈS PROPRIÉTAIRE</p>
            <h2 id="owner-dialog-title">{owner ? 'Modifier le propriétaire' : 'Nouveau propriétaire'}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer">
            <X size={19} />
          </button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="owner-name">Nom complet
            <span className="input-shell">
              <UserRound size={17} />
              <input
                id="owner-name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                minLength={2}
                maxLength={160}
                placeholder="Awa Ndiaye"
                autoFocus
                required
              />
            </span>
          </label>
          <label className="field-label" htmlFor="owner-email">Adresse e-mail
            <span className="input-shell">
              <Mail size={17} />
              <input
                id="owner-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="proprietaire@entreprise.com"
                required
              />
            </span>
          </label>
          <label className="field-label" htmlFor="owner-password">
            {owner ? 'Nouveau mot de passe (facultatif)' : 'Mot de passe initial'}
            <span className="input-shell">
              <input
                id="owner-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={12}
                maxLength={128}
                placeholder="12 caractères minimum"
                required={!owner}
              />
              <button
                className="field-icon-button"
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                title={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </span>
          </label>

          <fieldset className="owner-stores">
            <legend>Boutiques accessibles</legend>
            {stores.length === 0 ? (
              <p>Aucune boutique disponible.</p>
            ) : (
              <div className="owner-store-list">
                {stores.map((store) => (
                  <label className={selectedStoreIds.has(store.id) ? 'selected' : ''} key={store.id}>
                    <input
                      type="checkbox"
                      checked={selectedStoreIds.has(store.id)}
                      onChange={() => toggleStore(store.id)}
                    />
                    <span><strong>{store.name}</strong><small>{store.code}{store.is_active ? '' : ' · Suspendue'}</small></span>
                  </label>
                ))}
              </div>
            )}
          </fieldset>

          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending}>
              {pending && <LoaderCircle className="spin" size={17} />}
              {pending ? 'Enregistrement…' : owner ? 'Enregistrer' : 'Créer le propriétaire'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}