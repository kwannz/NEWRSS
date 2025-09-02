import { render, screen, fireEvent } from '@testing-library/react'
import { NotificationSettings } from '@/components/settings/NotificationSettings'
import { useAuthStore, useNotificationStore } from '@/lib/store'
import { jest } from '@jest/globals'

// Mock the stores
jest.mock('@/lib/store')

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>
const mockUseNotificationStore = useNotificationStore as jest.MockedFunction<typeof useNotificationStore>

describe('NotificationSettings', () => {
  const mockUpdatePreferences = jest.fn()
  const mockRequestBrowserPermission = jest.fn()
  const mockCheckTelegramConnection = jest.fn()
  
  beforeEach(() => {
    mockUseAuthStore.mockReturnValue({
      user: { id: 1, username: 'testuser', email: 'test@example.com', is_active: true },
      isAuthenticated: true,
      isLoading: false,
      token: 'test-token',
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      loadUser: jest.fn(),
      updatePreferences: jest.fn()
    })

    mockUseNotificationStore.mockReturnValue({
      browserPermission: 'granted' as NotificationPermission,
      telegramConnected: false,
      preferences: {
        urgentNotifications: true,
        dailyDigest: false,
        browserNotifications: true,
        telegramNotifications: false,
        minImportance: 3,
        maxDailyNotifications: 10
      },
      requestBrowserPermission: mockRequestBrowserPermission,
      updatePreferences: mockUpdatePreferences,
      checkTelegramConnection: mockCheckTelegramConnection
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders notification settings for authenticated user', () => {
    render(<NotificationSettings />)
    
    expect(screen.getByText('通知设置')).toBeInTheDocument()
    expect(screen.getByText('管理您的新闻通知偏好和渠道')).toBeInTheDocument()
    expect(screen.getByText('浏览器通知')).toBeInTheDocument()
    expect(screen.getByText('Telegram 通知')).toBeInTheDocument()
  })

  it('shows login prompt for unauthenticated users', () => {
    mockUseAuthStore.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      token: null,
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      loadUser: jest.fn(),
      updatePreferences: jest.fn()
    })
    
    render(<NotificationSettings />)
    
    expect(screen.getByText('请先登录以管理您的通知偏好')).toBeInTheDocument()
    expect(screen.getByText('登录后可以个性化您的通知设置')).toBeInTheDocument()
  })

  it('displays browser permission status correctly', () => {
    render(<NotificationSettings />)
    
    expect(screen.getByText('已授权')).toBeInTheDocument()
  })

  it('shows telegram connection status', () => {
    render(<NotificationSettings />)
    
    expect(screen.getByText('未连接')).toBeInTheDocument()
    expect(screen.getByText('您尚未连接 Telegram 账户')).toBeInTheDocument()
    expect(screen.getByText('连接 Telegram')).toBeInTheDocument()
  })

  it('toggles notification preferences', () => {
    render(<NotificationSettings />)
    
    const urgentToggle = screen.getAllByRole('switch')[0] // First switch is urgent notifications
    fireEvent.click(urgentToggle)
    
    expect(mockUpdatePreferences).toHaveBeenCalledWith({ urgentNotifications: false })
  })

  it('shows telegram connected status when connected', () => {
    mockUseNotificationStore.mockReturnValue({
      browserPermission: 'granted' as NotificationPermission,
      telegramConnected: true,
      preferences: {
        urgentNotifications: true,
        dailyDigest: false,
        browserNotifications: true,
        telegramNotifications: true,
        minImportance: 3,
        maxDailyNotifications: 10
      },
      requestBrowserPermission: mockRequestBrowserPermission,
      updatePreferences: mockUpdatePreferences,
      checkTelegramConnection: mockCheckTelegramConnection
    })
    
    render(<NotificationSettings />)
    
    expect(screen.getByText('已连接')).toBeInTheDocument()
    expect(screen.queryByText('您尚未连接 Telegram 账户')).not.toBeInTheDocument()
  })
})