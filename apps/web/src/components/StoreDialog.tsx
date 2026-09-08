import { useState, type FormEvent } from 'react'
import { LoaderCircle, MapPin, Store as StoreIcon, X } from 'lucide-react'
import type { Store, StoreInput } from '../lib/api'

interface StoreDialogProps {
  store: Store | null
  onClose: () => void
  onSubmit: (input: StoreInput) => Promise<void>
}

export function StoreDialog({ store, onClose, onSubmit }: StoreDialogProps) {
  const [name, setName] = useState(store?.name ?? '')
  const [code, setCode] = useState(store?.code ?? '')
  const [address, setAddress] = useState(store?.address ?? '')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onSubmit({
        name: name.trim(),
        code: code.trim().toUpperCase(),
        address: address.trim() || null,
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
        className="store-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="store-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="dialog-heading">
          <div>
            <p className="eyebrow">RÉSEAU DE VENTE</p>
            <h2 id="store-dialog-title">{store ? 'Modifier la boutique' : 'Nouvelle boutique'}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer" title="Fermer">
            <X size={19} />
          </button>
        </header>
        <form onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="store-name">Nom de la boutique
            <span className="input-shell">
              <StoreIcon size={17} />
              <input
                id="store-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                minLength={2}
                maxLength={160}
                placeholder="Boutique Plateau"
                autoFocus
                required
              />
            </span>
          </label>
          <label className="field-label" htmlFor="store-code">Code
            <input
              id="store-code"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              minLength={2}
              maxLength={40}
              pattern="[A-Za-z0-9_\-]+"
              placeholder="PLATEAU-01"
              required
            />
          </label>
          <label className="field-label" htmlFor="store-address">Adresse
            <span className="input-shell">
              <MapPin size={17} />
              <input
                id="store-address"
                value={address}
                onChange={(event) => setAddress(event.target.value)}
                maxLength={255}
                placeholder="Quartier, rue ou repère"
              />
            </span>
          </label>
          <footer className="dialog-actions">
            <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
            <button className="primary-button" type="submit" disabled={pending}>
              {pending && <LoaderCircle className="spin" size={17} />}
              {pending ? 'Enregistrement…' : store ? 'Enregistrer' : 'Créer la boutique'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
