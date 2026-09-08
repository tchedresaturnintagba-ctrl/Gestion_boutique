const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const API_PREFIX = '/api/v1'
const ACCESS_TOKEN_KEY = 'ker-manager-access-token'
const REFRESH_TOKEN_KEY = 'ker-manager-refresh-token'

export type UserRole = 'manager' | 'owner'
export type ProductUnit = 'piece' | 'pack' | 'kilogram' | 'liter'
export type StockMovementType = 'entry' | 'adjustment_in' | 'adjustment_out' | 'sale'
export type ManualStockMovementType = Exclude<StockMovementType, 'sale'>
export type StockAlertType = 'out_of_stock' | 'low_stock'

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface CurrentUser {
  id: string
  organization_id: string
  email: string
  full_name: string
  role: UserRole
}

export interface Store {
  id: string
  organization_id: string
  name: string
  code: string
  address: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Product {
  id: string
  organization_id: string
  category_id: string | null
  name: string
  sku: string
  description: string | null
  unit: ProductUnit
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StoreProduct {
  organization_id: string
  store_id: string
  product_id: string
  unit_price: number
  low_stock_threshold: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface InventoryBalance {
  organization_id: string
  store_id: string
  product_id: string
  quantity: string
  updated_at: string
}

export interface StockMovement {
  id: string
  organization_id: string
  store_id: string
  product_id: string
  actor_user_id: string | null
  sale_id: string | null
  movement_type: StockMovementType
  quantity: string
  previous_quantity: string
  new_quantity: string
  reason: string
  created_at: string
}

export interface StockAlert {
  id: string
  organization_id: string
  store_id: string
  product_id: string
  alert_type: StockAlertType
  observed_quantity: string
  threshold: string
  created_at: string
  resolved_at: string | null
}

export interface SaleLine {
  id: string
  product_id: string
  quantity: string
  unit_price: number
  line_total: string
}

export interface Sale {
  id: string
  organization_id: string
  store_id: string
  actor_user_id: string | null
  total_amount: string
  created_at: string
  lines: SaleLine[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface StockMovementResult {
  movement: StockMovement
  balance: InventoryBalance
  alert: StockAlert | null
}

export interface LoginCredentials {
  organization_slug: string
  email: string
  password: string
}

export interface StockMovementInput {
  product_id: string
  movement_type: ManualStockMovementType
  quantity: string
  reason: string
}

export interface SaleInput {
  store_id: string
  lines: Array<{ product_id: string; quantity: string }>
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
}

export function clearSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function hasSession(): boolean {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY) !== null
}

function errorMessage(body: unknown, fallback: string): string {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return fallback
  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) return String(item.msg)
        return String(item)
      })
      .join(' · ')
  }
  if (typeof detail === 'object' && detail !== null && 'message' in detail) {
    return String(detail.message)
  }
  return fallback
}

let refreshPromise: Promise<boolean> | null = null

async function refreshSession(): Promise<boolean> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_URL}${API_PREFIX}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) return false
    saveTokens((await response.json()) as TokenPair)
    return true
  } catch {
    return false
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  const accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  let response: Response
  try {
    response = await fetch(`${API_URL}${API_PREFIX}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('Impossible de joindre le serveur. Vérifiez que l’API est démarrée.', 0)
  }

  if (response.status === 401 && retry && path !== '/auth/refresh') {
    refreshPromise ??= refreshSession().finally(() => {
      refreshPromise = null
    })
    if (await refreshPromise) return request<T>(path, init, false)
    clearSession()
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(errorMessage(body, `Erreur HTTP ${response.status}`), response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function allPages<T>(path: string): Promise<Page<T>> {
  const separator = path.includes('?') ? '&' : '?'
  const firstPage = await request<Page<T>>(`${path}${separator}page=1&page_size=100`)
  const items = [...firstPage.items]
  let page = 2
  while (items.length < firstPage.total) {
    const nextPage = await request<Page<T>>(`${path}${separator}page=${page}&page_size=100`)
    items.push(...nextPage.items)
    if (nextPage.items.length === 0) break
    page += 1
  }
  return { ...firstPage, items }
}

export const api = {
  async login(credentials: LoginCredentials): Promise<void> {
    clearSession()
    const response = await fetch(`${API_URL}${API_PREFIX}/auth/login`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    }).catch(() => {
      throw new ApiError('Impossible de joindre le serveur. Vérifiez que l’API est démarrée.', 0)
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new ApiError(errorMessage(body, 'Connexion refusée'), response.status)
    }
    saveTokens((await response.json()) as TokenPair)
  },

  me: () => request<CurrentUser>('/auth/me'),
  stores: () => allPages<Store>('/stores'),
  products: () => allPages<Product>('/catalog/products'),
  storeProducts: (storeId: string) =>
    allPages<StoreProduct>(`/catalog/stores/${storeId}/products`),
  balances: (storeId: string) =>
    allPages<InventoryBalance>(`/inventory/stores/${storeId}/balances`),
  movements: (storeId: string) =>
    request<Page<StockMovement>>(`/inventory/stores/${storeId}/movements?page=1&page_size=100`),
  alerts: () => allPages<StockAlert>('/inventory/alerts?open_only=true'),
  sales: () => allPages<Sale>('/sales'),
  createMovement: (storeId: string, input: StockMovementInput) =>
    request<StockMovementResult>(`/inventory/stores/${storeId}/movements`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  createSale: (input: SaleInput) =>
    request<Sale>('/sales', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  async logout(): Promise<void> {
    try {
      await request<void>('/auth/logout-all', { method: 'POST' })
    } finally {
      clearSession()
    }
  },
}