import { render, screen, waitFor } from '@testing-library/react'
import { Dashboard } from '@/components/dashboard/Dashboard'
import { useAuthStore, useNewsStore } from '@/lib/store'
import { useRealTimeNews } from '@/hooks/useRealTimeNews'
import { apiClient } from '@/lib/api'
import { jest } from '@jest/globals'

// Mock all the dependencies
jest.mock('@/lib/store')
jest.mock('@/hooks/useRealTimeNews')
jest.mock('@/lib/api')

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>
const mockUseNewsStore = useNewsStore as jest.MockedFunction<typeof useNewsStore>
const mockUseRealTimeNews = useRealTimeNews as jest.MockedFunction<typeof useRealTimeNews>

const mockNewsData = [
  {
    id: 1,
    title: 'Test News 1',
    content: 'Test content 1',
    url: 'https://example.com/1',
    source: 'Test Source',
    publishedAt: '2025-09-01T00:00:00Z',
    importanceScore: 3,
    isUrgent: false,
    marketImpact: 2,
    isProcessed: true,
    createdAt: '2025-09-01T00:00:00Z',
    updatedAt: '2025-09-01T00:00:00Z'
  }
]

describe('Dashboard', () => {
  beforeEach(() => {
    // Mock auth store
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

    // Mock news store
    mockUseNewsStore.mockReturnValue({
      news: mockNewsData,
      isConnected: true,
      filters: {},
      loading: false,
      error: null,
      addNews: jest.fn(),
      setNews: jest.fn(),
      setConnected: jest.fn(),
      setFilters: jest.fn(),
      clearError: jest.fn(),
      setError: jest.fn(),
      setLoading: jest.fn()
    })

    // Mock real-time news hook
    mockUseRealTimeNews.mockReturnValue({
      socket: null
    })

    // Mock API client
    ;(apiClient.getNews as jest.Mock).mockResolvedValue(mockNewsData)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders dashboard with header and news', async () => {
    render(<Dashboard />)
    
    // Check header elements
    expect(screen.getByText('加密新闻')).toBeInTheDocument()
    expect(screen.getByText('实时')).toBeInTheDocument()
    
    // Check main content
    expect(screen.getByText('实时加密新闻')).toBeInTheDocument()
    expect(screen.getByText('最新的加密货币行业动态和市场资讯')).toBeInTheDocument()
    
    // Wait for news to load
    await waitFor(() => {
      expect(screen.getByText('Test News 1')).toBeInTheDocument()
    })
  })

  it('shows authenticated user content when logged in', () => {
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
    
    render(<Dashboard />)
    
    expect(screen.getByText('个人新闻源')).toBeInTheDocument()
    expect(screen.getByText('为您精选的个性化加密货币资讯')).toBeInTheDocument()
  })

  it('shows offline status when not connected', () => {
    mockUseNewsStore.mockReturnValue({
      news: mockNewsData,
      isConnected: false,
      filters: {},
      loading: false,
      error: null,
      addNews: jest.fn(),
      setNews: jest.fn(),
      setConnected: jest.fn(),
      setFilters: jest.fn(),
      clearError: jest.fn(),
      setError: jest.fn(),
      setLoading: jest.fn()
    })
    
    render(<Dashboard />)
    
    expect(screen.getByText('离线')).toBeInTheDocument()
  })

  it('shows empty state when no news available', () => {
    mockUseNewsStore.mockReturnValue({
      news: [],
      isConnected: true,
      filters: {},
      loading: false,
      error: null,
      addNews: jest.fn(),
      setNews: jest.fn(),
      setConnected: jest.fn(),
      setFilters: jest.fn(),
      clearError: jest.fn(),
      setError: jest.fn(),
      setLoading: jest.fn()
    })
    
    render(<Dashboard />)
    
    expect(screen.getByText('暂无新闻')).toBeInTheDocument()
    expect(screen.getByText('暂时没有找到符合条件的新闻，请稍后再试或调整筛选条件。')).toBeInTheDocument()
  })

  it('shows error state when there is an error', async () => {
    ;(apiClient.getNews as jest.Mock).mockRejectedValue(new Error('API Error'))
    
    render(<Dashboard />)
    
    await waitFor(() => {
      expect(screen.getByText(/加载新闻时出错/)).toBeInTheDocument()
    })
  })
})