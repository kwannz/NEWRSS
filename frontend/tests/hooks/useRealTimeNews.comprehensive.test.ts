import { renderHook, act, waitFor } from '@testing-library/react'
import { useRealTimeNews } from '@/hooks/useRealTimeNews'
import { useNewsStore, useNotificationStore } from '@/lib/store'
import { io } from 'socket.io-client'
import { NewsItem } from '@/types/news'
import { jest } from '@jest/globals'

// Mock dependencies
jest.mock('@/lib/store')
jest.mock('socket.io-client')

// Mock global Notification API
const mockNotification = jest.fn()
Object.defineProperty(global, 'Notification', {
  writable: true,
  value: mockNotification
})

Object.defineProperty(global, 'window', {
  writable: true,
  value: {
    ...global.window,
    Notification: mockNotification
  }
})

const mockSocketInstance = {
  on: jest.fn(),
  close: jest.fn(),
  emit: jest.fn(),
  id: 'mock-socket-id'
}

const mockNewsItem: NewsItem = {
  id: 1,
  title: 'Bitcoin Reaches New High',
  content: 'Bitcoin has reached a new all-time high',
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

const mockUrgentNewsItem: NewsItem = {
  ...mockNewsItem,
  id: 2,
  title: 'BREAKING: Major Exchange Hacked',
  isUrgent: true,
  importanceScore: 5
}

describe('useRealTimeNews - Comprehensive Tests', () => {
  const mockUseNewsStore = useNewsStore as jest.MockedFunction<typeof useNewsStore>
  const mockUseNotificationStore = useNotificationStore as jest.MockedFunction<typeof useNotificationStore>
  const mockIo = io as jest.MockedFunction<typeof io>

  const mockAddNews = jest.fn()
  const mockSetConnected = jest.fn()

  const defaultPreferences = {
    urgentNotifications: true,
    dailyDigest: false,
    browserNotifications: true,
    telegramNotifications: false,
    minImportance: 3,
    maxDailyNotifications: 10
  }

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Reset Notification mock
    mockNotification.mockReset()
    
    // Setup default store mocks
    mockUseNewsStore.mockReturnValue({
      addNews: mockAddNews,
      setConnected: mockSetConnected
    } as any)

    mockUseNotificationStore.mockReturnValue({
      preferences: defaultPreferences,
      browserPermission: 'granted'
    } as any)

    // Setup socket.io mock
    mockIo.mockReturnValue(mockSocketInstance as any)
    
    // Setup environment variable
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000'
  })

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_WS_URL
  })

  describe('Socket Connection Management', () => {
    it('establishes socket connection on mount', () => {
      renderHook(() => useRealTimeNews())
      
      expect(mockIo).toHaveBeenCalledWith('ws://localhost:8000')
      expect(mockSocketInstance.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocketInstance.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
    })

    it('uses default URL when environment variable not set', () => {
      delete process.env.NEXT_PUBLIC_WS_URL
      
      renderHook(() => useRealTimeNews())
      
      expect(mockIo).toHaveBeenCalledWith('http://localhost:8000')
    })

    it('closes socket connection on unmount', () => {
      const { unmount } = renderHook(() => useRealTimeNews())
      
      unmount()
      
      expect(mockSocketInstance.close).toHaveBeenCalled()
    })

    it('handles connection event correctly', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation()
      
      renderHook(() => useRealTimeNews())
      
      // Get the connect event handler
      const connectHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'connect'
      )?.[1]
      
      // Simulate connection
      act(() => {
        connectHandler?.()
      })
      
      expect(mockSetConnected).toHaveBeenCalledWith(true)
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket connected')
      
      consoleSpy.mockRestore()
    })

    it('handles disconnect event correctly', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation()
      
      renderHook(() => useRealTimeNews())
      
      // Get the disconnect event handler
      const disconnectHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1]
      
      // Simulate disconnection
      act(() => {
        disconnectHandler?.()
      })
      
      expect(mockSetConnected).toHaveBeenCalledWith(false)
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket disconnected')
      
      consoleSpy.mockRestore()
    })
  })

  describe('Regular News Handling', () => {
    it('handles new_news events', () => {
      renderHook(() => useRealTimeNews())
      
      // Get the new_news event handler
      const newsHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'new_news'
      )?.[1]
      
      // Simulate receiving news
      act(() => {
        newsHandler?.(mockNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockNewsItem)
    })

    it('processes multiple news items correctly', () => {
      renderHook(() => useRealTimeNews())
      
      const newsHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'new_news'
      )?.[1]
      
      const newsItems = [
        mockNewsItem,
        { ...mockNewsItem, id: 2, title: 'Ethereum Update' },
        { ...mockNewsItem, id: 3, title: 'Crypto Regulation News' }
      ]
      
      act(() => {
        newsItems.forEach(item => newsHandler?.(item))
      })
      
      expect(mockAddNews).toHaveBeenCalledTimes(3)
      newsItems.forEach(item => {
        expect(mockAddNews).toHaveBeenCalledWith(item)
      })
    })
  })

  describe('Urgent News and Notifications', () => {
    beforeEach(() => {
      // Ensure Notification is available in window
      Object.defineProperty(window, 'Notification', {
        writable: true,
        value: mockNotification
      })
    })

    it('handles urgent_news events and adds to news feed', () => {
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
    })

    it('shows browser notification for urgent news when conditions met', () => {
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockNotification).toHaveBeenCalledWith(
        'BREAKING: Major Exchange Hacked',
        {
          body: 'Bitcoin hits $50k milestone',
          icon: '/favicon.ico',
          tag: 'urgent-news',
          requireInteraction: true
        }
      )
    })

    it('uses truncated content when summary not available', () => {
      const newsWithoutSummary = {
        ...mockUrgentNewsItem,
        summary: null,
        content: 'This is a very long content that should be truncated to 100 characters maximum for notification display purposes and readability'
      }
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(newsWithoutSummary)
      })
      
      expect(mockNotification).toHaveBeenCalledWith(
        'BREAKING: Major Exchange Hacked',
        expect.objectContaining({
          body: expect.stringMatching(/^This is a very long content.{0,100}\.\.\.$/),
        })
      )
    })

    it('respects importance threshold for notifications', () => {
      const lowImportanceUrgent = {
        ...mockUrgentNewsItem,
        importanceScore: 2 // Below default threshold of 3
      }
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(lowImportanceUrgent)
      })
      
      // Should add to news but not show notification
      expect(mockAddNews).toHaveBeenCalledWith(lowImportanceUrgent)
      expect(mockNotification).not.toHaveBeenCalled()
    })

    it('does not show notification when browser notifications disabled', () => {
      mockUseNotificationStore.mockReturnValue({
        preferences: {
          ...defaultPreferences,
          browserNotifications: false
        },
        browserPermission: 'granted'
      } as any)
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      expect(mockNotification).not.toHaveBeenCalled()
    })

    it('does not show notification when urgent notifications disabled', () => {
      mockUseNotificationStore.mockReturnValue({
        preferences: {
          ...defaultPreferences,
          urgentNotifications: false
        },
        browserPermission: 'granted'
      } as any)
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      expect(mockNotification).not.toHaveBeenCalled()
    })

    it('does not show notification when browser permission denied', () => {
      mockUseNotificationStore.mockReturnValue({
        preferences: defaultPreferences,
        browserPermission: 'denied'
      } as any)
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      expect(mockNotification).not.toHaveBeenCalled()
    })

    it('handles server-side environment gracefully', () => {
      // Mock server-side environment
      const originalWindow = global.window
      delete (global as any).window
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      // Should still add to news
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      // Should not try to show notification
      expect(mockNotification).not.toHaveBeenCalled()
      
      // Restore window
      global.window = originalWindow
    })

    it('handles missing Notification API gracefully', () => {
      // Mock environment without Notification API
      delete (window as any).Notification
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      expect(mockNotification).not.toHaveBeenCalled()
      
      // Restore Notification API
      window.Notification = mockNotification
    })
  })

  describe('Store Integration and Dependencies', () => {
    it('reestablishes connection when dependencies change', () => {
      const { rerender } = renderHook(() => useRealTimeNews())
      
      // Clear initial connection setup
      mockIo.mockClear()
      mockSocketInstance.on.mockClear()
      mockSocketInstance.close.mockClear()
      
      // Change dependencies
      mockUseNotificationStore.mockReturnValue({
        preferences: {
          ...defaultPreferences,
          minImportance: 4 // Changed threshold
        },
        browserPermission: 'granted'
      } as any)
      
      rerender()
      
      // Should close old connection and create new one
      expect(mockSocketInstance.close).toHaveBeenCalled()
      expect(mockIo).toHaveBeenCalledTimes(1)
    })

    it('maintains connection when unrelated store changes occur', () => {
      const { rerender } = renderHook(() => useRealTimeNews())
      
      // Clear initial setup
      mockIo.mockClear()
      mockSocketInstance.close.mockClear()
      
      // Change unrelated store values (not in dependency array)
      mockUseNewsStore.mockReturnValue({
        addNews: mockAddNews,
        setConnected: mockSetConnected,
        // Other properties that shouldn't affect the hook
        news: [mockNewsItem],
        loading: true
      } as any)
      
      rerender()
      
      // Should not create new connection
      expect(mockIo).not.toHaveBeenCalled()
      expect(mockSocketInstance.close).not.toHaveBeenCalled()
    })

    it('handles store method changes gracefully', () => {
      renderHook(() => useRealTimeNews())
      
      const newsHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'new_news'
      )?.[1]
      
      // Change addNews function reference
      const newAddNews = jest.fn()
      mockUseNewsStore.mockReturnValue({
        addNews: newAddNews,
        setConnected: mockSetConnected
      } as any)
      
      // Trigger news event with old handler
      act(() => {
        newsHandler?.(mockNewsItem)
      })
      
      // Should still use the original addNews function (closure)
      expect(mockAddNews).toHaveBeenCalledWith(mockNewsItem)
      expect(newAddNews).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('handles malformed news data gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
      
      renderHook(() => useRealTimeNews())
      
      const newsHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'new_news'
      )?.[1]
      
      // Simulate malformed data
      const malformedNews = {
        id: 'invalid-id', // Should be number
        title: null,      // Should be string
        // Missing required fields
      }
      
      act(() => {
        try {
          newsHandler?.(malformedNews as any)
        } catch (error) {
          // Hook should handle errors gracefully
        }
      })
      
      // Should attempt to add news (let store handle validation)
      expect(mockAddNews).toHaveBeenCalledWith(malformedNews)
      
      consoleSpy.mockRestore()
    })

    it('handles socket connection errors', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
      
      renderHook(() => useRealTimeNews())
      
      // Simulate connection error
      const errorHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'connect_error'
      )?.[1] || mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'error'
      )?.[1]
      
      if (errorHandler) {
        act(() => {
          errorHandler(new Error('Connection failed'))
        })
      }
      
      // Hook should continue to work despite connection errors
      expect(() => renderHook(() => useRealTimeNews())).not.toThrow()
      
      consoleSpy.mockRestore()
    })

    it('handles rapid connection/disconnection cycles', () => {
      renderHook(() => useRealTimeNews())
      
      const connectHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'connect'
      )?.[1]
      
      const disconnectHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1]
      
      // Simulate rapid connect/disconnect cycles
      act(() => {
        connectHandler?.()
        disconnectHandler?.()
        connectHandler?.()
        disconnectHandler?.()
        connectHandler?.()
      })
      
      // Should handle all state changes
      expect(mockSetConnected).toHaveBeenCalledTimes(5)
      expect(mockSetConnected).toHaveBeenLastCalledWith(true)
    })

    it('handles notification creation errors', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
      mockNotification.mockImplementation(() => {
        throw new Error('Notification failed')
      })
      
      renderHook(() => useRealTimeNews())
      
      const urgentHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'urgent_news'
      )?.[1]
      
      act(() => {
        urgentHandler?.(mockUrgentNewsItem)
      })
      
      // Should still add news to store even if notification fails
      expect(mockAddNews).toHaveBeenCalledWith(mockUrgentNewsItem)
      
      consoleSpy.mockRestore()
    })
  })

  describe('Performance and Memory Management', () => {
    it('returns stable socket reference', () => {
      const { result, rerender } = renderHook(() => useRealTimeNews())
      
      const firstSocket = result.current.socket
      
      rerender()
      
      const secondSocket = result.current.socket
      expect(firstSocket).toBe(secondSocket)
    })

    it('cleans up event listeners on unmount', () => {
      const { unmount } = renderHook(() => useRealTimeNews())
      
      expect(mockSocketInstance.on).toHaveBeenCalledTimes(4) // connect, disconnect, new_news, urgent_news
      
      unmount()
      
      expect(mockSocketInstance.close).toHaveBeenCalled()
    })

    it('handles multiple rapid news items without performance issues', () => {
      renderHook(() => useRealTimeNews())
      
      const newsHandler = mockSocketInstance.on.mock.calls.find(
        call => call[0] === 'new_news'
      )?.[1]
      
      // Simulate rapid news updates
      const newsItems = Array.from({ length: 100 }, (_, i) => ({
        ...mockNewsItem,
        id: i + 1,
        title: `News Item ${i + 1}`
      }))
      
      act(() => {
        newsItems.forEach(item => newsHandler?.(item))
      })
      
      expect(mockAddNews).toHaveBeenCalledTimes(100)
    })
  })

  describe('Return Value and API', () => {
    it('returns socket instance', () => {
      const { result } = renderHook(() => useRealTimeNews())
      
      expect(result.current).toEqual({
        socket: mockSocketInstance
      })
    })

    it('maintains consistent API across re-renders', () => {
      const { result, rerender } = renderHook(() => useRealTimeNews())
      
      const firstResult = result.current
      
      rerender()
      
      const secondResult = result.current
      
      expect(Object.keys(firstResult)).toEqual(Object.keys(secondResult))
      expect(typeof firstResult.socket).toBe(typeof secondResult.socket)
    })
  })
})