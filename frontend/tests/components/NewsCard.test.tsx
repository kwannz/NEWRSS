import { render, screen, fireEvent } from '@testing-library/react'
import { NewsCard } from '@/components/NewsCard'
import { NewsItem } from '@/types/news'

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
  keyTokens: ['BTC', 'Bitcoin', 'ATH'],
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

describe('NewsCard', () => {
  const mockOnRead = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders news item correctly', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    expect(screen.getByText('Bitcoin Reaches New High')).toBeInTheDocument()
    expect(screen.getByText('Bitcoin hits $50k milestone')).toBeInTheDocument()
    expect(screen.getByText('CoinDesk')).toBeInTheDocument()
    expect(screen.getByText('bitcoin')).toBeInTheDocument()
  })

  it('handles urgent news styling', () => {
    render(<NewsCard news={mockUrgentNewsItem} onRead={mockOnRead} />)
    
    const urgentBadge = screen.getByText('CoinDesk')
    expect(urgentBadge).toHaveClass('badge-destructive')
  })

  it('handles non-urgent news styling', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    const normalBadge = screen.getByText('CoinDesk')
    expect(normalBadge).toHaveClass('badge-secondary')
  })

  it('displays importance score correctly', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    const importanceContainer = screen.getByText('重要度:').closest('div')
    const dots = importanceContainer?.querySelectorAll('.w-2.h-2.rounded-full')
    
    expect(dots).toHaveLength(5) // 总共5个点
    
    const redDots = Array.from(dots || []).filter(dot => 
      dot.classList.contains('bg-red-500')
    )
    const grayDots = Array.from(dots || []).filter(dot => 
      dot.classList.contains('bg-gray-200')
    )
    
    expect(redDots).toHaveLength(4) // importanceScore = 4
    expect(grayDots).toHaveLength(1) // 5 - 4 = 1
  })

  it('displays key tokens', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    expect(screen.getByText('BTC')).toBeInTheDocument()
    expect(screen.getByText('Bitcoin')).toBeInTheDocument()
    expect(screen.getByText('ATH')).toBeInTheDocument()
  })

  it('limits key tokens to 3', () => {
    const newsWithManyTokens = {
      ...mockNewsItem,
      keyTokens: ['BTC', 'ETH', 'XRP', 'ADA', 'SOL', 'DOT']
    }
    
    render(<NewsCard news={newsWithManyTokens} onRead={mockOnRead} />)
    
    expect(screen.getByText('BTC')).toBeInTheDocument()
    expect(screen.getByText('ETH')).toBeInTheDocument()
    expect(screen.getByText('XRP')).toBeInTheDocument()
    expect(screen.queryByText('ADA')).not.toBeInTheDocument()
    expect(screen.queryByText('SOL')).not.toBeInTheDocument()
  })

  it('handles missing key tokens', () => {
    const newsWithoutTokens = {
      ...mockNewsItem,
      keyTokens: null
    }
    
    render(<NewsCard news={newsWithoutTokens} onRead={mockOnRead} />)
    
    // 应该不显示key tokens区域
    expect(screen.queryByText('BTC')).not.toBeInTheDocument()
  })

  it('handles missing category with default', () => {
    const newsWithoutCategory = {
      ...mockNewsItem,
      category: null
    }
    
    render(<NewsCard news={newsWithoutCategory} onRead={mockOnRead} />)
    
    expect(screen.getByText('general')).toBeInTheDocument()
  })

  it('uses content when summary is missing', () => {
    const newsWithoutSummary = {
      ...mockNewsItem,
      summary: null
    }
    
    render(<NewsCard news={newsWithoutSummary} onRead={mockOnRead} />)
    
    expect(screen.getByText(/Bitcoin has reached a new all-time high/)).toBeInTheDocument()
  })

  it('calls onRead when clicked', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    const card = screen.getByRole('article') || screen.getByText('Bitcoin Reaches New High').closest('[data-testid]') || screen.getByText('Bitcoin Reaches New High').closest('div')
    
    fireEvent.click(card)
    
    expect(mockOnRead).toHaveBeenCalledWith(1)
    expect(mockOnRead).toHaveBeenCalledTimes(1)
  })

  it('has hover effects', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    const card = screen.getByText('Bitcoin Reaches New High').closest('div')
    expect(card).toHaveClass('hover:shadow-lg', 'transition-shadow', 'cursor-pointer')
  })

  it('displays formatted time', () => {
    render(<NewsCard news={mockNewsItem} onRead={mockOnRead} />)
    
    // 应该显示格式化的时间，但具体格式取决于formatTimeAgo函数
    const timeElement = screen.getByText(/ago|分钟前|小时前|天前/)
    expect(timeElement).toBeInTheDocument()
  })
}