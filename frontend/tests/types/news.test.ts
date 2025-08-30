import { NewsItem, NewsFilter, NewsSource, User } from '@/types/news'

describe('News Types', () => {
  describe('NewsItem', () => {
    it('should have correct required fields', () => {
      const newsItem: NewsItem = {
        id: 1,
        title: 'Test News',
        content: 'Test content',
        url: 'https://example.com',
        source: 'TestSource',
        publishedAt: '2024-01-01T12:00:00Z',
        importanceScore: 3,
        isUrgent: false,
        marketImpact: 2,
        isProcessed: true,
        createdAt: '2024-01-01T12:00:00Z',
        updatedAt: '2024-01-01T12:00:00Z'
      }
      
      expect(newsItem.id).toBe(1)
      expect(newsItem.title).toBe('Test News')
      expect(newsItem.content).toBe('Test content')
      expect(newsItem.isUrgent).toBe(false)
      expect(newsItem.importanceScore).toBe(3)
    })

    it('should have correct optional fields', () => {
      const newsItem: NewsItem = {
        id: 1,
        title: 'Test News',
        content: 'Test content',
        summary: 'Test summary',
        url: 'https://example.com',
        source: 'TestSource',
        category: 'bitcoin',
        publishedAt: '2024-01-01T12:00:00Z',
        importanceScore: 3,
        isUrgent: false,
        marketImpact: 2,
        sentimentScore: 0.8,
        keyTokens: ['BTC', 'Bitcoin'],
        keyPrices: ['$50000'],
        isProcessed: true,
        createdAt: '2024-01-01T12:00:00Z',
        updatedAt: '2024-01-01T12:00:00Z'
      }
      
      expect(newsItem.summary).toBe('Test summary')
      expect(newsItem.category).toBe('bitcoin')
      expect(newsItem.sentimentScore).toBe(0.8)
      expect(newsItem.keyTokens).toEqual(['BTC', 'Bitcoin'])
      expect(newsItem.keyPrices).toEqual(['$50000'])
    })
  })

  describe('NewsFilter', () => {
    it('should allow all optional filters', () => {
      const filter: NewsFilter = {
        category: 'bitcoin',
        source: 'CoinDesk',
        timeRange: 'day',
        importance: 3,
        urgent: true
      }
      
      expect(filter.category).toBe('bitcoin')
      expect(filter.source).toBe('CoinDesk')
      expect(filter.timeRange).toBe('day')
      expect(filter.importance).toBe(3)
      expect(filter.urgent).toBe(true)
    })

    it('should allow empty filter', () => {
      const filter: NewsFilter = {}
      
      expect(filter.category).toBeUndefined()
      expect(filter.source).toBeUndefined()
      expect(filter.timeRange).toBeUndefined()
      expect(filter.importance).toBeUndefined()
      expect(filter.urgent).toBeUndefined()
    })

    it('should accept valid timeRange values', () => {
      const filters: NewsFilter[] = [
        { timeRange: 'hour' },
        { timeRange: 'day' },
        { timeRange: 'week' }
      ]
      
      filters.forEach(filter => {
        expect(['hour', 'day', 'week']).toContain(filter.timeRange)
      })
    })
  })

  describe('NewsSource', () => {
    it('should have correct required fields', () => {
      const newsSource: NewsSource = {
        id: 1,
        name: 'CoinDesk',
        url: 'https://feeds.coindesk.com/all',
        sourceType: 'rss',
        isActive: true,
        fetchInterval: 30,
        priority: 1
      }
      
      expect(newsSource.id).toBe(1)
      expect(newsSource.name).toBe('CoinDesk')
      expect(newsSource.url).toBe('https://feeds.coindesk.com/all')
      expect(newsSource.sourceType).toBe('rss')
      expect(newsSource.isActive).toBe(true)
      expect(newsSource.fetchInterval).toBe(30)
      expect(newsSource.priority).toBe(1)
    })

    it('should have correct optional fields', () => {
      const newsSource: NewsSource = {
        id: 1,
        name: 'CoinDesk',
        url: 'https://feeds.coindesk.com/all',
        sourceType: 'rss',
        category: 'news',
        isActive: true,
        fetchInterval: 30,
        lastFetched: '2024-01-01T12:00:00Z',
        priority: 1
      }
      
      expect(newsSource.category).toBe('news')
      expect(newsSource.lastFetched).toBe('2024-01-01T12:00:00Z')
    })
  })

  describe('User', () => {
    it('should have correct required fields', () => {
      const user: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        isActive: true,
        urgentNotifications: true,
        dailyDigest: false
      }
      
      expect(user.id).toBe(1)
      expect(user.username).toBe('testuser')
      expect(user.email).toBe('test@example.com')
      expect(user.isActive).toBe(true)
      expect(user.urgentNotifications).toBe(true)
      expect(user.dailyDigest).toBe(false)
    })

    it('should have correct optional Telegram fields', () => {
      const user: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        isActive: true,
        telegramId: '123456789',
        telegramUsername: 'testuser_tg',
        urgentNotifications: true,
        dailyDigest: false
      }
      
      expect(user.telegramId).toBe('123456789')
      expect(user.telegramUsername).toBe('testuser_tg')
    })
  })
})