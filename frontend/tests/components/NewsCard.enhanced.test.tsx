import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { NewsCard } from '@/components/NewsCard'
import { NewsItem } from '@/types/news'
import { jest } from '@jest/globals'

// Mock the utility functions
jest.mock('@/lib/utils', () => ({
  ...jest.requireActual('@/lib/utils'),
  formatTimeAgo: jest.fn((date: string) => {
    const now = new Date()
    const past = new Date(date)
    const diffMs = now.getTime() - past.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHours < 1) return '刚刚'
    if (diffHours < 24) return `${diffHours}小时前`
    return `${Math.floor(diffHours / 24)}天前`
  }),
  cn: jest.fn((...classes) => classes.filter(Boolean).join(' '))
}))

const baseNewsItem: NewsItem = {
  id: 1,
  title: 'Bitcoin Reaches New High',
  content: 'Bitcoin has reached a new all-time high of $50,000, marking a significant milestone for the cryptocurrency.',
  summary: 'Bitcoin hits $50k milestone',
  url: 'https://example.com/bitcoin-news',
  source: 'CoinDesk',
  category: 'bitcoin',
  publishedAt: '2024-01-01T12:00:00Z',
  importanceScore: 4,
  isUrgent: false,
  marketImpact: 3,
  sentimentScore: 0.8,
  keyTokens: ['BTC', 'Bitcoin', 'ATH'],
  keyPrices: ['$50,000'],
  isProcessed: true,
  createdAt: '2024-01-01T12:00:00Z',
  updatedAt: '2024-01-01T12:00:00Z'
}

describe('NewsCard - Enhanced Tests', () => {
  const mockOnRead = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering and Content', () => {
    it('renders all essential elements', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      expect(screen.getByText('Bitcoin Reaches New High')).toBeInTheDocument()
      expect(screen.getByText('Bitcoin hits $50k milestone')).toBeInTheDocument()
      expect(screen.getByText('CoinDesk')).toBeInTheDocument()
      expect(screen.getByText('bitcoin')).toBeInTheDocument()
      expect(screen.getByText('重要度:')).toBeInTheDocument()
    })

    it('handles very long titles with proper truncation', () => {
      const longTitleNews = {
        ...baseNewsItem,
        title: 'This is an extremely long title that should be truncated properly when rendered in the news card component to prevent layout issues and maintain readability'
      }
      
      render(<NewsCard news={longTitleNews} onRead={mockOnRead} />)
      
      const titleElement = screen.getByText(/This is an extremely long title/)
      expect(titleElement).toHaveClass('line-clamp-2')
    })

    it('handles very long content with proper truncation', () => {
      const longContentNews = {
        ...baseNewsItem,
        summary: null,
        content: 'This is an extremely long content that goes on and on and on and should be properly truncated when displayed in the news card summary section to maintain proper layout and readability across different screen sizes and device types.'
      }
      
      render(<NewsCard news={longContentNews} onRead={mockOnRead} />)
      
      const contentElement = screen.getByText(/This is an extremely long content/)
      expect(contentElement).toHaveClass('line-clamp-3')
    })

    it('prefers summary over content when both exist', () => {
      const newsWithBoth = {
        ...baseNewsItem,
        summary: 'Short summary',
        content: 'Much longer detailed content that should not be shown'
      }
      
      render(<NewsCard news={newsWithBoth} onRead={mockOnRead} />)
      
      expect(screen.getByText('Short summary')).toBeInTheDocument()
      expect(screen.queryByText('Much longer detailed content')).not.toBeInTheDocument()
    })
  })

  describe('Urgency and Styling', () => {
    it('applies urgent styling correctly', () => {
      const urgentNews = {
        ...baseNewsItem,
        isUrgent: true,
        title: 'BREAKING: Critical Security Alert'
      }
      
      render(<NewsCard news={urgentNews} onRead={mockOnRead} />)
      
      const sourceBadge = screen.getByText('CoinDesk')
      expect(sourceBadge).toHaveClass('badge-destructive')
    })

    it('applies normal styling for non-urgent news', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      const sourceBadge = screen.getByText('CoinDesk')
      expect(sourceBadge).toHaveClass('badge-secondary')
    })

    it('maintains hover effects for interactivity', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      const card = screen.getByText('Bitcoin Reaches New High').closest('div')
      expect(card).toHaveClass('hover:shadow-lg', 'transition-shadow', 'cursor-pointer')
    })
  })

  describe('Importance Score Display', () => {
    it('displays correct importance score with filled/empty indicators', () => {
      const scoreTestCases = [
        { score: 1, filled: 1, empty: 4 },
        { score: 3, filled: 3, empty: 2 },
        { score: 5, filled: 5, empty: 0 },
        { score: 0, filled: 0, empty: 5 }
      ]

      scoreTestCases.forEach(({ score, filled, empty }) => {
        const testNews = { ...baseNewsItem, importanceScore: score }
        const { unmount } = render(<NewsCard news={testNews} onRead={mockOnRead} />)
        
        const importanceContainer = screen.getByText('重要度:').closest('div')
        const dots = importanceContainer?.querySelectorAll('.w-2.h-2.rounded-full')
        
        expect(dots).toHaveLength(5)
        
        const redDots = Array.from(dots || []).filter(dot => 
          dot.classList.contains('bg-red-500')
        )
        const grayDots = Array.from(dots || []).filter(dot => 
          dot.classList.contains('bg-gray-200')
        )
        
        expect(redDots).toHaveLength(filled)
        expect(grayDots).toHaveLength(empty)
        
        unmount()
      })
    })

    it('handles edge case importance scores gracefully', () => {
      const edgeCaseNews = {
        ...baseNewsItem,
        importanceScore: -1 // Invalid score
      }
      
      render(<NewsCard news={edgeCaseNews} onRead={mockOnRead} />)
      
      const importanceContainer = screen.getByText('重要度:').closest('div')
      const dots = importanceContainer?.querySelectorAll('.w-2.h-2.rounded-full')
      expect(dots).toHaveLength(5) // Should still render 5 dots
    })
  })

  describe('Key Tokens Display', () => {
    it('displays up to 3 key tokens', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      expect(screen.getByText('BTC')).toBeInTheDocument()
      expect(screen.getByText('Bitcoin')).toBeInTheDocument()
      expect(screen.getByText('ATH')).toBeInTheDocument()
    })

    it('limits display to first 3 tokens when more exist', () => {
      const newsWithManyTokens = {
        ...baseNewsItem,
        keyTokens: ['BTC', 'ETH', 'XRP', 'ADA', 'SOL', 'DOT', 'MATIC']
      }
      
      render(<NewsCard news={newsWithManyTokens} onRead={mockOnRead} />)
      
      // First 3 should be visible
      expect(screen.getByText('BTC')).toBeInTheDocument()
      expect(screen.getByText('ETH')).toBeInTheDocument()
      expect(screen.getByText('XRP')).toBeInTheDocument()
      
      // Rest should not be visible
      expect(screen.queryByText('ADA')).not.toBeInTheDocument()
      expect(screen.queryByText('SOL')).not.toBeInTheDocument()
      expect(screen.queryByText('DOT')).not.toBeInTheDocument()
      expect(screen.queryByText('MATIC')).not.toBeInTheDocument()
    })

    it('handles empty key tokens array', () => {
      const newsWithEmptyTokens = {
        ...baseNewsItem,
        keyTokens: []
      }
      
      render(<NewsCard news={newsWithEmptyTokens} onRead={mockOnRead} />)
      
      // Key tokens section should not be rendered
      expect(screen.queryByText('BTC')).not.toBeInTheDocument()
    })

    it('handles null key tokens', () => {
      const newsWithNullTokens = {
        ...baseNewsItem,
        keyTokens: null
      }
      
      render(<NewsCard news={newsWithNullTokens} onRead={mockOnRead} />)
      
      // Key tokens section should not be rendered
      expect(screen.queryByText('BTC')).not.toBeInTheDocument()
    })

    it('handles undefined key tokens', () => {
      const newsWithUndefinedTokens = {
        ...baseNewsItem,
        keyTokens: undefined
      }
      
      render(<NewsCard news={newsWithUndefinedTokens} onRead={mockOnRead} />)
      
      // Key tokens section should not be rendered
      expect(screen.queryByText('BTC')).not.toBeInTheDocument()
    })
  })

  describe('Category Handling', () => {
    it('displays provided category', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      expect(screen.getByText('bitcoin')).toBeInTheDocument()
    })

    it('falls back to "general" for null category', () => {
      const newsWithNullCategory = {
        ...baseNewsItem,
        category: null
      }
      
      render(<NewsCard news={newsWithNullCategory} onRead={mockOnRead} />)
      
      expect(screen.getByText('general')).toBeInTheDocument()
    })

    it('falls back to "general" for undefined category', () => {
      const newsWithUndefinedCategory = {
        ...baseNewsItem,
        category: undefined
      }
      
      render(<NewsCard news={newsWithUndefinedCategory} onRead={mockOnRead} />)
      
      expect(screen.getByText('general')).toBeInTheDocument()
    })

    it('falls back to "general" for empty category', () => {
      const newsWithEmptyCategory = {
        ...baseNewsItem,
        category: ''
      }
      
      render(<NewsCard news={newsWithEmptyCategory} onRead={mockOnRead} />)
      
      expect(screen.getByText('general')).toBeInTheDocument()
    })
  })

  describe('Time Display', () => {
    it('displays formatted time using formatTimeAgo', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      // Based on our mocked formatTimeAgo function
      expect(screen.getByText(/小时前|天前|刚刚/)).toBeInTheDocument()
    })

    it('handles invalid date gracefully', () => {
      const newsWithInvalidDate = {
        ...baseNewsItem,
        publishedAt: 'invalid-date'
      }
      
      render(<NewsCard news={newsWithInvalidDate} onRead={mockOnRead} />)
      
      // Should still render without crashing
      expect(screen.getByText('Bitcoin Reaches New High')).toBeInTheDocument()
    })
  })

  describe('Interaction Handling', () => {
    it('calls onRead with correct id on click', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      const card = screen.getByText('Bitcoin Reaches New High').closest('[role="button"], div')
      fireEvent.click(card!)
      
      expect(mockOnRead).toHaveBeenCalledWith(1)
      expect(mockOnRead).toHaveBeenCalledTimes(1)
    })

    it('handles multiple rapid clicks correctly', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      const card = screen.getByText('Bitcoin Reaches New High').closest('div')
      
      fireEvent.click(card!)
      fireEvent.click(card!)
      fireEvent.click(card!)
      
      expect(mockOnRead).toHaveBeenCalledTimes(3)
    })

    it('supports keyboard navigation', async () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      const card = screen.getByText('Bitcoin Reaches New High').closest('div')
      
      // Focus the card
      card?.focus()
      
      // Press Enter
      fireEvent.keyDown(card!, { key: 'Enter', code: 'Enter' })
      
      // Should not call onRead since we haven't implemented keyboard support
      // This test documents current behavior and will need updating if keyboard support is added
      expect(mockOnRead).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic structure', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      // Check for proper heading structure
      const title = screen.getByText('Bitcoin Reaches New High')
      expect(title.tagName).toBe('H3')
      
      // Check for interactive element
      const card = title.closest('div')
      expect(card).toHaveClass('cursor-pointer')
    })

    it('provides meaningful text alternatives', () => {
      render(<NewsCard news={baseNewsItem} onRead={mockOnRead} />)
      
      // Importance score should have descriptive text
      expect(screen.getByText('重要度:')).toBeInTheDocument()
      
      // Source and category should be clearly labeled
      expect(screen.getByText('CoinDesk')).toBeInTheDocument()
      expect(screen.getByText('bitcoin')).toBeInTheDocument()
    })

    it('maintains proper color contrast for urgent badges', () => {
      const urgentNews = { ...baseNewsItem, isUrgent: true }
      render(<NewsCard news={urgentNews} onRead={mockOnRead} />)
      
      const urgentBadge = screen.getByText('CoinDesk')
      expect(urgentBadge).toHaveClass('badge-destructive')
      // Note: In a real implementation, we'd test actual color contrast ratios
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('handles missing required fields gracefully', () => {
      const incompleteNews = {
        id: 999,
        title: 'Test Title',
        content: 'Test Content',
        url: 'https://test.com',
        source: 'Test Source',
        publishedAt: '2024-01-01T12:00:00Z',
        importanceScore: 1,
        isUrgent: false,
        // Missing optional fields
        summary: null,
        category: null,
        keyTokens: null
      } as NewsItem
      
      render(<NewsCard news={incompleteNews} onRead={mockOnRead} />)
      
      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test Content')).toBeInTheDocument()
      expect(screen.getByText('general')).toBeInTheDocument() // Default category
    })

    it('handles extremely high importance scores', () => {
      const highScoreNews = {
        ...baseNewsItem,
        importanceScore: 999999
      }
      
      render(<NewsCard news={highScoreNews} onRead={mockOnRead} />)
      
      // Should still render 5 dots max
      const importanceContainer = screen.getByText('重要度:').closest('div')
      const dots = importanceContainer?.querySelectorAll('.w-2.h-2.rounded-full')
      expect(dots).toHaveLength(5)
      
      // All should be filled
      const redDots = Array.from(dots || []).filter(dot => 
        dot.classList.contains('bg-red-500')
      )
      expect(redDots).toHaveLength(5)
    })

    it('handles special characters in content', () => {
      const specialCharNews = {
        ...baseNewsItem,
        title: 'Bitcoin & Ethereum: The Future of Crypto 🚀💰',
        summary: 'Special chars: @#$%^&*()[]{}|\\:";\'<>?,./~`',
        keyTokens: ['BTC', 'ETH', '$', '€', '¥']
      }
      
      render(<NewsCard news={specialCharNews} onRead={mockOnRead} />)
      
      expect(screen.getByText(/Bitcoin & Ethereum/)).toBeInTheDocument()
      expect(screen.getByText(/Special chars:/)).toBeInTheDocument()
      expect(screen.getByText('$')).toBeInTheDocument()
    })

    it('handles XSS attempts in content', () => {
      const xssNews = {
        ...baseNewsItem,
        title: '<script>alert("XSS")</script>Safe Title',
        summary: '<img src="x" onerror="alert(\'XSS\')" />Safe summary',
        keyTokens: ['<script>', 'alert()', 'safe']
      }
      
      render(<NewsCard news={xssNews} onRead={mockOnRead} />)
      
      // React should automatically escape the content
      expect(screen.getByText(/Safe Title/)).toBeInTheDocument()
      expect(screen.getByText(/Safe summary/)).toBeInTheDocument()
      
      // Script tags should not be executed
      expect(document.querySelectorAll('script')).toHaveLength(0)
    })
  })
})