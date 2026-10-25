import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight, ArrowUpRight, CarFront, Check, ChevronDown, Filter, KeyRound,
  LogOut, Menu, Plus, Search, ShieldCheck, SlidersHorizontal, Sparkles,
  Trash2, X,
} from 'lucide-react'
import { api, API_BASE, ApiError, searchPath, TOKEN_KEY } from './api'
import CarArt from './CarArt'

const emptyFilters = { make: '', model: '', category: '', min_price: '', max_price: '' }
const emptyVehicle = { make: '', model: '', category: '', price: '', quantity: '' }
const categories = ['All', 'Sedan', 'SUV', 'Truck', 'Coupe']
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)

function Mark({ light = false }) {
  return <span className={`brand-mark ${light ? 'brand-mark-light' : ''}`} aria-hidden="true"><span>A</span></span>
}

function AuthPanel({ onSuccess }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'register') await api('/api/auth/register', { method: 'POST', body: { email, password } })
      const result = await api('/api/auth/login', { method: 'POST', body: { email, password } })
      onSuccess(result.access_token)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      <header className="auth-header"><div className="site-width flex items-center justify-between"><div className="flex items-center gap-3"><Mark /><span className="brand-name">ATELIER<span className="brand-dot">.</span> MOTORS</span></div><span className="hidden sm:block text-xs tracking-[.22em] uppercase text-forest/60">The road begins here</span></div></header>
      <main className="site-width flex-1 grid lg:grid-cols-[1.05fr_.95fr] gap-10 lg:gap-20 items-center py-14 lg:py-20">
        <section className="max-w-xl">
          <span className="eyebrow"><span className="eyebrow-line" /> Curated for the drive</span>
          <h1 className="font-display text-[clamp(3.2rem,6.8vw,6.5rem)] leading-[1.02] tracking-[-.075em] font-semibold text-ink mt-7">Find the car.<br/><em className="font-normal serif-accent text-accent">Feel the freedom.</em></h1>
          <p className="text-forest/65 text-lg leading-relaxed mt-7 max-w-lg">A considered collection of vehicles, ready for wherever the road takes you next.</p>
          <div className="mt-12 flex items-center gap-5 text-sm text-forest/70"><span className="icon-badge"><ShieldCheck size={21}/></span><span>Simple browsing. Clear inventory. Your next chapter.</span></div>
        </section>
        <section className="auth-card" aria-label="Account access">
          <div className="auth-art"><CarArt hero /><div className="absolute left-7 top-7 text-white/80 text-[11px] uppercase tracking-[.22em] font-semibold">THE ATELIER EDITION</div><div className="absolute bottom-6 left-7 text-white text-xl font-display font-semibold">Drive something extraordinary.</div></div>
          <div className="p-7 sm:p-9">
            <div className="flex gap-7 border-b border-ink/10 mb-7" role="tablist" aria-label="Account mode">
              <button role="tab" aria-selected={mode === 'login'} className={`auth-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => { setMode('login'); setError('') }}>Sign in</button>
              <button role="tab" aria-selected={mode === 'register'} className={`auth-tab ${mode === 'register' ? 'active' : ''}`} onClick={() => { setMode('register'); setError('') }}>Create account</button>
            </div>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">{mode === 'login' ? 'Welcome back' : 'Start your journey'}</h2>
            <p className="text-sm text-forest/60 mt-2 mb-7">{mode === 'login' ? 'Sign in to explore the collection.' : 'Create an account to explore and purchase.'}</p>
            <form onSubmit={submit} className="space-y-4">
              <label className="field-label">Email address<input required type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} className="field-input" placeholder="you@example.com" /></label>
              <label className="field-label">Password<input required minLength={mode === 'register' ? 8 : 1} type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} className="field-input" placeholder={mode === 'register' ? 'At least 8 characters' : 'Enter your password'} /></label>
              {error && <p role="alert" className="form-error">{error}</p>}
              <button disabled={busy} type="submit" className="btn-primary w-full justify-center mt-2">{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight size={18}/></button>
            </form>
          </div>
        </section>
      </main>
      <footer className="site-width w-full pb-7 text-xs text-forest/45 flex justify-between"><span>© {new Date().getFullYear()} Atelier Motors</span><span>Built for the journey ahead.</span></footer>
    </div>
  )
}

function VehicleCard({ vehicle, admin, busy, onPurchase, onEdit, onRestock, onDelete }) {
  const available = vehicle.quantity > 0
  return (
    <article className="vehicle-card" data-testid={`vehicle-${vehicle.id}`}>
      <div className="vehicle-art"><CarArt vehicle={vehicle} /><span className={`stock-pill ${available ? '' : 'sold'}`}>{available ? <><span className="status-dot" /> Available now</> : 'Out of stock'}</span></div>
      <div className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3"><div><p className="overline">{vehicle.category}</p><h3 className="font-display text-[1.35rem] font-semibold tracking-tight text-ink mt-1">{vehicle.make} {vehicle.model}</h3></div><ArrowUpRight className="text-forest/40 mt-1" size={19}/></div>
        <div className="border-t border-ink/10 mt-5 pt-4 flex items-end justify-between"><div><p className="text-[11px] uppercase tracking-[.15em] text-forest/50 font-bold">Asking price</p><p className="font-display text-[1.4rem] font-semibold text-ink mt-1">{money(vehicle.price)}</p></div><p className="text-xs text-forest/60 pb-1">{vehicle.quantity} available</p></div>
        <button className="card-action mt-5" disabled={!available || busy} onClick={() => onPurchase(vehicle)}>{busy ? 'Processing…' : available ? 'Purchase vehicle' : 'Sold out'}{available && !busy && <ArrowRight size={17}/>}</button>
        {admin && <div className="admin-actions"><button onClick={() => onEdit(vehicle)} aria-label={`Edit ${vehicle.make} ${vehicle.model}`}>Edit</button><button onClick={() => onRestock(vehicle)}>Restock</button><button onClick={() => onDelete(vehicle)} aria-label={`Delete ${vehicle.make} ${vehicle.model}`} className="danger">Delete</button></div>}
      </div>
    </article>
  )
}

function VehicleModal({ vehicle, mode, onClose, onSave }) {
  const [form, setForm] = useState(vehicle ? { ...vehicle } : { ...emptyVehicle })
  const [amount, setAmount] = useState('1')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const restock = mode === 'restock'

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = restock ? { amount: Number(amount) } : {
        make: form.make.trim(), model: form.model.trim(), category: form.category.trim(),
        price: Number(form.price), quantity: Number(form.quantity),
      }
      await onSave(payload)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
    <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="flex items-start justify-between gap-4 mb-7"><div><p className="overline">Inventory management</p><h2 id="modal-title" className="font-display text-2xl font-semibold mt-2">{restock ? `Restock ${vehicle.make} ${vehicle.model}` : vehicle ? 'Edit vehicle' : 'Add a vehicle'}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={19}/></button></div>
      <form onSubmit={submit} className="space-y-4">
        {restock ? <label className="field-label">Units to add<input className="field-input" type="number" min="1" step="1" required value={amount} onChange={e => setAmount(e.target.value)} /></label> : <>
          <div className="grid sm:grid-cols-2 gap-4">{['make', 'model'].map(key => <label className="field-label capitalize" key={key}>{key}<input className="field-input" required maxLength="100" value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} placeholder={key === 'make' ? 'e.g. Toyota' : 'e.g. Camry'} /></label>)}</div>
          <label className="field-label">Category<input className="field-input" required maxLength="100" list="categories" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="e.g. Sedan" /><datalist id="categories">{categories.slice(1).map(c => <option key={c} value={c}/>)}</datalist></label>
          <div className="grid sm:grid-cols-2 gap-4"><label className="field-label">Price ($)<input className="field-input" type="number" min="0.01" step="0.01" required value={form.price} onChange={e => setForm({ ...form, price: e.target.value })}/></label><label className="field-label">Quantity<input className="field-input" type="number" min="0" step="1" required value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })}/></label></div>
        </>}
        {error && <p role="alert" className="form-error">{error}</p>}
        <div className="flex gap-3 pt-4"><button type="button" className="btn-outline flex-1 justify-center" onClick={onClose}>Cancel</button><button disabled={busy} className="btn-primary flex-1 justify-center" type="submit">{busy ? 'Saving…' : restock ? 'Add stock' : vehicle ? 'Save changes' : 'Add vehicle'} <Check size={17}/></button></div>
      </form>
    </div>
  </div>
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(Boolean(token))
  const [filters, setFilters] = useState({ ...emptyFilters })
  const [activeFilters, setActiveFilters] = useState({ ...emptyFilters })
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [modal, setModal] = useState(null)
  const [mobileMenu, setMobileMenu] = useState(false)

  const signOut = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
    setVehicles([])
    setModal(null)
  }, [])

  const loadVehicles = useCallback(async (accessToken, selected = activeFilters) => {
    try {
      const list = await api(searchPath(selected), { token: accessToken })
      setVehicles(list)
      setError('')
    } catch (err) {
      if (err.status === 401) signOut()
      else setError(err.message)
    }
  }, [activeFilters, signOut])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    async function start() {
      setLoading(true)
      try {
        const account = await api('/api/auth/me', { token })
        if (cancelled) return
        setUser(account)
        const list = await api('/api/vehicles', { token })
        if (!cancelled) { setVehicles(list); setError('') }
      } catch (err) {
        if (cancelled) return
        if (err.status === 401) signOut()
        else setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    start()
    return () => { cancelled = true }
  }, [token, signOut])

  function authenticated(accessToken) {
    sessionStorage.setItem(TOKEN_KEY, accessToken)
    setToken(accessToken)
    setNotice('Welcome to the collection.')
  }

  async function search(e) {
    e.preventDefault()
    setActiveFilters({ ...filters })
    setLoading(true)
    await loadVehicles(token, filters)
    setLoading(false)
  }

  async function selectCategory(category) {
    const next = { ...filters, category: category === 'All' ? '' : category }
    setFilters(next)
    setActiveFilters(next)
    setLoading(true)
    await loadVehicles(token, next)
    setLoading(false)
  }

  async function resetFilters() {
    setFilters({ ...emptyFilters })
    setActiveFilters({ ...emptyFilters })
    setLoading(true)
    await loadVehicles(token, emptyFilters)
    setLoading(false)
  }

  async function purchase(vehicle) {
    setBusyId(vehicle.id)
    setNotice('')
    setError('')
    try {
      await api(`/api/vehicles/${vehicle.id}/purchase`, { method: 'POST', token })
      await loadVehicles(token)
      setNotice(`${vehicle.make} ${vehicle.model} purchased. Enjoy the drive!`)
    } catch (err) {
      if (err.status === 401) signOut()
      else { setError(err.message); if (err.status === 409) await loadVehicles(token) }
    } finally { setBusyId(null) }
  }

  async function saveVehicle(payload) {
    const { mode, vehicle } = modal
    const path = mode === 'add' ? '/api/vehicles' : mode === 'restock' ? `/api/vehicles/${vehicle.id}/restock` : `/api/vehicles/${vehicle.id}`
    const method = mode === 'edit' ? 'PUT' : 'POST'
    try {
      await api(path, { method, body: payload, token })
      setModal(null)
      await loadVehicles(token)
      setNotice(mode === 'add' ? 'Vehicle added to the collection.' : mode === 'restock' ? 'Stock updated.' : 'Vehicle updated.')
    } catch (err) {
      if (err.status === 401) signOut()
      throw err
    }
  }

  async function deleteVehicle(vehicle) {
    if (!window.confirm(`Delete ${vehicle.make} ${vehicle.model} from inventory?`)) return
    setError('')
    try {
      await api(`/api/vehicles/${vehicle.id}`, { method: 'DELETE', token })
      await loadVehicles(token)
      setNotice('Vehicle removed from inventory.')
    } catch (err) {
      if (err.status === 401) signOut()
      else setError(err.message)
    }
  }

  if (!token) return <AuthPanel onSuccess={authenticated} />
  const admin = user?.role === 'admin'
  const stockCount = vehicles.reduce((count, v) => count + v.quantity, 0)
  const hasFilters = Object.values(activeFilters).some(Boolean)

  return <div className="min-h-screen bg-cream text-ink">
    <header className="main-header"><div className="site-width flex items-center justify-between h-[76px]">
      <div className="flex items-center gap-3"><Mark/><span className="brand-name">ATELIER<span className="brand-dot">.</span> MOTORS</span></div>
      <nav className="hidden md:flex items-center gap-9 text-sm font-semibold"><a href="#collection" className="nav-link active">Collection</a><a href="#about" className="nav-link">Our approach</a></nav>
      <div className="hidden md:flex items-center gap-4"><span className="text-xs text-forest/60 max-w-[170px] truncate">{user?.email}</span>{admin && <span className="admin-badge"><ShieldCheck size={12}/> Admin</span>}<button onClick={signOut} className="logout-button" aria-label="Sign out"><LogOut size={18}/></button></div>
      <button className="md:hidden icon-button" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Toggle menu"><Menu size={22}/></button>
    </div>{mobileMenu && <div className="mobile-nav"><span>{user?.email}</span><button onClick={signOut}>Sign out <LogOut size={15}/></button></div>}</header>

    <main>
      <section className="hero-section"><div className="site-width hero-grid">
        <div className="hero-copy"><div className="hero-eyebrow"><span className="w-7 h-px bg-[#d7ad89]"/> YOUR NEXT DRIVE STARTS HERE</div><h1 className="font-display font-semibold tracking-[-.075em] text-[clamp(3rem,5.5vw,5.6rem)] leading-[1.05] mt-7">A better way<br/>to <span className="hero-italic">move.</span></h1><p className="text-white/65 text-[15px] leading-7 mt-6 max-w-md">Discover vehicles selected for the journeys that matter. Your perfect match is waiting in the collection.</p><a href="#collection" className="hero-cta">Explore the collection <ArrowRight size={18}/></a><div className="hero-caption"><span className="hero-caption-rule"/> CURATED COLLECTION · OPEN ROAD</div></div>
        <div className="hero-image"><CarArt hero /><div className="hero-image-label"><span>01 / THE COLLECTION</span><ArrowUpRight size={19}/></div></div>
      </div></section>

      <section className="site-width py-12 sm:py-16" id="collection">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6"><div><span className="eyebrow"><span className="eyebrow-line"/> THE COLLECTION</span><h2 className="section-title">Explore our vehicles<span className="text-accent">.</span></h2><p className="text-forest/60 text-sm sm:text-base mt-3">Considered choices for every kind of journey.</p></div><div className="flex items-center gap-3">{admin && <button className="btn-primary" onClick={() => setModal({ mode: 'add' })}><Plus size={18}/> Add vehicle</button>}<span className="collection-count"><CarFront size={17}/>{stockCount} in stock</span></div></div>

        {(notice || error) && <div className={`alert-bar ${error ? 'alert-error' : ''}`} role="status"><span>{error || notice}</span><button onClick={() => { setNotice(''); setError('') }} aria-label="Dismiss message"><X size={16}/></button></div>}

        <form onSubmit={search} className="filters-panel mt-9"><div className="flex items-center gap-2 text-ink font-display font-semibold mb-5"><SlidersHorizontal size={18} className="text-accent"/> Find your match <span className="ml-auto text-[11px] text-forest/40 font-sans font-medium hidden sm:block">FILTER YOUR COLLECTION</span></div><div className="grid sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_.85fr_.85fr_auto] gap-3 items-end">
          <label className="filter-label">Make filter<input className="filter-input" placeholder="Any make" value={filters.make} onChange={e => setFilters({ ...filters, make: e.target.value })}/></label>
          <label className="filter-label">Model<input className="filter-input" placeholder="Any model" value={filters.model} onChange={e => setFilters({ ...filters, model: e.target.value })}/></label>
          <label className="filter-label">Category<span className="select-wrap"><select className="filter-input appearance-none" value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })}><option value="">All types</option>{categories.slice(1).map(c => <option key={c} value={c}>{c}</option>)}</select><ChevronDown size={15}/></span></label>
          <label className="filter-label">Min price<input className="filter-input" type="number" min="0" placeholder="$ 0" value={filters.min_price} onChange={e => setFilters({ ...filters, min_price: e.target.value })}/></label>
          <label className="filter-label">Max price<input className="filter-input" type="number" min="0" placeholder="No limit" value={filters.max_price} onChange={e => setFilters({ ...filters, max_price: e.target.value })}/></label>
          <button className="filter-submit" type="submit" aria-label="Search vehicles"><Search size={19}/></button>
        </div></form>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-8 mb-6"><div className="category-tabs">{categories.map(c => <button key={c} onClick={() => selectCategory(c)} className={activeFilters.category === (c === 'All' ? '' : c) ? 'selected' : ''}>{c}</button>)}</div><div className="text-xs text-forest/55 flex gap-4 items-center"><span>{vehicles.length} {vehicles.length === 1 ? 'vehicle' : 'vehicles'} found</span>{hasFilters && <button onClick={resetFilters} className="underline underline-offset-4 hover:text-ink">Clear filters</button>}</div></div>

        {loading ? <div className="empty-state"><div className="loading-ring"/><p>Loading the collection…</p></div> : vehicles.length === 0 ? <div className="empty-state"><Filter size={28} className="text-accent"/><h3>No vehicles found</h3><p>Try adjusting your filters or clear them to see the full collection.</p><button className="btn-outline mt-5" onClick={resetFilters}>Clear filters</button></div> : <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">{vehicles.map(vehicle => <VehicleCard key={vehicle.id} vehicle={vehicle} admin={admin} busy={busyId === vehicle.id} onPurchase={purchase} onEdit={v => setModal({ mode: 'edit', vehicle: v })} onRestock={v => setModal({ mode: 'restock', vehicle: v })} onDelete={deleteVehicle}/>)}</div>}
      </section>

      <section id="about" className="about-strip"><div className="site-width grid md:grid-cols-[1fr_auto] gap-8 items-center"><div><span className="text-[11px] tracking-[.2em] uppercase text-[#d6ae8a] font-bold">THE ATELIER WAY</span><h2 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight mt-3">Good journeys begin with a good choice.</h2><p className="text-white/60 mt-3 text-sm max-w-xl">Explore the collection at your pace. Clear availability, straightforward pricing, and a car for the road ahead.</p></div><div className="flex items-center gap-3 text-white/80 text-sm"><Sparkles size={20} className="text-[#d6ae8a]"/> Made for the journey</div></div></section>
    </main>
    <footer className="site-width footer"><div className="flex items-center gap-3"><Mark/><span className="brand-name">ATELIER<span className="brand-dot">.</span> MOTORS</span></div><span>© {new Date().getFullYear()} Atelier Motors. The road is yours.</span><span className="text-xs text-forest/40">Inventory system</span></footer>
    {modal && <VehicleModal key={`${modal.mode}-${modal.vehicle?.id ?? 'new'}`} mode={modal.mode} vehicle={modal.vehicle} onClose={() => setModal(null)} onSave={saveVehicle} />}
  </div>
}
