import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../src/App.jsx'

const car = { id: 7, make: 'Toyota', model: 'Camry', category: 'Sedan', price: 25000, quantity: 2 }
const soldOut = { id: 8, make: 'Honda', model: 'Civic', category: 'Sedan', price: 21000, quantity: 0 }
const json = (body, status = 200) => ({ ok: status < 400, status, json: async () => body })

function mockApi(role = 'user', vehicles = [car, soldOut]) {
  sessionStorage.setItem('atelier_token', 'valid-token')
  let inventory = vehicles
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    if (url.endsWith('/api/auth/me')) return json({ id: 1, email: 'buyer@example.com', role })
    if (url.endsWith('/api/vehicles') && (!options.method || options.method === 'GET')) return json(inventory)
    if (url.includes('/api/vehicles/search')) return json(inventory.filter(v => v.make.toLowerCase() === 'toyota'))
    if (url.endsWith('/7/purchase')) {
      inventory = inventory.map(v => v.id === 7 ? { ...v, quantity: v.quantity - 1 } : v)
      return json(inventory.find(v => v.id === 7))
    }
    if (url.endsWith('/7') && options.method === 'DELETE') {
      inventory = inventory.filter(v => v.id !== 7)
      return { ok: true, status: 204 }
    }
    if (url.endsWith('/api/vehicles') && options.method === 'POST') {
      const added = { id: 9, ...JSON.parse(options.body) }
      inventory = [...inventory, added]
      return json(added, 201)
    }
    if (url.endsWith('/7/restock') && options.method === 'POST') {
      inventory = inventory.map(v => v.id === 7 ? { ...v, quantity: v.quantity + JSON.parse(options.body).amount } : v)
      return json(inventory.find(v => v.id === 7))
    }
    if (url.endsWith('/7') && options.method === 'PUT') {
      inventory = inventory.map(v => v.id === 7 ? { id: 7, ...JSON.parse(options.body) } : v)
      return json(inventory.find(v => v.id === 7))
    }
    throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
  })
  return fetchMock
}

describe('inventory SPA', () => {
  it('logs in and loads inventory with the bearer token', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url.endsWith('/api/auth/login')) return json({ access_token: 'valid-token' })
      if (url.endsWith('/api/auth/me')) return json({ id: 1, email: 'buyer@example.com', role: 'user' })
      if (url.endsWith('/api/vehicles')) return json([car])
      throw new Error(url)
    })
    render(<App />)
    await user.type(screen.getByLabelText(/email address/i), 'buyer@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'SecurePass123!')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(await screen.findByText('Toyota Camry')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/vehicles'), expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer valid-token' }) }))
  })

  it('shows sold-out inventory and prevents purchasing it', async () => {
    mockApi()
    render(<App />)
    const card = await screen.findByTestId('vehicle-8')
    expect(within(card).getByText(/out of stock/i)).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: /sold out/i })).toBeDisabled()
  })

  it('purchases and refreshes the displayed quantity', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi('user', [car])
    render(<App />)
    const card = await screen.findByTestId('vehicle-7')
    await user.click(within(card).getByRole('button', { name: /purchase/i }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/7/purchase'))).toBe(true))
    expect(await within(card).findByText(/1 available/i)).toBeInTheDocument()
  })

  it('hides admin actions for a normal user and shows them for admin', async () => {
    mockApi('user', [car])
    const first = render(<App />)
    await screen.findByText('Toyota Camry')
    expect(screen.queryByRole('button', { name: /add vehicle/i })).not.toBeInTheDocument()
    first.unmount()
    vi.restoreAllMocks()
    mockApi('admin', [car])
    render(<App />)
    expect(await screen.findByRole('button', { name: /add vehicle/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /edit toyota camry/i })).toBeInTheDocument()
  })

  it('searches through the protected API', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi()
    render(<App />)
    await screen.findByText('Toyota Camry')
    await user.type(screen.getByLabelText(/make filter/i), 'toyota')
    await user.click(screen.getByRole('button', { name: /^search vehicles$/i }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.includes('/api/vehicles/search?make=toyota'))).toBe(true))
  })

  it('lets an admin add and restock vehicles through the API', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi('admin', [car])
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /add vehicle/i }))
    const dialog = screen.getByRole('dialog')
    await user.type(within(dialog).getByLabelText(/^make$/i), 'Mazda')
    await user.type(within(dialog).getByLabelText(/^model$/i), 'CX-5')
    await user.type(within(dialog).getByLabelText(/^category$/i), 'SUV')
    await user.type(within(dialog).getByLabelText(/^price/i), '30000')
    await user.type(within(dialog).getByLabelText(/^quantity$/i), '3')
    await user.click(within(dialog).getByRole('button', { name: /add vehicle/i }))
    expect(await screen.findByText('Mazda CX-5')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/vehicles'), expect.objectContaining({ method: 'POST', body: expect.stringContaining('Mazda') }))

    await user.click(screen.getAllByRole('button', { name: 'Restock' })[0])
    const restockDialog = screen.getByRole('dialog')
    await user.clear(within(restockDialog).getByLabelText(/units to add/i))
    await user.type(within(restockDialog).getByLabelText(/units to add/i), '2')
    await user.click(within(restockDialog).getByRole('button', { name: /add stock/i }))
    expect(await screen.findByText('4 available')).toBeInTheDocument()
  })

  it('supports registration and then signs in', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url.endsWith('/api/auth/register')) return json({ id: 1, role: 'user' }, 201)
      if (url.endsWith('/api/auth/login')) return json({ access_token: 'registered-token' })
      if (url.endsWith('/api/auth/me')) return json({ id: 1, email: 'new@example.com', role: 'user' })
      if (url.endsWith('/api/vehicles')) return json([])
      throw new Error(url)
    })
    render(<App />)
    await user.click(screen.getByRole('tab', { name: /create account/i }))
    await user.type(screen.getByLabelText(/email address/i), 'new@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'SecurePass123!')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText('No vehicles found')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/api/auth/register'))).toBe(true)
  })

  it('lets an admin edit and delete a listing', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi('admin', [car])
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Edit Toyota Camry' }))
    const dialog = screen.getByRole('dialog')
    const price = within(dialog).getByLabelText(/^price/i)
    await user.clear(price)
    await user.type(price, '27000')
    await user.click(within(dialog).getByRole('button', { name: /save changes/i }))
    expect(await screen.findByText('$27,000')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Delete Toyota Camry' }))
    expect(await screen.findByText('No vehicles found')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url, options]) => url.endsWith('/7') && options.method === 'DELETE')).toBe(true)
  })

  it('clears an expired session and returns to sign in', async () => {
    sessionStorage.setItem('atelier_token', 'expired')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Invalid or expired token' }, 401))
    render(<App />)
    expect(await screen.findByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
    expect(sessionStorage.getItem('atelier_token')).toBeNull()
  })
})
