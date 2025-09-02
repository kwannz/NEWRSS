import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { LoginForm } from '@/components/auth/LoginForm'
import { useAuthStore } from '@/lib/store'
import { jest } from '@jest/globals'

// Mock the auth store
jest.mock('@/lib/store', () => ({
  useAuthStore: jest.fn()
}))

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    login: jest.fn(),
    getCurrentUser: jest.fn()
  }
}))

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>

describe('LoginForm', () => {
  const mockLogin = jest.fn()
  const mockOnSuccess = jest.fn()
  const mockOnSwitchToRegister = jest.fn()

  beforeEach(() => {
    mockUseAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: false,
      user: null,
      isAuthenticated: false,
      token: null,
      register: jest.fn(),
      logout: jest.fn(),
      loadUser: jest.fn(),
      updatePreferences: jest.fn()
    })
    jest.clearAllMocks()
  })

  it('renders login form correctly', () => {
    render(<LoginForm onSuccess={mockOnSuccess} onSwitchToRegister={mockOnSwitchToRegister} />)
    
    expect(screen.getByText('登录')).toBeInTheDocument()
    expect(screen.getByLabelText('用户名')).toBeInTheDocument()
    expect(screen.getByLabelText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
  })

  it('shows validation error for empty fields', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)
    
    const submitButton = screen.getByRole('button', { name: '登录' })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('请填写用户名和密码')).toBeInTheDocument()
    })
  })

  it('calls login function with correct credentials', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)
    
    const usernameInput = screen.getByLabelText('用户名')
    const passwordInput = screen.getByLabelText('密码')
    const submitButton = screen.getByRole('button', { name: '登录' })
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'testpass' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'testpass')
    })
  })

  it('shows switch to register button when handler provided', () => {
    render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />)
    
    const switchButton = screen.getByRole('button', { name: '立即注册' })
    expect(switchButton).toBeInTheDocument()
    
    fireEvent.click(switchButton)
    expect(mockOnSwitchToRegister).toHaveBeenCalled()
  })

  it('shows loading state during login', () => {
    mockUseAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: true,
      user: null,
      isAuthenticated: false,
      token: null,
      register: jest.fn(),
      logout: jest.fn(),
      loadUser: jest.fn(),
      updatePreferences: jest.fn()
    })
    
    render(<LoginForm />)
    
    expect(screen.getByText('登录中...')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })
})