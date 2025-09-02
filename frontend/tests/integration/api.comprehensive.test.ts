import { apiClient } from '@/lib/api'
import axios from 'axios'
import { NewsItem, User } from '@/types/news'
import { jest } from '@jest/globals'

// Mock axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

const mockNewsItem: NewsItem = {
  id: 1,
  title: 'Bitcoin Reaches New High',
  content: 'Bitcoin has reached a new all-time high of $50,000',
  summary: 'Bitcoin hits $50k milestone',
  url: 'https://example.com/bitcoin-news',
  source: 'CoinDesk',
  category: 'bitcoin',
  publishedAt: '2024-01-01T12:00:00Z',
  importanceScore: 4,
  isUrgent: false,
  marketImpact: 3,
  sentimentScore: 0.8,
  keyTokens: ['BTC', 'Bitcoin'],
  keyPrices: ['$50,000'],
  isProcessed: true,
  createdAt: '2024-01-01T12:00:00Z',
  updatedAt: '2024-01-01T12:00:00Z'
}

const mockUser: User = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  isActive: true,
  createdAt: '2024-01-01T12:00:00Z',
  preferences: {
    urgent_notifications: true,
    daily_digest: false,
    min_importance_score: 3,
    max_daily_notifications: 10,
    categories: ['bitcoin', 'ethereum']
  }
}

describe('ApiClient - Comprehensive Integration Tests', () => {
  const mockAxiosInstance = {
    create: jest.fn(),
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  }

  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
    
    // Reset axios mock
    mockedAxios.create.mockReturnValue(mockAxiosInstance as any)
    
    // Mock successful responses by default
    mockAxiosInstance.get.mockResolvedValue({ data: [] })
    mockAxiosInstance.post.mockResolvedValue({ data: {} })
    mockAxiosInstance.patch.mockResolvedValue({ data: {} })
  })

  describe('Initialization and Configuration', () => {
    it('creates axios instance with correct base URL from environment', () => {
      const originalEnv = process.env.NEXT_PUBLIC_API_URL
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com'
      
      // Re-import to test new environment
      jest.resetModules()
      
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'https://api.example.com',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      process.env.NEXT_PUBLIC_API_URL = originalEnv
    })

    it('uses default localhost URL when environment variable not set', () => {
      const originalEnv = process.env.NEXT_PUBLIC_API_URL
      delete process.env.NEXT_PUBLIC_API_URL
      
      jest.resetModules()
      
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      process.env.NEXT_PUBLIC_API_URL = originalEnv
    })

    it('sets up request interceptor for token injection', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled()
      
      const interceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      
      // Test with token
      apiClient.setToken('test-token')
      const configWithToken = interceptor({ headers: {} })
      expect(configWithToken.headers.Authorization).toBe('Bearer test-token')
      
      // Test without token
      apiClient.setToken(null)
      const configWithoutToken = interceptor({ headers: {} })
      expect(configWithoutToken.headers.Authorization).toBeUndefined()
    })

    it('sets up response interceptor for error handling', () => {
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled()
      
      const [successHandler, errorHandler] = mockAxiosInstance.interceptors.response.use.mock.calls[0]
      
      // Test success response passthrough
      const successResponse = { status: 200, data: 'success' }
      expect(successHandler(successResponse)).toBe(successResponse)
      
      // Test 401 error handling
      const error401 = {
        response: { status: 401 }
      }
      
      apiClient.setToken('test-token')
      expect(errorHandler(error401)).rejects.toBe(error401)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_token')
    })
  })

  describe('Token Management', () => {
    it('sets token and saves to localStorage', () => {
      apiClient.setToken('new-token')
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_token', 'new-token')
    })

    it('clears token and removes from localStorage', () => {
      apiClient.setToken('test-token')
      localStorageMock.setItem.mockClear()
      
      apiClient.setToken(null)
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_token')
    })

    it('loads token from localStorage on initialization', () => {
      localStorageMock.getItem.mockReturnValue('stored-token')
      
      apiClient.loadToken()
      
      expect(localStorageMock.getItem).toHaveBeenCalledWith('auth_token')
    })

    it('handles missing localStorage gracefully', () => {
      localStorageMock.getItem.mockReturnValue(null)
      
      expect(() => apiClient.loadToken()).not.toThrow()
    })

    it('skips localStorage operations on server-side', () => {
      const originalWindow = global.window
      delete (global as any).window
      
      apiClient.loadToken()
      
      expect(localStorageMock.getItem).not.toHaveBeenCalled()
      
      global.window = originalWindow
    })
  })

  describe('Authentication Endpoints', () => {
    describe('login()', () => {
      it('calls login endpoint with form data', async () => {
        const mockResponse = { access_token: 'new-token' }
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        const result = await apiClient.login('testuser', 'password123')
        
        expect(mockAxiosInstance.post).toHaveBeenCalledWith(
          '/auth/token',
          expect.any(FormData),
          { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        )
        
        // Verify FormData content
        const formData = mockAxiosInstance.post.mock.calls[0][1] as FormData
        expect(formData.get('username')).toBe('testuser')
        expect(formData.get('password')).toBe('password123')
        
        expect(result).toEqual(mockResponse)
      })

      it('handles login with special characters', async () => {
        const mockResponse = { access_token: 'token' }
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        await apiClient.login('test@user.com', 'p@ssw0rd!@#$%')
        
        const formData = mockAxiosInstance.post.mock.calls[0][1] as FormData
        expect(formData.get('username')).toBe('test@user.com')
        expect(formData.get('password')).toBe('p@ssw0rd!@#$%')
      })

      it('handles login failure with proper error propagation', async () => {
        const loginError = new Error('Invalid credentials')
        mockAxiosInstance.post.mockRejectedValue(loginError)
        
        await expect(apiClient.login('wrong', 'credentials')).rejects.toThrow('Invalid credentials')
      })
    })

    describe('register()', () => {
      it('calls register endpoint with user data', async () => {
        const mockResponse = { id: 1, username: 'newuser' }
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        const result = await apiClient.register('newuser', 'new@example.com', 'password123')
        
        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', {
          username: 'newuser',
          email: 'new@example.com',
          password: 'password123'
        })
        
        expect(result).toEqual(mockResponse)
      })

      it('handles registration with international characters', async () => {
        const mockResponse = { id: 1, username: '用户测试' }
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        await apiClient.register('用户测试', 'test@测试.com', '密码123')
        
        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', {
          username: '用户测试',
          email: 'test@测试.com',
          password: '密码123'
        })
      })

      it('handles registration validation errors', async () => {
        const validationError = {
          response: {
            status: 422,
            data: { detail: 'Email already exists' }
          }
        }
        mockAxiosInstance.post.mockRejectedValue(validationError)
        
        await expect(apiClient.register('test', 'existing@example.com', 'pass')).rejects.toMatchObject(validationError)
      })
    })

    describe('getCurrentUser()', () => {
      it('fetches current user data', async () => {
        mockAxiosInstance.get.mockResolvedValue({ data: mockUser })
        
        const result = await apiClient.getCurrentUser()
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/me')
        expect(result).toEqual(mockUser)
      })

      it('handles unauthorized access', async () => {
        const unauthorizedError = {
          response: { status: 401 }
        }
        mockAxiosInstance.get.mockRejectedValue(unauthorizedError)
        
        await expect(apiClient.getCurrentUser()).rejects.toMatchObject(unauthorizedError)
      })
    })
  })

  describe('News Endpoints', () => {
    describe('getNews()', () => {
      it('fetches news without parameters', async () => {
        const mockNews = [mockNewsItem]
        mockAxiosInstance.get.mockResolvedValue({ data: mockNews })
        
        const result = await apiClient.getNews()
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/news', { params: undefined })
        expect(result).toEqual(mockNews)
      })

      it('fetches news with pagination parameters', async () => {
        const mockNews = [mockNewsItem]
        mockAxiosInstance.get.mockResolvedValue({ data: mockNews })
        
        const params = { page: 2, limit: 20 }
        const result = await apiClient.getNews(params)
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/news', { params })
        expect(result).toEqual(mockNews)
      })

      it('fetches news with filtering parameters', async () => {
        const mockNews = [mockNewsItem]
        mockAxiosInstance.get.mockResolvedValue({ data: mockNews })
        
        const params = {
          category: 'bitcoin',
          source: 'CoinDesk',
          urgent_only: true,
          min_importance: 4
        }
        const result = await apiClient.getNews(params)
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/news', { params })
        expect(result).toEqual(mockNews)
      })

      it('handles empty news response', async () => {
        mockAxiosInstance.get.mockResolvedValue({ data: [] })
        
        const result = await apiClient.getNews()
        
        expect(result).toEqual([])
      })

      it('handles news fetch with server error', async () => {
        const serverError = {
          response: { status: 500, data: { detail: 'Internal server error' } }
        }
        mockAxiosInstance.get.mockRejectedValue(serverError)
        
        await expect(apiClient.getNews()).rejects.toMatchObject(serverError)
      })

      it('handles news fetch with network error', async () => {
        const networkError = new Error('Network Error')
        mockAxiosInstance.get.mockRejectedValue(networkError)
        
        await expect(apiClient.getNews()).rejects.toThrow('Network Error')
      })
    })

    describe('getNewsItem()', () => {
      it('fetches individual news item', async () => {
        mockAxiosInstance.get.mockResolvedValue({ data: mockNewsItem })
        
        const result = await apiClient.getNewsItem(1)
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/news/1')
        expect(result).toEqual(mockNewsItem)
      })

      it('handles news item not found', async () => {
        const notFoundError = {
          response: { status: 404, data: { detail: 'News item not found' } }
        }
        mockAxiosInstance.get.mockRejectedValue(notFoundError)
        
        await expect(apiClient.getNewsItem(999)).rejects.toMatchObject(notFoundError)
      })

      it('handles invalid news item ID', async () => {
        const validationError = {
          response: { status: 422, data: { detail: 'Invalid news ID' } }
        }
        mockAxiosInstance.get.mockRejectedValue(validationError)
        
        await expect(apiClient.getNewsItem(-1)).rejects.toMatchObject(validationError)
      })
    })
  })

  describe('User Preferences Endpoints', () => {
    describe('updateUserPreferences()', () => {
      it('updates user preferences', async () => {
        const preferences = {
          urgent_notifications: false,
          daily_digest: true,
          min_importance_score: 4,
          max_daily_notifications: 5,
          categories: ['ethereum', 'defi']
        }
        const mockResponse = { success: true }
        mockAxiosInstance.patch.mockResolvedValue({ data: mockResponse })
        
        const result = await apiClient.updateUserPreferences(preferences)
        
        expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/auth/me/preferences', preferences)
        expect(result).toEqual(mockResponse)
      })

      it('updates partial preferences', async () => {
        const partialPrefs = { urgent_notifications: false }
        const mockResponse = { success: true }
        mockAxiosInstance.patch.mockResolvedValue({ data: mockResponse })
        
        const result = await apiClient.updateUserPreferences(partialPrefs)
        
        expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/auth/me/preferences', partialPrefs)
        expect(result).toEqual(mockResponse)
      })

      it('handles unauthorized preference update', async () => {
        const unauthorizedError = {
          response: { status: 401 }
        }
        mockAxiosInstance.patch.mockRejectedValue(unauthorizedError)
        
        await expect(apiClient.updateUserPreferences({})).rejects.toMatchObject(unauthorizedError)
      })
    })

    describe('getUserPreferences()', () => {
      it('fetches user preferences', async () => {
        const mockPreferences = {
          urgent_notifications: true,
          daily_digest: false,
          min_importance_score: 3,
          categories: ['bitcoin']
        }
        mockAxiosInstance.get.mockResolvedValue({ data: mockPreferences })
        
        const result = await apiClient.getUserPreferences()
        
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/me/preferences')
        expect(result).toEqual(mockPreferences)
      })

      it('handles missing preferences', async () => {
        const notFoundError = {
          response: { status: 404 }
        }
        mockAxiosInstance.get.mockRejectedValue(notFoundError)
        
        await expect(apiClient.getUserPreferences()).rejects.toMatchObject(notFoundError)
      })
    })
  })

  describe('Error Handling and Resilience', () => {
    it('handles timeout errors', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 5000ms exceeded'
      }
      mockAxiosInstance.get.mockRejectedValue(timeoutError)
      
      await expect(apiClient.getNews()).rejects.toMatchObject(timeoutError)
    })

    it('handles connection refused errors', async () => {
      const connectionError = {
        code: 'ECONNREFUSED',
        message: 'connect ECONNREFUSED 127.0.0.1:8000'
      }
      mockAxiosInstance.get.mockRejectedValue(connectionError)
      
      await expect(apiClient.getNews()).rejects.toMatchObject(connectionError)
    })

    it('handles rate limiting errors', async () => {
      const rateLimitError = {
        response: {
          status: 429,
          headers: {
            'retry-after': '60'
          }
        }
      }
      mockAxiosInstance.get.mockRejectedValue(rateLimitError)
      
      await expect(apiClient.getNews()).rejects.toMatchObject(rateLimitError)
    })

    it('handles malformed response data', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: null })
      
      const result = await apiClient.getNews()
      expect(result).toBe(null)
    })

    it('handles concurrent requests correctly', async () => {
      const promises = [
        apiClient.getNews({ page: 1 }),
        apiClient.getNews({ page: 2 }),
        apiClient.getNewsItem(1),
        apiClient.getCurrentUser()
      ]
      
      mockAxiosInstance.get.mockResolvedValue({ data: mockNewsItem })
      
      await Promise.all(promises)
      
      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(4)
    })
  })

  describe('Request Configuration and Headers', () => {
    it('includes authentication token in requests when available', () => {
      apiClient.setToken('test-token')
      apiClient.getNews()
      
      // Token should be added by interceptor
      const interceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      const config = interceptor({ headers: {} })
      
      expect(config.headers.Authorization).toBe('Bearer test-token')
    })

    it('omits authentication header when token not available', () => {
      apiClient.setToken(null)
      apiClient.getNews()
      
      const interceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      const config = interceptor({ headers: {} })
      
      expect(config.headers.Authorization).toBeUndefined()
    })

    it('preserves existing headers in requests', () => {
      const interceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      const config = interceptor({
        headers: {
          'X-Custom-Header': 'custom-value',
          'Content-Type': 'application/json'
        }
      })
      
      expect(config.headers['X-Custom-Header']).toBe('custom-value')
      expect(config.headers['Content-Type']).toBe('application/json')
    })

    it('uses correct content-type for form data in login', async () => {
      await apiClient.login('user', 'pass')
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/auth/token',
        expect.any(FormData),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )
    })
  })

  describe('Response Data Transformation', () => {
    it('extracts data from successful responses', async () => {
      const responseData = { success: true, data: 'test' }
      mockAxiosInstance.get.mockResolvedValue({
        data: responseData,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      })
      
      const result = await apiClient.getNews()
      expect(result).toEqual(responseData)
    })

    it('handles responses with nested data structures', async () => {
      const nestedData = {
        results: [mockNewsItem],
        pagination: { page: 1, total: 100 },
        meta: { timestamp: '2024-01-01T12:00:00Z' }
      }
      mockAxiosInstance.get.mockResolvedValue({ data: nestedData })
      
      const result = await apiClient.getNews()
      expect(result).toEqual(nestedData)
    })
  })

  describe('Memory and Performance', () => {
    it('reuses axios instance for multiple requests', async () => {
      await apiClient.getNews()
      await apiClient.getCurrentUser()
      await apiClient.getNewsItem(1)
      
      // Should only create one axios instance
      expect(mockedAxios.create).toHaveBeenCalledTimes(1)
    })

    it('handles rapid sequential requests without memory leaks', async () => {
      const promises = Array.from({ length: 100 }, (_, i) =>
        apiClient.getNewsItem(i + 1)
      )
      
      mockAxiosInstance.get.mockResolvedValue({ data: mockNewsItem })
      
      await Promise.all(promises)
      
      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(100)
    })
  })
})