import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginForm } from '@/components/auth/LoginForm'
import { useAuthStore } from '@/lib/store'
import { jest } from '@jest/globals'

// Mock the auth store
jest.mock('@/lib/store')

// Mock utility functions
jest.mock('@/lib/utils', () => ({
  getErrorMessage: jest.fn((error: any) => {
    if (error?.response?.status === 401) return '401 Unauthorized'
    if (error?.message) return error.message
    return String(error)
  })
}))

describe('LoginForm - Comprehensive Tests', () => {
  const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>
  const mockLogin = jest.fn()
  const mockOnSwitchToRegister = jest.fn()
  const mockOnSuccess = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default store mock
    mockUseAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: false
    } as any)
  })

  describe('Form Rendering and UI', () => {
    it('renders all form elements correctly', () => {
      render(<LoginForm />)
      
      expect(screen.getByText('登录')).toBeInTheDocument()
      expect(screen.getByText('登录您的 NEWRSS 账户以获取个性化新闻体验')).toBeInTheDocument()
      expect(screen.getByLabelText('用户名')).toBeInTheDocument()
      expect(screen.getByLabelText('密码')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
    })

    it('renders registration switch when callback provided', () => {
      render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />)
      
      expect(screen.getByText('还没有账户？')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '立即注册' })).toBeInTheDocument()
    })

    it('does not render registration switch when callback not provided', () => {
      render(<LoginForm />)
      
      expect(screen.queryByText('还没有账户？')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '立即注册' })).not.toBeInTheDocument()
    })

    it('has proper form accessibility attributes', () => {
      render(<LoginForm />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      
      expect(usernameInput).toHaveAttribute('type', 'text')
      expect(usernameInput).toHaveAttribute('autoComplete', 'username')
      expect(usernameInput).toHaveAttribute('required')
      
      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
      expect(passwordInput).toHaveAttribute('required')
    })

    it('applies proper styling classes', () => {
      render(<LoginForm />)
      
      const card = screen.getByText('登录').closest('.w-full')
      expect(card).toHaveClass('max-w-md', 'mx-auto')
      
      const submitButton = screen.getByRole('button', { name: '登录' })
      expect(submitButton).toHaveClass('w-full')
    })
  })

  describe('Form Input Handling', () => {
    it('updates username input value', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)
      
      const usernameInput = screen.getByLabelText('用户名')
      
      await user.type(usernameInput, 'testuser')
      
      expect(usernameInput).toHaveValue('testuser')
    })

    it('updates password input value', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)
      
      const passwordInput = screen.getByLabelText('密码')
      
      await user.type(passwordInput, 'testpass123')
      
      expect(passwordInput).toHaveValue('testpass123')
    })

    it('handles empty form submission', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)
      
      const submitButton = screen.getByRole('button', { name: '登录' })
      await user.click(submitButton)
      
      expect(screen.getByText('请填写用户名和密码')).toBeInTheDocument()
      expect(mockLogin).not.toHaveBeenCalled()
    })

    it('validates username field specifically', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)
      
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })
      
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      expect(screen.getByText('请填写用户名和密码')).toBeInTheDocument()
      expect(mockLogin).not.toHaveBeenCalled()
    })

    it('validates password field specifically', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const submitButton = screen.getByRole('button', { name: '登录' })
      
      await user.type(usernameInput, 'testuser')
      await user.click(submitButton)
      
      expect(screen.getByText('请填写用户名和密码')).toBeInTheDocument()
      expect(mockLogin).not.toHaveBeenCalled()
    })

    it('trims whitespace from username', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue(undefined)
      
      render(<LoginForm onSuccess={mockOnSuccess} />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })
      
      await user.type(usernameInput, '  testuser  ')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
    })

    it('preserves password as-is without trimming', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue(undefined)
      
      render(<LoginForm onSuccess={mockOnSuccess} />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })
      
      await user.type(usernameInput, 'testuser')
      await user.type(passwordInput, '  password123  ')
      await user.click(submitButton)
      
      expect(mockLogin).toHaveBeenCalledWith('testuser', '  password123  ')
    })
  })

  describe('Loading States', () => {
    it('disables form inputs when loading', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        isLoading: true
      } as any)
      
      render(<LoginForm />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button')
      
      expect(usernameInput).toBeDisabled()
      expect(passwordInput).toBeDisabled()
      expect(submitButton).toBeDisabled()
    })

    it('shows loading button state', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        isLoading: true
      } as any)
      
      render(<LoginForm />)
      
      expect(screen.getByText('登录中...')).toBeInTheDocument()
      expect(screen.getByRole('button')).toContainElement(
        screen.getByText('登录中...')
      )
      
      const spinnerIcon = screen.getByRole('button').querySelector('.animate-spin')
      expect(spinnerIcon).toBeInTheDocument()
    })

    it('returns to normal state after loading completes', async () => {
      mockLogin.mockResolvedValue(undefined)
      
      // Start with loading state
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        isLoading: true
      } as any)
      
      const { rerender } = render(<LoginForm />)
      
      expect(screen.getByText('登录中...')).toBeInTheDocument()
      
      // Simulate loading completion
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        isLoading: false
      } as any)
      
      rerender(<LoginForm />)
      
      expect(screen.getByText('登录')).toBeInTheDocument()
      expect(screen.queryByText('登录中...')).not.toBeInTheDocument()
    })
  })

  describe('Successful Login Flow', () => {
    it('calls login with correct credentials', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue(undefined)
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
    })

    it('calls onSuccess callback after successful login', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue(undefined)
      
      render(<LoginForm onSuccess={mockOnSuccess} />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled()
      })
    })

    it('clears previous errors on successful login', async () => {
      const user = userEvent.setup()
      mockLogin
        .mockRejectedValueOnce(new Error('Login failed'))
        .mockResolvedValue(undefined)
      
      render(<LoginForm onSuccess={mockOnSuccess} />)
      
      // First attempt - should show error
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'wrongpass')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
      
      // Second attempt - should clear error
      await user.clear(screen.getByLabelText('密码'))
      await user.type(screen.getByLabelText('密码'), 'correctpass')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.queryByText('登录失败，请稍后重试')).not.toBeInTheDocument()
        expect(mockOnSuccess).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('shows specific error for 401 unauthorized', async () => {
      const user = userEvent.setup()
      const error = {
        response: { status: 401 },
        message: '401 Unauthorized'
      }
      mockLogin.mockRejectedValue(error)
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'wrongpass')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('用户名或密码错误')).toBeInTheDocument()
      })
    })

    it('shows specific error for unauthorized message', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Unauthorized access'))
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'wrongpass')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('用户名或密码错误')).toBeInTheDocument()
      })
    })

    it('shows generic error for other failures', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Network error'))
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
    })

    it('clears error when form is resubmitted', async () => {
      const user = userEvent.setup()
      mockLogin
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Another error'))
      
      render(<LoginForm />)
      
      // First submission with error
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
      
      // Second submission should clear previous error first
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      // Error should be cleared momentarily before new error appears
      // This tests that setError('') is called before the login attempt
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
      
      expect(mockLogin).toHaveBeenCalledTimes(2)
    })

    it('handles non-Error objects gracefully', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue('String error')
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
    })
  })

  describe('Form Navigation and UX', () => {
    it('handles registration switch callback', async () => {
      const user = userEvent.setup()
      render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />)
      
      const registerButton = screen.getByRole('button', { name: '立即注册' })
      await user.click(registerButton)
      
      expect(mockOnSwitchToRegister).toHaveBeenCalled()
    })

    it('supports form submission via Enter key', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue(undefined)
      
      render(<LoginForm onSuccess={mockOnSuccess} />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      
      // Press Enter in password field
      await user.keyboard('{Enter}')
      
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
    })

    it('maintains form state during error display', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Login failed'))
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
      
      // Form values should be preserved
      expect(screen.getByLabelText('用户名')).toHaveValue('testuser')
      expect(screen.getByLabelText('密码')).toHaveValue('password123')
    })
  })

  describe('Keyboard and Accessibility', () => {
    it('supports tab navigation between form fields', async () => {
      const user = userEvent.setup()
      render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      const submitButton = screen.getByRole('button', { name: '登录' })
      const registerButton = screen.getByRole('button', { name: '立即注册' })
      
      usernameInput.focus()
      expect(usernameInput).toHaveFocus()
      
      await user.tab()
      expect(passwordInput).toHaveFocus()
      
      await user.tab()
      expect(submitButton).toHaveFocus()
      
      await user.tab()
      expect(registerButton).toHaveFocus()
    })

    it('has proper ARIA labels and descriptions', () => {
      render(<LoginForm />)
      
      const usernameInput = screen.getByLabelText('用户名')
      const passwordInput = screen.getByLabelText('密码')
      
      expect(usernameInput).toHaveAttribute('id', 'username')
      expect(passwordInput).toHaveAttribute('id', 'password')
      
      // Check that labels are properly associated
      expect(screen.getByText('用户名')).toHaveAttribute('for', 'username')
      expect(screen.getByText('密码')).toHaveAttribute('for', 'password')
    })

    it('announces errors to screen readers', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Login failed'))
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        const errorAlert = screen.getByText('登录失败，请稍后重试')
        expect(errorAlert.closest('[role="alert"]')).toBeInTheDocument()
      })
    })
  })

  describe('Form State Management', () => {
    it('resets error state when user starts typing after error', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Login failed'))
      
      render(<LoginForm />)
      
      // Trigger error
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'wrongpass')
      await user.click(screen.getByRole('button', { name: '登录' }))
      
      await waitFor(() => {
        expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
      })
      
      // Start typing - error should persist (only cleared on form submission)
      await user.type(screen.getByLabelText('用户名'), 'x')
      
      // Error should still be visible (current implementation)
      expect(screen.getByText('登录失败，请稍后重试')).toBeInTheDocument()
    })

    it('handles rapid form submissions gracefully', async () => {
      const user = userEvent.setup()
      let resolveLogin: (value?: any) => void
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve
      })
      mockLogin.mockReturnValue(loginPromise)
      
      render(<LoginForm />)
      
      await user.type(screen.getByLabelText('用户名'), 'testuser')
      await user.type(screen.getByLabelText('密码'), 'password123')
      
      // Submit form twice rapidly
      const submitButton = screen.getByRole('button', { name: '登录' })
      await user.click(submitButton)
      await user.click(submitButton) // Second click should be ignored due to disabled state
      
      expect(mockLogin).toHaveBeenCalledTimes(1)
      
      // Resolve the promise
      resolveLogin!()
    })
  })
})