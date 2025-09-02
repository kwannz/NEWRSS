"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useNotificationStore, useAuthStore } from '@/lib/store'
import { Bell, MessageSquare, Check, X, AlertTriangle } from 'lucide-react'

interface NotificationSettingsProps {
  onClose?: () => void
}

export function NotificationSettings({ onClose }: NotificationSettingsProps) {
  const { 
    preferences, 
    browserPermission, 
    telegramConnected,
    updatePreferences, 
    requestBrowserPermission,
    checkTelegramConnection 
  } = useNotificationStore()
  
  const { user, isAuthenticated } = useAuthStore()
  const [importanceRange, setImportanceRange] = useState([preferences.minImportance])
  const [maxNotifications, setMaxNotifications] = useState([preferences.maxDailyNotifications])
  const [isUpdating, setIsUpdating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      checkTelegramConnection()
    }
    setImportanceRange([preferences.minImportance])
    setMaxNotifications([preferences.maxDailyNotifications])
  }, [isAuthenticated, checkTelegramConnection, preferences.minImportance, preferences.maxDailyNotifications])

  const handleBrowserNotificationToggle = async (enabled: boolean) => {
    if (enabled && browserPermission !== 'granted') {
      const permission = await requestBrowserPermission()
      if (permission !== 'granted') {
        return // Don't update if permission denied
      }
    }
    updatePreferences({ browserNotifications: enabled })
  }

  const handleSavePreferences = async () => {
    setIsUpdating(true)
    try {
      updatePreferences({
        minImportance: importanceRange[0],
        maxDailyNotifications: maxNotifications[0]
      })
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 2000)
    } catch (error) {
      console.error('Failed to save preferences:', error)
    } finally {
      setIsUpdating(false)
    }
  }

  const getBrowserPermissionStatus = () => {
    switch (browserPermission) {
      case 'granted':
        return { icon: Check, text: '已授权', variant: 'default' as const }
      case 'denied':
        return { icon: X, text: '已拒绝', variant: 'destructive' as const }
      default:
        return { icon: AlertTriangle, text: '待授权', variant: 'secondary' as const }
    }
  }

  const getTelegramStatus = () => {
    if (telegramConnected) {
      return { icon: Check, text: '已连接', variant: 'default' as const }
    }
    return { icon: X, text: '未连接', variant: 'secondary' as const }
  }

  if (!isAuthenticated) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            通知设置
          </CardTitle>
          <CardDescription>
            请先登录以管理您的通知偏好
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              登录后可以个性化您的通知设置
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  const browserStatus = getBrowserPermissionStatus()
  const telegramStatus = getTelegramStatus()
  const BrowserIcon = browserStatus.icon
  const TelegramIcon = telegramStatus.icon

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          通知设置
        </CardTitle>
        <CardDescription>
          管理您的新闻通知偏好和渠道
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {showSuccess && (
          <Alert>
            <Check className="h-4 w-4" />
            <AlertDescription>
              设置已保存！
            </AlertDescription>
          </Alert>
        )}

        {/* Notification Channels */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium">通知渠道</h4>
          
          {/* Browser Notifications */}
          <div className="flex items-center justify-between space-x-2">
            <div className="flex items-center space-x-2">
              <Bell className="h-4 w-4" />
              <Label className="text-sm">浏览器通知</Label>
              <Badge variant={browserStatus.variant}>
                <BrowserIcon className="mr-1 h-3 w-3" />
                {browserStatus.text}
              </Badge>
            </div>
            <Switch 
              checked={preferences.browserNotifications && browserPermission === 'granted'}
              onCheckedChange={handleBrowserNotificationToggle}
            />
          </div>

          {/* Telegram Notifications */}
          <div className="flex items-center justify-between space-x-2">
            <div className="flex items-center space-x-2">
              <MessageSquare className="h-4 w-4" />
              <Label className="text-sm">Telegram 通知</Label>
              <Badge variant={telegramStatus.variant}>
                <TelegramIcon className="mr-1 h-3 w-3" />
                {telegramStatus.text}
              </Badge>
            </div>
            <Switch 
              checked={preferences.telegramNotifications && telegramConnected}
              onCheckedChange={(checked) => updatePreferences({ telegramNotifications: checked })}
              disabled={!telegramConnected}
            />
          </div>
          
          {!telegramConnected && (
            <Alert>
              <MessageSquare className="h-4 w-4" />
              <AlertDescription>
                <div className="flex flex-col space-y-2">
                  <span>您尚未连接 Telegram 账户</span>
                  <Button size="sm" variant="outline">
                    连接 Telegram
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>

        {/* Notification Preferences */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium">通知偏好</h4>
          
          {/* Urgent Notifications Toggle */}
          <div className="flex items-center justify-between">
            <Label className="text-sm">紧急新闻通知</Label>
            <Switch 
              checked={preferences.urgentNotifications}
              onCheckedChange={(checked) => updatePreferences({ urgentNotifications: checked })}
            />
          </div>

          {/* Daily Digest Toggle */}
          <div className="flex items-center justify-between">
            <Label className="text-sm">每日摘要</Label>
            <Switch 
              checked={preferences.dailyDigest}
              onCheckedChange={(checked) => updatePreferences({ dailyDigest: checked })}
            />
          </div>
        </div>

        {/* Advanced Settings */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium">高级设置</h4>
          
          {/* Minimum Importance Slider */}
          <div className="space-y-3">
            <Label className="text-sm">最低通知重要度: {importanceRange[0]}</Label>
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

          {/* Max Daily Notifications Slider */}
          <div className="space-y-3">
            <Label className="text-sm">每日最大通知数: {maxNotifications[0]}</Label>
            <Slider
              value={maxNotifications}
              onValueChange={setMaxNotifications}
              max={50}
              min={1}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1</span>
              <span>50</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-4">
          {onClose && (
            <Button variant="outline" onClick={onClose} className="flex-1">
              关闭
            </Button>
          )}
          <Button 
            onClick={handleSavePreferences}
            className="flex-1"
            disabled={isUpdating}
          >
            {isUpdating ? '保存中...' : '保存设置'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}