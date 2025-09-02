"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { useNewsStore } from '@/lib/store'
import { NewsFilter } from '@/types/news'
import { X, RotateCcw } from 'lucide-react'

interface NewsFilterProps {
  onClose?: () => void
}

const CATEGORIES = [
  { value: 'bitcoin', label: '比特币' },
  { value: 'ethereum', label: '以太坊' },
  { value: 'defi', label: 'DeFi' },
  { value: 'nft', label: 'NFT' },
  { value: 'altcoin', label: '山寨币' },
  { value: 'trading', label: '交易' },
  { value: 'regulation', label: '监管' },
  { value: 'mining', label: '挖矿' },
  { value: 'general', label: '通用' }
]

const SOURCES = [
  { value: 'coindesk', label: 'CoinDesk' },
  { value: 'cointelegraph', label: 'Cointelegraph' },
  { value: 'cryptocompare', label: 'CryptoCompare' },
  { value: 'newsbtc', label: 'NewsBTC' },
  { value: 'decrypt', label: 'Decrypt' },
  { value: '8btc', label: '巴比特' },
  { value: 'jinse', label: '金色财经' }
]

const TIME_RANGES = [
  { value: 'hour', label: '最近1小时' },
  { value: 'day', label: '最近1天' },
  { value: 'week', label: '最近1周' }
]

export function NewsFilterComponent({ onClose }: NewsFilterProps) {
  const { filters, setFilters } = useNewsStore()
  const [localFilters, setLocalFilters] = useState<NewsFilter>(filters)
  const [importanceRange, setImportanceRange] = useState([localFilters.importance || 1])

  useEffect(() => {
    setLocalFilters(filters)
    setImportanceRange([filters.importance || 1])
  }, [filters])

  const handleApplyFilters = () => {
    const newFilters = {
      ...localFilters,
      importance: importanceRange[0]
    }
    setFilters(newFilters)
    onClose?.()
  }

  const handleResetFilters = () => {
    const resetFilters: NewsFilter = {}
    setLocalFilters(resetFilters)
    setImportanceRange([1])
    setFilters(resetFilters)
  }

  const handleCategoryChange = (category: string) => {
    setLocalFilters(prev => ({
      ...prev,
      category: category === 'all' ? undefined : category
    }))
  }

  const handleSourceChange = (source: string) => {
    setLocalFilters(prev => ({
      ...prev,
      source: source === 'all' ? undefined : source
    }))
  }

  const handleTimeRangeChange = (timeRange: string) => {
    setLocalFilters(prev => ({
      ...prev,
      timeRange: timeRange === 'all' ? undefined : timeRange as 'hour' | 'day' | 'week'
    }))
  }

  const handleUrgentToggle = () => {
    setLocalFilters(prev => ({
      ...prev,
      urgent: prev.urgent ? undefined : true
    }))
  }

  const getActiveFiltersCount = () => {
    let count = 0
    if (localFilters.category) count++
    if (localFilters.source) count++
    if (localFilters.timeRange) count++
    if (localFilters.urgent) count++
    if (importanceRange[0] > 1) count++
    return count
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            新闻筛选
            {getActiveFiltersCount() > 0 && (
              <Badge variant="secondary" className="text-xs">
                {getActiveFiltersCount()} 个有效
              </Badge>
            )}
          </CardTitle>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Category Filter */}
        <div className="space-y-2">
          <Label>分类</Label>
          <Select 
            value={localFilters.category || 'all'} 
            onValueChange={handleCategoryChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分类</SelectItem>
              {CATEGORIES.map(cat => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Source Filter */}
        <div className="space-y-2">
          <Label>新闻源</Label>
          <Select 
            value={localFilters.source || 'all'} 
            onValueChange={handleSourceChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择新闻源" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部源</SelectItem>
              {SOURCES.map(source => (
                <SelectItem key={source.value} value={source.value}>
                  {source.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Time Range Filter */}
        <div className="space-y-2">
          <Label>时间范围</Label>
          <Select 
            value={localFilters.timeRange || 'all'} 
            onValueChange={handleTimeRangeChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择时间范围" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部时间</SelectItem>
              {TIME_RANGES.map(range => (
                <SelectItem key={range.value} value={range.value}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Importance Slider */}
        <div className="space-y-3">
          <Label>最低重要度: {importanceRange[0]}</Label>
          <Slider
            value={importanceRange}
            onValueChange={setImportanceRange}
            max={5}
            min={1}
            step={1}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>低</span>
            <span>高</span>
          </div>
        </div>

        {/* Urgent Only Toggle */}
        <div className="flex items-center justify-between">
          <Label>仅显示紧急新闻</Label>
          <Button
            variant={localFilters.urgent ? "default" : "outline"}
            size="sm"
            onClick={handleUrgentToggle}
          >
            {localFilters.urgent ? '已开启' : '关闭'}
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-4">
          <Button 
            variant="outline" 
            onClick={handleResetFilters}
            className="flex-1"
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            重置
          </Button>
          <Button 
            onClick={handleApplyFilters}
            className="flex-1"
          >
            应用筛选
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}