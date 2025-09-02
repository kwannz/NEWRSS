"use client"

import { useState, useCallback, useEffect } from 'react'
import { Header } from '@/components/layout/Header'
import { NewsFilterComponent } from '@/components/filters/NewsFilter'
import { NotificationSettings } from '@/components/settings/NotificationSettings'
import { NewsCard } from '@/components/NewsCard'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useRealTimeNews } from '@/hooks/useRealTimeNews'
import { useNewsStore, useAuthStore } from '@/lib/store'
import { apiClient } from '@/lib/api'
import { NewsItem } from '@/types/news'
import { RefreshCw, AlertTriangle } from 'lucide-react'
import { getErrorMessage } from '@/lib/utils'

export function Dashboard() {
  const [showFilters, setShowFilters] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [initialNews, setInitialNews] = useState<NewsItem[]>([])
  const [loadingInitial, setLoadingInitial] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const { news, filters, setNews, setError: setNewsError, setLoading } = useNewsStore()
  const { isAuthenticated } = useAuthStore()
  const { socket } = useRealTimeNews()

  // Load initial news data
  const loadInitialNews = useCallback(async () => {
    setLoadingInitial(true)
    setError(null)
    try {
      const params = {
        limit: 50,
        ...filters
      }
      const newsData = await apiClient.getNews(params)
      setInitialNews(newsData)
      setNews(newsData)
    } catch (err) {
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      setNewsError(errorMessage)
    } finally {
      setLoadingInitial(false)
      setLoading(false)
    }
  }, [filters, setNews, setNewsError, setLoading])

  // Load news on mount and when filters change
  useEffect(() => {
    loadInitialNews()
  }, [loadInitialNews])

  // Handle news item read action
  const handleNewsRead = useCallback((id: number) => {
    // TODO: Implement read status tracking
    console.log(`Marking news item ${id} as read`)
    
    // If authenticated, could send to backend
    if (isAuthenticated) {
      // apiClient.markAsRead(id)
    }
  }, [isAuthenticated])

  // Handle manual refresh
  const handleRefresh = useCallback(() => {
    loadInitialNews()
  }, [loadInitialNews])

  const handleOpenFilters = () => setShowFilters(true)
  const handleCloseFilters = () => setShowFilters(false)
  const handleOpenSettings = () => setShowSettings(true)
  const handleCloseSettings = () => setShowSettings(false)
  const handleOpenNotifications = () => setShowNotifications(true)
  const handleCloseNotifications = () => setShowNotifications(false)

  // Combine initial news with real-time updates, removing duplicates
  const displayNews = [...news]
  // Sort by published date, most recent first
  displayNews.sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime())

  return (
    <div className="min-h-screen bg-background">
      <Header 
        onOpenFilters={handleOpenFilters}
        onOpenSettings={handleOpenSettings}
        onOpenNotifications={handleOpenNotifications}
      />
      
      <main className="container mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">
                {isAuthenticated ? '个人新闻源' : '实时加密新闻'}
              </h2>
              <p className="text-muted-foreground">
                {isAuthenticated 
                  ? '为您精选的个性化加密货币资讯' 
                  : '最新的加密货币行业动态和市场资讯'
                }
              </p>
            </div>
            <Button 
              variant="outline" 
              onClick={handleRefresh} 
              disabled={loadingInitial}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loadingInitial ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                加载新闻时出错: {error}
                <Button 
                  variant="link" 
                  className="p-0 ml-2 h-auto" 
                  onClick={handleRefresh}
                >
                  重试
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Loading State */}
          {loadingInitial && displayNews.length === 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="bg-muted rounded-lg h-48"></div>
                </div>
              ))}
            </div>
          )}

          {/* News Grid */}
          {displayNews.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {displayNews.map((newsItem) => (
                <NewsCard 
                  key={newsItem.id} 
                  news={newsItem} 
                  onRead={handleNewsRead} 
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!loadingInitial && displayNews.length === 0 && (
            <div className="text-center py-12">
              <div className="mx-auto max-w-md">
                <h3 className="text-lg font-semibold mb-2">暂无新闻</h3>
                <p className="text-muted-foreground mb-4">
                  暂时没有找到符合条件的新闻，请稍后再试或调整筛选条件。
                </p>
                <div className="space-x-2">
                  <Button onClick={handleRefresh}>
                    刷新
                  </Button>
                  <Button variant="outline" onClick={handleOpenFilters}>
                    调整筛选
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Filters Modal */}
      <Dialog open={showFilters} onOpenChange={setShowFilters}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogTitle className="sr-only">新闻筛选</DialogTitle>
          <NewsFilterComponent onClose={handleCloseFilters} />
        </DialogContent>
      </Dialog>

      {/* Settings Modal */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogTitle className="sr-only">设置</DialogTitle>
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-4">设置</h2>
            <p className="text-muted-foreground">设置页面尚未完全开发</p>
            <Button 
              className="mt-4" 
              onClick={handleCloseSettings}
            >
              关闭
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Notification Settings Modal */}
      <Dialog open={showNotifications} onOpenChange={setShowNotifications}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogTitle className="sr-only">通知设置</DialogTitle>
          <NotificationSettings onClose={handleCloseNotifications} />
        </DialogContent>
      </Dialog>
    </div>
  )
}