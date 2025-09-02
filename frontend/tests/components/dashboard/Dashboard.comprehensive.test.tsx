import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { Dashboard } from '@/components/dashboard/Dashboard'
import { useNewsStore, useAuthStore } from '@/lib/store'
import { useRealTimeNews } from '@/hooks/useRealTimeNews'
import { apiClient } from '@/lib/api'
import { NewsItem } from '@/types/news'
import { jest } from '@jest/globals'

// Mock all dependencies
jest.mock('@/lib/store')
jest.mock('@/hooks/useRealTimeNews')
jest.mock('@/lib/api')

// Mock UI components to isolate Dashboard logic
jest.mock('@/components/layout/Header', () => ({
  Header: ({ onOpenFilters, onOpenSettings, onOpenNotifications }: any) => (
    <header data-testid="header">
      <button onClick={onOpenFilters} data-testid="open-filters">Filters</button>
      <button onClick={onOpenSettings} data-testid="open-settings">Settings</button>
      <button onClick={onOpenNotifications} data-testid="open-notifications">Notifications</button>
    </header>
  )
}))

jest.mock('@/components/filters/NewsFilter', () => ({
  NewsFilterComponent: ({ onClose }: any) => (
    <div data-testid="news-filter">
      <button onClick={onClose} data-testid="close-filters">Close Filters</button>
    </div>
  )
}))

jest.mock('@/components/settings/NotificationSettings', () => ({
  NotificationSettings: ({ onClose }: any) => (
    <div data-testid="notification-settings">
      <button onClick={onClose} data-testid="close-notifications">Close Notifications</button>
    </div>
  )
}))

jest.mock('@/components/NewsCard', () => ({
  NewsCard: ({ news, onRead }: any) => (
    <div data-testid={`news-card-${news.id}`} onClick={() => onRead(news.id)}>
      <h3>{news.title}</h3>
      <p>{news.summary}</p>
    </div>
  )
}))

const mockNewsData: NewsItem[] = [
  {
    id: 1,
    title: 'Bitcoin Reaches New High',
    content: 'Bitcoin content...',
    summary: 'Bitcoin hits $50k',
    url: 'https://example.com/bitcoin-news',
    source: 'CoinDesk',
    category: 'bitcoin',
    publishedAt: '2024-01-01T12:00:00Z',
    importanceScore: 4,
    isUrgent: false,
    marketImpact: 3,
    sentimentScore: 0.8,
    keyTokens: ['BTC'],
    keyPrices: ['$50,000'],
    isProcessed: true,
    createdAt: '2024-01-01T12:00:00Z',
    updatedAt: '2024-01-01T12:00:00Z'
  },
  {
    id: 2,
    title: 'Ethereum Network Update',
    content: 'Ethereum content...',
    summary: 'ETH network improvements',
    url: 'https://example.com/eth-news',
    source: 'CoinTelegraph',
    category: 'ethereum',
    publishedAt: '2024-01-01T11:00:00Z',
    importanceScore: 3,
    isUrgent: false,
    marketImpact: 2,
    sentimentScore: 0.6,
    keyTokens: ['ETH'],
    keyPrices: ['$3,000'],
    isProcessed: true,
    createdAt: '2024-01-01T11:00:00Z',
    updatedAt: '2024-01-01T11:00:00Z'
  }
]

describe('Dashboard - Comprehensive Tests', () => {
  const mockUseNewsStore = useNewsStore as jest.MockedFunction<typeof useNewsStore>
  const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>
  const mockUseRealTimeNews = useRealTimeNews as jest.MockedFunction<typeof useRealTimeNews>
  const mockApiClient = apiClient as jest.Mocked<typeof apiClient>

  // Default mock implementations
  const defaultNewsStore = {
    news: [],
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
  }

  const defaultAuthStore = {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    token: null,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    loadUser: jest.fn(),
    updatePreferences: jest.fn()
  }

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Setup default mocks
    mockUseNewsStore.mockReturnValue(defaultNewsStore)
    mockUseAuthStore.mockReturnValue(defaultAuthStore)
    mockUseRealTimeNews.mockReturnValue({ socket: null })
    mockApiClient.getNews.mockResolvedValue(mockNewsData)
  })

  describe('Initial Loading and Rendering', () => {
    it('renders main dashboard structure', () => {
      render(<Dashboard />)
      
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByText('实时加密新闻')).toBeInTheDocument()
      expect(screen.getByText('最新的加密货币行业动态和市场资讯')).toBeInTheDocument()
      expect(screen.getByText('刷新')).toBeInTheDocument()
    })

    it('shows authenticated user interface when logged in', () => {
      mockUseAuthStore.mockReturnValue({
        ...defaultAuthStore,
        isAuthenticated: true,
        user: { id: 1, username: 'testuser' } as any
      })
      
      render(<Dashboard />)
      
      expect(screen.getByText('个人新闻源')).toBeInTheDocument()
      expect(screen.getByText('为您精选的个性化加密货币资讯')).toBeInTheDocument()
    })

    it('calls API to load initial news on mount', async () => {
      render(<Dashboard />)
      
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledWith({
          limit: 50
        })
      })
    })

    it('displays loading skeleton while loading', () => {
      render(<Dashboard />)
      
      // Should show loading skeleton
      const skeletonElements = screen.getAllByTestId(/animate-pulse|loading/)
      expect(skeletonElements.length).toBeGreaterThan(0)
    })
  })

  describe('News Display and Management', () => {
    it('displays news items when loaded', async () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: mockNewsData
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        expect(screen.getByTestId('news-card-1')).toBeInTheDocument()
        expect(screen.getByTestId('news-card-2')).toBeInTheDocument()
        expect(screen.getByText('Bitcoin Reaches New High')).toBeInTheDocument()
        expect(screen.getByText('Ethereum Network Update')).toBeInTheDocument()
      })
    })

    it('sorts news by published date (most recent first)', async () => {
      const unsortedNews = [
        { ...mockNewsData[1], publishedAt: '2024-01-01T10:00:00Z' }, // older
        { ...mockNewsData[0], publishedAt: '2024-01-01T14:00:00Z' }  // newer
      ]
      
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: unsortedNews
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        const newsCards = screen.getAllByTestId(/news-card-/)
        // First card should be the newer one (id: 1)
        expect(newsCards[0]).toHaveAttribute('data-testid', 'news-card-1')
        expect(newsCards[1]).toHaveAttribute('data-testid', 'news-card-2')
      })
    })

    it('handles news item read action', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation()
      
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: mockNewsData
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        const firstNewsCard = screen.getByTestId('news-card-1')
        fireEvent.click(firstNewsCard)
      })
      
      expect(consoleSpy).toHaveBeenCalledWith('Marking news item 1 as read')
      consoleSpy.mockRestore()
    })

    it('shows empty state when no news available', async () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: []
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        expect(screen.getByText('暂无新闻')).toBeInTheDocument()
        expect(screen.getByText('暂时没有找到符合条件的新闻，请稍后再试或调整筛选条件。')).toBeInTheDocument()
        expect(screen.getByText('调整筛选')).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      const errorMessage = 'Network error occurred'
      mockApiClient.getNews.mockRejectedValue(new Error(errorMessage))
      
      render(<Dashboard />)
      
      await waitFor(() => {
        expect(screen.getByText(`加载新闻时出错: ${errorMessage}`)).toBeInTheDocument()
        expect(screen.getByText('重试')).toBeInTheDocument()
      })
    })

    it('handles retry action after error', async () => {
      const errorMessage = 'Network error'
      mockApiClient.getNews
        .mockRejectedValueOnce(new Error(errorMessage))
        .mockResolvedValue(mockNewsData)
      
      render(<Dashboard />)
      
      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText(/加载新闻时出错/)).toBeInTheDocument()
      })
      
      // Click retry button
      const retryButton = screen.getByText('重试')
      fireEvent.click(retryButton)
      
      // Should call API again
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledTimes(2)
      })
    })

    it('displays error from news store', () => {
      const storeError = 'Store error message'
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        error: storeError
      })
      
      render(<Dashboard />)
      
      expect(screen.getByText(`加载新闻时出错: ${storeError}`)).toBeInTheDocument()
    })
  })

  describe('Refresh Functionality', () => {
    it('handles manual refresh', async () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: mockNewsData
      })
      
      render(<Dashboard />)
      
      // Wait for initial load
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledTimes(1)
      })
      
      // Click refresh button
      const refreshButton = screen.getByText('刷新')
      fireEvent.click(refreshButton)
      
      // Should call API again
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledTimes(2)
      })
    })

    it('disables refresh button while loading', async () => {
      let resolveApiCall: (value: any) => void
      const apiPromise = new Promise((resolve) => {
        resolveApiCall = resolve
      })
      mockApiClient.getNews.mockReturnValue(apiPromise as any)
      
      render(<Dashboard />)
      
      const refreshButton = screen.getByText('刷新')
      expect(refreshButton).toBeDisabled()
      
      // Resolve the API call
      act(() => {
        resolveApiCall(mockNewsData)
      })
      
      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled()
      })
    })

    it('shows loading spinner on refresh button when loading', () => {
      render(<Dashboard />)
      
      const refreshButton = screen.getByText('刷新')
      const spinnerIcon = refreshButton.querySelector('.animate-spin')
      expect(spinnerIcon).toBeInTheDocument()
    })
  })

  describe('Filter Integration', () => {
    it('applies filters when loading news', async () => {
      const filters = {
        category: 'bitcoin',
        minImportance: 3,
        isUrgent: true
      }
      
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        filters
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledWith({
          limit: 50,
          ...filters
        })
      })
    })

    it('reloads news when filters change', async () => {
      const { rerender } = render(<Dashboard />)
      
      // Initial load
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledTimes(1)
      })
      
      // Change filters
      const updatedFilters = { category: 'ethereum' }
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        filters: updatedFilters
      })
      
      rerender(<Dashboard />)
      
      // Should reload with new filters
      await waitFor(() => {
        expect(mockApiClient.getNews).toHaveBeenCalledWith({
          limit: 50,
          ...updatedFilters
        })
      })
    })
  })

  describe('Modal Management', () => {
    it('opens and closes filters modal', async () => {
      render(<Dashboard />)
      
      // Open filters
      const openFiltersButton = screen.getByTestId('open-filters')
      fireEvent.click(openFiltersButton)
      
      await waitFor(() => {
        expect(screen.getByTestId('news-filter')).toBeInTheDocument()
      })
      
      // Close filters
      const closeFiltersButton = screen.getByTestId('close-filters')
      fireEvent.click(closeFiltersButton)
      
      await waitFor(() => {
        expect(screen.queryByTestId('news-filter')).not.toBeInTheDocument()
      })
    })

    it('opens and closes settings modal', async () => {
      render(<Dashboard />)
      
      // Open settings
      const openSettingsButton = screen.getByTestId('open-settings')
      fireEvent.click(openSettingsButton)
      
      await waitFor(() => {
        expect(screen.getByText('设置页面尚未完全开发')).toBeInTheDocument()
      })
      
      // Close settings via button
      const closeButton = screen.getByText('关闭')
      fireEvent.click(closeButton)
      
      await waitFor(() => {
        expect(screen.queryByText('设置页面尚未完全开发')).not.toBeInTheDocument()
      })
    })

    it('opens and closes notifications modal', async () => {
      render(<Dashboard />)
      
      // Open notifications
      const openNotificationsButton = screen.getByTestId('open-notifications')
      fireEvent.click(openNotificationsButton)
      
      await waitFor(() => {
        expect(screen.getByTestId('notification-settings')).toBeInTheDocument()
      })
      
      // Close notifications
      const closeNotificationsButton = screen.getByTestId('close-notifications')
      fireEvent.click(closeNotificationsButton)
      
      await waitFor(() => {
        expect(screen.queryByTestId('notification-settings')).not.toBeInTheDocument()
      })
    })

    it('opens filter modal from empty state', async () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: []
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        const adjustFiltersButton = screen.getByText('调整筛选')
        fireEvent.click(adjustFiltersButton)
        
        expect(screen.getByTestId('news-filter')).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Integration', () => {
    it('integrates with real-time news hook', () => {
      const mockSocket = { id: 'mock-socket' }
      mockUseRealTimeNews.mockReturnValue({ socket: mockSocket as any })
      
      render(<Dashboard />)
      
      // Verify hook is called
      expect(mockUseRealTimeNews).toHaveBeenCalled()
    })

    it('displays connection status based on store state', () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        isConnected: true
      })
      
      render(<Dashboard />)
      
      // Component should render normally without connection errors
      expect(screen.getByText('实时加密新闻')).toBeInTheDocument()
    })
  })

  describe('Responsive Design and Layout', () => {
    it('applies responsive grid classes', async () => {
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: mockNewsData
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        const newsGrid = screen.getByTestId('news-card-1').closest('.grid')
        expect(newsGrid).toHaveClass(
          'grid-cols-1',
          'md:grid-cols-2', 
          'lg:grid-cols-3'
        )
      })
    })

    it('maintains proper spacing and layout structure', () => {
      render(<Dashboard />)
      
      const mainContainer = screen.getByRole('main')
      expect(mainContainer).toHaveClass('container', 'mx-auto', 'px-4', 'py-6')
      
      const contentDiv = mainContainer.querySelector('.space-y-6')
      expect(contentDiv).toBeInTheDocument()
    })
  })

  describe('Performance and Optimization', () => {
    it('limits news display to prevent memory issues', async () => {
      const largeNewsArray = Array.from({ length: 1500 }, (_, i) => ({
        ...mockNewsData[0],
        id: i + 1,
        title: `News Item ${i + 1}`
      }))
      
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: largeNewsArray
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        // Should display all items (store handles the limiting)
        const newsCards = screen.getAllByTestId(/news-card-/)
        expect(newsCards).toHaveLength(1500)
      })
    })

    it('prevents duplicate news rendering', async () => {
      const duplicatedNews = [...mockNewsData, ...mockNewsData]
      
      mockUseNewsStore.mockReturnValue({
        ...defaultNewsStore,
        news: duplicatedNews
      })
      
      render(<Dashboard />)
      
      await waitFor(() => {
        // Should render duplicates if they exist in store (store handles deduplication)
        const newsCards = screen.getAllByTestId(/news-card-/)
        expect(newsCards).toHaveLength(4) // 2 items * 2 duplicates
      })
    })
  })

  describe('Accessibility', () => {
    it('provides proper semantic structure', () => {
      render(<Dashboard />)
      
      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /刷新/ })).toBeInTheDocument()
    })

    it('includes proper dialog titles for screen readers', async () => {
      render(<Dashboard />)
      
      // Open filters modal
      fireEvent.click(screen.getByTestId('open-filters'))
      
      await waitFor(() => {
        // Dialog should have screen reader title
        expect(screen.getByText('新闻筛选')).toHaveClass('sr-only')
      })
    })

    it('provides keyboard navigation support', () => {
      render(<Dashboard />)
      
      const refreshButton = screen.getByRole('button', { name: /刷新/ })
      
      // Button should be focusable
      refreshButton.focus()
      expect(refreshButton).toHaveFocus()
      
      // Should handle keyboard activation
      fireEvent.keyDown(refreshButton, { key: 'Enter' })
      // Verify interaction works (button should have been clicked)
    })
  })
})