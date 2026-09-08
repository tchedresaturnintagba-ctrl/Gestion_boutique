import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, LoaderCircle, LockKeyhole, Mail, ShoppingBag } from 'lucide-react'
import type { LoginCredentials } from '../lib/api'

interface LoginScreenProps {
  onLogin: (credentials: LoginCredentials) => Promise<void>
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [organizationSlug, setOrganizationSlug] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await onLogin({
        organization_slug: organizationSlug.trim().toLowerCase(),
        email: email.trim().toLowerCase(),
        password,
      })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Connexion impossible')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro" aria-label="KërManager">
        <div className="login-brand">
          <span className="brand-symbol"><ShoppingBag size={22} /></span>
          <span>Kër<span>Manager</span></span>
        </div>
        <div className="login-statement">
          <p className="eyebrow">GESTION MULTI-BOUTIQUES</p>
          <h1>Vos stocks.<br />Une seule vue.</h1>
          <p>Suivez chaque boutique et agissez dès qu’un niveau de stock demande votre attention.</p>
        </div>
        <div className="login-footnote">Données isolées et sécurisées par organisation</div>
      </section>

      <section className="login-form-side">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form-heading">
            <span className="login-lock"><LockKeyhole size={19} /></span>
            <div><h2>Connexion</h2><p>Accédez à votre espace de gestion.</p></div>
          </div>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label className="field-label" htmlFor="organization">
            Organisation
            <span className="input-shell">
              <ShoppingBag size={17} />
              <input id="organization" value={organizationSlug} onChange={(event) => setOrganizationSlug(event.target.value)} placeholder="mon-organisation" autoComplete="organization" required minLength={2} />
            </span>
          </label>
          <label className="field-label" htmlFor="email">
            Adresse e-mail
            <span className="input-shell">
              <Mail size={17} />
              <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="gestionnaire@entreprise.com" autoComplete="email" required />
            </span>
          </label>
          <label className="field-label" htmlFor="password">
            Mot de passe
            <span className="input-shell">
              <LockKeyhole size={17} />
              <input id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Votre mot de passe" autoComplete="current-password" required minLength={8} />
              <button className="field-icon-button" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'} title={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}>
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
          </label>
          <button className="login-button" type="submit" disabled={pending}>
            {pending && <LoaderCircle className="spin" size={17} />}
            {pending ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </section>
    </main>
  )
}