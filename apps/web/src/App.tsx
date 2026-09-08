import { useDeferredValue, useEffect, useState } from 'react'
import {
  Banknote,
  Bell,
  Boxes,
  ChevronRight,
  CircleAlert,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  Package,
  Pencil,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  ReceiptText,
  Search,
  ShoppingBag,
  Store as StoreIcon,
  X,
} from 'lucide-react'
import { LoginScreen } from './components/LoginScreen'
import { MovementDialog } from './components/MovementDialog'
import { SaleDialog } from './components/SaleDialog'
import { StoreDialog } from './components/StoreDialog'
import {
  ApiError,
  api,
  clearSession,
  hasSession,
  type CurrentUser,
  type InventoryBalance,
  type Product,
  type Sale,
  type SaleInput,
  type StockAlert,
  type StockMovement,
  type StockMovementInput,
  type Store,
  type StoreInput,
  type StoreProduct,
} from './lib/api'
import './App.css'

interface DashboardData {
  stores: Store[]
  products: Product[]
  configurations: StoreProduct[]
  balances: InventoryBalance[]
  movements: StockMovement[]
  alerts: StockAlert[]
  sales: Sale[]
}

const emptyDashboard: DashboardData = {
  stores: [], products: [], configurations: [], balances: [], movements: [], alerts: [], sales: [],
}
const numberFormatter = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 3 })
const moneyFormatter = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', maximumFractionDigits: 0 })
const dateFormatter = new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
const longDateFormatter = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric', month: 'long', year: 'numeric' })
const movementLabels = { entry: 'Entrée', adjustment_in: 'Ajustement +', adjustment_out: 'Ajustement −', sale: 'Vente' }

async function fetchDashboard(): Promise<DashboardData> {
  const [storesResponse, productsResponse, alertsResponse, salesResponse] = await Promise.all([api.stores(), api.products(), api.alerts(), api.sales()])
  const slices = await Promise.all(storesResponse.items.map(async (store) => {
    const [configurations, balances, movements] = await Promise.all([api.storeProducts(store.id), api.balances(store.id), api.movements(store.id)])
    return { configurations: configurations.items, balances: balances.items, movements: movements.items }
  }))
  return {
    stores: storesResponse.items,
    products: productsResponse.items,
    alerts: alertsResponse.items,
    sales: salesResponse.items,
    configurations: slices.flatMap((slice) => slice.configurations),
    balances: slices.flatMap((slice) => slice.balances),
    movements: slices.flatMap((slice) => slice.movements).sort((left, right) => right.created_at.localeCompare(left.created_at)),
  }
}

function initials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function formatQuantity(value: string | number): string {
  return numberFormatter.format(Number(value))
}

function EmptyState({ children }: { children: string }) {
  return <div className="empty-state"><Boxes size={24} /><p>{children}</p></div>
}

function App() {
  const [authState, setAuthState] = useState<'checking' | 'signed-out' | 'signed-in'>(() =>
    hasSession() ? 'checking' : 'signed-out',
  )
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [dashboard, setDashboard] = useState<DashboardData>(emptyDashboard)
  const [selectedStoreId, setSelectedStoreId] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [movementOpen, setMovementOpen] = useState(false)
  const [saleOpen, setSaleOpen] = useState(false)
  const [storeEditor, setStoreEditor] = useState<Store | null | undefined>(undefined)
  const [statusStoreId, setStatusStoreId] = useState<string | null>(null)
  const deferredSearch = useDeferredValue(search.trim().toLocaleLowerCase('fr'))

  async function loadDashboard() {
    setLoading(true)
    setLoadError(null)
    try {
      setDashboard(await fetchDashboard())
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 401) {
        clearSession()
        setUser(null)
        setAuthState('signed-out')
        return
      }
      setLoadError(caughtError instanceof Error ? caughtError.message : 'Chargement impossible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    if (!hasSession()) return () => { active = false }
    async function restoreSession() {
      try {
        const currentUser = await api.me()
        if (!active) return
        setUser(currentUser)
        setAuthState('signed-in')
        try {
          const data = await fetchDashboard()
          if (active) setDashboard(data)
        } catch (caughtError) {
          if (active) setLoadError(caughtError instanceof Error ? caughtError.message : 'Chargement impossible')
        }
      } catch {
        if (!active) return
        clearSession()
        setAuthState('signed-out')
      }
    }
    void restoreSession()
    return () => { active = false }
  }, [])

  async function handleLogin(credentials: Parameters<typeof api.login>[0]) {
    await api.login(credentials)
    const [currentUser, data] = await Promise.all([api.me(), fetchDashboard()])
    setUser(currentUser)
    setDashboard(data)
    setAuthState('signed-in')
  }

  async function handleLogout() {
    try { await api.logout() } finally {
      setUser(null)
      setDashboard(emptyDashboard)
      setAuthState('signed-out')
    }
  }

  async function handleMovement(storeId: string, input: StockMovementInput) {
    await api.createMovement(storeId, input)
    setDashboard(await fetchDashboard())
    setMovementOpen(false)
    setNotice('Le mouvement de stock a été enregistré.')
    window.setTimeout(() => setNotice(null), 4500)
  }

  async function handleSale(input: SaleInput) {
    await api.createSale(input)
    setDashboard(await fetchDashboard())
    setSaleOpen(false)
    setNotice('La vente a été validée et le stock a été mis à jour.')
    window.setTimeout(() => setNotice(null), 4500)
  }

  async function handleStore(input: StoreInput) {
    if (storeEditor) await api.updateStore(storeEditor.id, input)
    else await api.createStore(input)
    setDashboard(await fetchDashboard())
    setStoreEditor(undefined)
    setNotice(storeEditor ? 'La boutique a été mise à jour.' : 'La boutique a été créée.')
    window.setTimeout(() => setNotice(null), 4500)
  }

  async function handleStoreStatus(store: Store) {
    if (store.is_active && !window.confirm(`Suspendre ${store.name} ?`)) return
    setStatusStoreId(store.id)
    setLoadError(null)
    try {
      await api.setStoreActive(store.id, !store.is_active)
      setDashboard(await fetchDashboard())
      if (store.id === selectedStoreId && store.is_active) setSelectedStoreId('all')
      setNotice(store.is_active ? 'La boutique a été suspendue.' : 'La boutique a été réactivée.')
      window.setTimeout(() => setNotice(null), 4500)
    } catch (caughtError) {
      setLoadError(caughtError instanceof Error ? caughtError.message : 'Changement de statut impossible')
    } finally {
      setStatusStoreId(null)
    }
  }

  if (authState === 'checking') {
    return <main className="boot-screen" aria-label="Chargement de KërManager"><span className="brand-symbol"><ShoppingBag size={22} /></span><LoaderCircle className="spin" size={22} /></main>
  }
  if (authState === 'signed-out' || user === null) return <LoginScreen onLogin={handleLogin} />

  const storeById = new Map(dashboard.stores.map((store) => [store.id, store]))
  const productById = new Map(dashboard.products.map((product) => [product.id, product]))
  const configurationByKey = new Map(dashboard.configurations.map((configuration) => [`${configuration.store_id}:${configuration.product_id}`, configuration]))
  const scopedStoreIds = new Set(dashboard.stores.filter((store) => selectedStoreId === 'all' || store.id === selectedStoreId).map((store) => store.id))
  const scopedConfigurations = dashboard.configurations.filter((configuration) => scopedStoreIds.has(configuration.store_id))
  const scopedBalances = dashboard.balances.filter((balance) => scopedStoreIds.has(balance.store_id))
  const scopedAlerts = dashboard.alerts.filter((alert) => scopedStoreIds.has(alert.store_id))
  const scopedMovements = dashboard.movements.filter((movement) => scopedStoreIds.has(movement.store_id))
  const scopedSales = dashboard.sales.filter((sale) => scopedStoreIds.has(sale.store_id))
  const matchesSearch = (...parts: (string | undefined)[]) => !deferredSearch || parts.join(' ').toLocaleLowerCase('fr').includes(deferredSearch)
  const filteredStores = dashboard.stores.filter((store) => scopedStoreIds.has(store.id) && matchesSearch(store.name, store.code))
  const filteredBalances = scopedBalances.filter((balance) => matchesSearch(productById.get(balance.product_id)?.name, productById.get(balance.product_id)?.sku, storeById.get(balance.store_id)?.name))
  const filteredAlerts = scopedAlerts.filter((alert) => matchesSearch(productById.get(alert.product_id)?.name, productById.get(alert.product_id)?.sku, storeById.get(alert.store_id)?.name))
  const filteredMovements = scopedMovements.filter((movement) => matchesSearch(productById.get(movement.product_id)?.name, productById.get(movement.product_id)?.sku, storeById.get(movement.store_id)?.name, movement.reason))
  const filteredSales = scopedSales.filter((sale) => matchesSearch(sale.id, storeById.get(sale.store_id)?.name, ...sale.lines.map((line) => productById.get(line.product_id)?.name)))
  const trackedProductCount = new Set(scopedConfigurations.filter((configuration) => configuration.is_active).map((item) => item.product_id)).size
  const totalStock = scopedBalances.reduce((sum, balance) => sum + Number(balance.quantity), 0)
  const outOfStockCount = scopedAlerts.filter((alert) => alert.alert_type === 'out_of_stock').length
  const activeStoreCount = dashboard.stores.filter((store) => scopedStoreIds.has(store.id) && store.is_active).length
  const hasActiveStores = dashboard.stores.some((store) => store.is_active)
  const totalRevenue = scopedSales.reduce((sum, sale) => sum + Number(sale.total_amount), 0)
  const selectedStore = dashboard.stores.find((store) => store.id === selectedStoreId)
  const actionDefaultStore = selectedStore?.is_active
    ? selectedStore.id
    : dashboard.stores.find((store) => store.is_active)?.id ?? ''

  return (
    <div className="app-shell">
      {menuOpen && <button className="sidebar-scrim" onClick={() => setMenuOpen(false)} aria-label="Fermer le menu" />}
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand-mark">
          <span className="brand-symbol"><ShoppingBag size={20} /></span><span>Kër<span>Manager</span></span>
          <button className="mobile-close" type="button" onClick={() => setMenuOpen(false)} aria-label="Fermer le menu"><X size={20} /></button>
        </div>
        <nav aria-label="Navigation principale" onClick={() => setMenuOpen(false)}>
          <p className="nav-caption">ESPACE DE TRAVAIL</p>
          <a className="nav-link active" href="#dashboard"><LayoutDashboard size={19} />Vue d’ensemble</a>
          <a className="nav-link" href="#shops"><StoreIcon size={19} />Boutiques<span className="nav-count">{dashboard.stores.length}</span></a>
          <a className="nav-link" href="#stock"><Package size={19} />Produits & stock</a>
          <a className="nav-link" href="#sales"><ReceiptText size={19} />Ventes<span className="nav-count">{dashboard.sales.length}</span></a>
          <a className="nav-link" href="#movements"><Boxes size={19} />Mouvements</a>
          <a className="nav-link" href="#alerts"><CircleAlert size={19} />Alertes<span className="nav-count alert">{dashboard.alerts.length}</span></a>
        </nav>
        <div className="sidebar-profile">
          <div className="avatar">{initials(user.full_name)}</div>
          <div><strong>{user.full_name}</strong><span>{user.role === 'manager' ? 'Gestionnaire' : 'Propriétaire'}</span></div>
          <button className="profile-action" type="button" onClick={() => void handleLogout()} aria-label="Se déconnecter" title="Se déconnecter"><LogOut size={17} /></button>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <button className="icon-button menu-button" type="button" onClick={() => setMenuOpen(true)} aria-label="Ouvrir le menu"><Menu size={21} /></button>
          <label className="search-box"><Search size={18} /><span className="sr-only">Rechercher</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher une boutique, un produit…" /></label>
          <div className="topbar-actions">
            <label className="store-filter"><span className="sr-only">Filtrer par boutique</span><StoreIcon size={15} /><select value={selectedStoreId} onChange={(event) => setSelectedStoreId(event.target.value)}><option value="all">Toutes les boutiques</option>{dashboard.stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}</select></label>
            <span className="period-label">{longDateFormatter.format(new Date())}</span>
            <button className="icon-button notification-button" type="button" aria-label="Voir les alertes" title="Voir les alertes" onClick={() => document.querySelector('#alerts')?.scrollIntoView()}><Bell size={20} />{scopedAlerts.length > 0 && <span className="notification-dot" />}</button>
          </div>
        </header>

        <div className="content-wrap">
          {notice && <div className="notice" role="status">{notice}</div>}
          {loadError && <div className="load-error" role="alert"><span>{loadError}</span><button type="button" onClick={() => void loadDashboard()}><RefreshCw size={15} />Réessayer</button></div>}
          <section className="page-heading">
            <div><p className="eyebrow">SITUATION OPÉRATIONNELLE</p><h1>Bonjour {user.full_name.split(' ')[0]},</h1><p>Les niveaux de stock de vos boutiques sont à jour.</p></div>
            <div className="heading-actions">
              <button className="icon-button" type="button" onClick={() => void loadDashboard()} aria-label="Actualiser" title="Actualiser" disabled={loading}><RefreshCw className={loading ? 'spin' : ''} size={18} /></button>
              {user.role === 'manager' && <button className="secondary-button action-button" type="button" onClick={() => setMovementOpen(true)} disabled={!hasActiveStores}><Boxes size={17} />Mouvement</button>}
              {user.role === 'manager' && <button className="primary-button" type="button" onClick={() => setSaleOpen(true)} disabled={!hasActiveStores}><Plus size={18} />Nouvelle vente</button>}
            </div>
          </section>

          <section className="metrics-grid" aria-label="Indicateurs principaux">
            <article className="metric-card accent-card"><div className="metric-icon"><Package size={21} /></div><p>Produits suivis</p><strong>{trackedProductCount}</strong><span className="neutral">{scopedConfigurations.length} configuration{scopedConfigurations.length > 1 ? 's' : ''} boutique</span></article>
            <article className="metric-card"><div className="metric-icon blue"><Boxes size={21} /></div><p>Unités en stock</p><strong>{formatQuantity(totalStock)}</strong><span className="neutral">Solde consolidé disponible</span></article>
            <article className="metric-card"><div className="metric-icon amber"><CircleAlert size={21} /></div><p>Alertes de stock</p><strong>{scopedAlerts.length}</strong><span className="warning">{outOfStockCount} rupture{outOfStockCount > 1 ? 's' : ''} · {scopedAlerts.length - outOfStockCount} faible{scopedAlerts.length - outOfStockCount > 1 ? 's' : ''}</span></article>
            <article className="metric-card"><div className="metric-icon graphite"><Banknote size={21} /></div><p>Chiffre d’affaires</p><strong>{moneyFormatter.format(totalRevenue)}</strong><span className="neutral">{scopedSales.length} vente{scopedSales.length > 1 ? 's' : ''} · {activeStoreCount} boutique{activeStoreCount > 1 ? 's' : ''}</span></article>
          </section>

          <section className="dashboard-grid">
            <article className="panel shops-panel" id="shops">
              <div className="panel-heading"><div><h2>État des boutiques</h2><p>Couverture du catalogue et santé du stock</p></div><div className="panel-heading-actions"><span className="panel-count">{filteredStores.length}</span>{user.role === 'manager' && <button className="panel-command" type="button" onClick={() => setStoreEditor(null)}><Plus size={15} />Ajouter</button>}</div></div>
              {filteredStores.length === 0 ? <EmptyState>Aucune boutique ne correspond à cette vue.</EmptyState> : <div className="shop-list">{filteredStores.map((store, index) => {
                const configurations = dashboard.configurations.filter((item) => item.store_id === store.id && item.is_active)
                const balances = dashboard.balances.filter((item) => item.store_id === store.id)
                const alerts = dashboard.alerts.filter((item) => item.store_id === store.id)
                const healthy = balances.filter((balance) => Number(balance.quantity) > Number(configurationByKey.get(`${store.id}:${balance.product_id}`)?.low_stock_threshold ?? 0)).length
                const health = configurations.length === 0 ? 0 : Math.round((healthy / configurations.length) * 100)
                return <div className={`shop-row ${store.is_active ? '' : 'suspended'}`} key={store.id}><span className={`shop-rank tone-${index % 3}`}>{String(index + 1).padStart(2, '0')}</span><div className="shop-info"><strong>{store.name}</strong><span>{store.code} · {configurations.length} produit{configurations.length > 1 ? 's' : ''}</span></div><div className="health-cell"><div className="bar-track"><span className={health < 50 ? 'danger' : health < 80 ? 'amber' : ''} style={{ width: `${health}%` }} /></div><span>{health}% sain</span></div><div className="shop-stock"><strong>{formatQuantity(balances.reduce((sum, item) => sum + Number(item.quantity), 0))}</strong><span>unités</span></div><span className={`alert-chip ${store.is_active && alerts.length === 0 ? 'clear' : ''}`}>{store.is_active ? alerts.length === 0 ? 'Sain' : `${alerts.length} alerte${alerts.length > 1 ? 's' : ''}` : 'Suspendue'}</span>{user.role === 'manager' && <div className="shop-actions"><button type="button" onClick={() => setStoreEditor(store)} aria-label={`Modifier ${store.name}`} title="Modifier"><Pencil size={15} /></button><button type="button" className={store.is_active ? 'danger' : 'activate'} onClick={() => void handleStoreStatus(store)} disabled={statusStoreId === store.id} aria-label={`${store.is_active ? 'Suspendre' : 'Réactiver'} ${store.name}`} title={store.is_active ? 'Suspendre' : 'Réactiver'}>{store.is_active ? <PowerOff size={15} /> : <Power size={15} />}</button></div>}</div>
              })}</div>}
            </article>

            <article className="panel alerts-panel" id="alerts">
              <div className="panel-heading"><div><h2>Alertes ouvertes</h2><p>Produits à surveiller maintenant</p></div><span className="panel-count danger">{filteredAlerts.length}</span></div>
              {filteredAlerts.length === 0 ? <EmptyState>Aucune alerte ouverte dans cette vue.</EmptyState> : <div className="alert-list">{filteredAlerts.slice(0, 5).map((alert) => <div className={`alert-row ${alert.alert_type === 'out_of_stock' ? 'critical' : 'low'}`} key={alert.id}><span className="product-icon"><Package size={18} /></span><div><strong>{productById.get(alert.product_id)?.name ?? 'Produit inconnu'}</strong><span>{storeById.get(alert.store_id)?.name ?? 'Boutique inconnue'}</span></div><b>{alert.alert_type === 'out_of_stock' ? 'Rupture' : `${formatQuantity(alert.observed_quantity)} restant`}</b></div>)}</div>}
            </article>

            <article className="panel stock-panel" id="stock">
              <div className="panel-heading"><div><h2>Inventaire actuel</h2><p>Soldes et seuils par boutique</p></div><span className="panel-count">{filteredBalances.length}</span></div>
              {filteredBalances.length === 0 ? <EmptyState>Aucun solde de stock ne correspond à cette vue.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Produit</th><th>Boutique</th><th>Stock</th><th>Seuil</th><th>État</th></tr></thead><tbody>{filteredBalances.map((balance) => {
                const product = productById.get(balance.product_id)
                const quantity = Number(balance.quantity)
                const threshold = Number(configurationByKey.get(`${balance.store_id}:${balance.product_id}`)?.low_stock_threshold ?? 0)
                const state = quantity === 0 ? 'Rupture' : quantity <= threshold ? 'Faible' : 'Disponible'
                return <tr key={`${balance.store_id}:${balance.product_id}`}><td><strong>{product?.name ?? 'Produit inconnu'}</strong><small>{product?.sku}</small></td><td>{storeById.get(balance.store_id)?.name}</td><td><strong>{formatQuantity(balance.quantity)}</strong></td><td>{formatQuantity(threshold)}</td><td><span className={`stock-status ${state.toLowerCase()}`}>{state}</span></td></tr>
              })}</tbody></table></div>}
            </article>

            <article className="panel sales-panel" id="sales">
              <div className="panel-heading"><div><h2>Ventes récentes</h2><p>Transactions validées et chiffre d’affaires</p></div><span className="panel-count">{filteredSales.length}</span></div>
              {filteredSales.length === 0 ? <EmptyState>Aucune vente ne correspond à cette vue.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Référence</th><th>Boutique</th><th>Date</th><th>Articles</th><th>Total</th></tr></thead><tbody>{filteredSales.slice(0, 12).map((sale) => <tr key={sale.id}><td><strong>#{sale.id.slice(0, 8).toUpperCase()}</strong><small>{sale.lines.length} produit{sale.lines.length > 1 ? 's' : ''}</small></td><td>{storeById.get(sale.store_id)?.name}</td><td>{dateFormatter.format(new Date(sale.created_at))}</td><td>{formatQuantity(sale.lines.reduce((sum, line) => sum + Number(line.quantity), 0))}</td><td><strong>{moneyFormatter.format(Number(sale.total_amount))}</strong></td></tr>)}</tbody></table></div>}
            </article>

            <article className="panel movements-panel" id="movements">
              <div className="panel-heading"><div><h2>Mouvements récents</h2><p>Historique immuable des variations</p></div><span className="panel-count">{filteredMovements.length}</span></div>
              {filteredMovements.length === 0 ? <EmptyState>Aucun mouvement ne correspond à cette vue.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Type</th><th>Produit</th><th>Boutique</th><th>Date</th><th>Quantité</th><th>Nouveau stock</th><th></th></tr></thead><tbody>{filteredMovements.slice(0, 12).map((movement) => {
                const isOutput = movement.movement_type === 'adjustment_out' || movement.movement_type === 'sale'
                return <tr key={movement.id}><td><span className={`movement-type ${isOutput ? 'out' : 'in'}`}>{movementLabels[movement.movement_type]}</span></td><td><strong>{productById.get(movement.product_id)?.name ?? 'Produit inconnu'}</strong><small>{productById.get(movement.product_id)?.sku}</small></td><td>{storeById.get(movement.store_id)?.name}</td><td>{dateFormatter.format(new Date(movement.created_at))}</td><td><strong>{isOutput ? '−' : '+'}{formatQuantity(movement.quantity)}</strong></td><td>{formatQuantity(movement.new_quantity)}</td><td><button className="row-action" type="button" title={movement.reason} aria-label={`Motif : ${movement.reason}`}><ChevronRight size={16} /></button></td></tr>
              })}</tbody></table></div>}
            </article>
          </section>
        </div>
      </main>

      {movementOpen && <MovementDialog stores={dashboard.stores} products={dashboard.products} configurations={dashboard.configurations} defaultStoreId={actionDefaultStore} onClose={() => setMovementOpen(false)} onSubmit={handleMovement} />}
      {saleOpen && <SaleDialog stores={dashboard.stores} products={dashboard.products} configurations={dashboard.configurations} balances={dashboard.balances} defaultStoreId={actionDefaultStore} onClose={() => setSaleOpen(false)} onSubmit={handleSale} />}
      {storeEditor !== undefined && <StoreDialog store={storeEditor} onClose={() => setStoreEditor(undefined)} onSubmit={handleStore} />}
    </div>
  )
}

export default App
