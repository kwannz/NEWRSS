"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { useNotificationStore, useAuthStore } from '@/lib/store'
import { useState as useReactState } from 'react'
import { NotificationSettings } from './NotificationSettings'
import { 
  Settings, 
  Bell, 
  MessageSquare, 
  Check, 
  X, 
  AlertTriangle,
  User,
  Globe,
  Database,
  Shield,
  Palette,
  Clock
} from 'lucide-react'

interface SettingsPageProps {
  onClose?: () => void
}

export function SettingsPage({ onClose }: SettingsPageProps) {
  const { user, isAuthenticated } = useAuthStore()
  const { telegramConnected, connectTelegram, disconnectTelegram, checkTelegramConnection } = useNotificationStore()
  const [activeSection, setActiveSection] = useState('general')
  const [showSuccess, setShowSuccess] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [telegramId, setTelegramId] = useReactState('')
  const [isConnecting, setIsConnecting] = useReactState(false)
  
  // General settings state
  const [language, setLanguage] = useState('zh-CN')
  const [theme, setTheme] = useState('system')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState([30])

  // Check Telegram connection on mount
  useEffect(() => {
    if (isAuthenticated) {
      checkTelegramConnection()
    }
  }, [isAuthenticated, checkTelegramConnection])

  if (!isAuthenticated) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="h-6 w-6" />
          <h2 className="text-2xl font-bold">设置</h2>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              用户设置
            </CardTitle>
            <CardDescription>
              请先登录以访问个人设置
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                登录后可以个性化您的使用体验和通知偏好
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleSaveSettings = async () => {
    setIsUpdating(true)
    try {
      // Save general settings (simulated)
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 2000)
    } catch (error) {
      console.error('Failed to save settings:', error)
    } finally {
      setIsUpdating(false)
    }
  }

  const sections = [
    { id: 'general', label: '常规设置', icon: Settings },
    { id: 'notifications', label: '通知设置', icon: Bell },
    { id: 'account', label: '账户管理', icon: User },
    { id: 'privacy', label: '隐私安全', icon: Shield },
    { id: 'appearance', label: '外观主题', icon: Palette },
    { id: 'data', label: '数据管理', icon: Database }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-6 w-6" />
          <h2 className="text-2xl font-bold">设置</h2>
        </div>
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            关闭
          </Button>
        )}
      </div>

      {showSuccess && (
        <Alert>
          <Check className="h-4 w-4" />
          <AlertDescription>
            设置已保存！
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Settings Navigation */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">设置分类</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {sections.map((section) => {
                const Icon = section.icon
                return (
                  <Button
                    key={section.id}
                    variant={activeSection === section.id ? "default" : "ghost"}
                    className="w-full justify-start"
                    onClick={() => setActiveSection(section.id)}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    {section.label}
                  </Button>
                )
              })}
            </CardContent>
          </Card>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* General Settings */}
          {activeSection === 'general' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  常规设置
                </CardTitle>
                <CardDescription>
                  管理应用的基本设置和行为
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Language Setting */}
                <div className="space-y-2">
                  <Label>界面语言</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh-CN">简体中文</SelectItem>
                      <SelectItem value="en-US">English</SelectItem>
                      <SelectItem value="zh-TW">繁體中文</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Auto Refresh */}
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label>自动刷新</Label>
                    <p className="text-sm text-muted-foreground">
                      自动获取最新新闻
                    </p>
                  </div>
                  <Switch 
                    checked={autoRefresh}
                    onCheckedChange={setAutoRefresh}
                  />
                </div>

                {/* Refresh Interval */}
                {autoRefresh && (
                  <div className="space-y-3">
                    <Label>刷新间隔: {refreshInterval[0]}秒</Label>
                    <Slider
                      value={refreshInterval}
                      onValueChange={setRefreshInterval}
                      max={300}
                      min={10}
                      step={10}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>10秒</span>
                      <span>5分钟</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Notification Settings */}
          {activeSection === 'notifications' && (
            <NotificationSettings />
          )}

          {/* Account Management */}
          {activeSection === 'account' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  账户管理
                </CardTitle>
                <CardDescription>
                  管理您的账户信息和连接
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* User Info */}
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">账户信息</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <Label className="text-muted-foreground">用户名</Label>
                      <p className="font-medium">{user?.username}</p>
                    </div>
                    <div>
                      <Label className="text-muted-foreground">邮箱</Label>
                      <p className="font-medium">{user?.email}</p>
                    </div>
                  </div>
                </div>

                {/* Telegram Connection */}
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">第三方连接</h4>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <MessageSquare className="h-4 w-4" />
                      <Label>Telegram 账户</Label>
                      <Badge variant={telegramConnected ? "default" : "secondary"}>
                        {telegramConnected ? "已连接" : "未连接"}
                      </Badge>
                    </div>
                    {telegramConnected ? (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={async () => {
                          try {
                            await disconnectTelegram()
                            setShowSuccess(true)
                            setTimeout(() => setShowSuccess(false), 2000)
                          } catch (error) {
                            console.error('Failed to disconnect Telegram:', error)
                          }
                        }}
                      >
                        断开连接
                      </Button>
                    ) : (
                      <div className="flex flex-col space-y-2">
                        <div className="flex items-center space-x-2">
                          <Input
                            type="text"
                            placeholder="输入Telegram ID"
                            value={telegramId}
                            onChange={(e) => setTelegramId(e.target.value)}
                            className="flex-1"
                          />
                          <Button 
                            variant="outline" 
                            size="sm"
                            disabled={!telegramId.trim() || isConnecting}
                            onClick={async () => {
                              if (!telegramId.trim()) return
                              setIsConnecting(true)
                              try {
                                await connectTelegram(telegramId.trim())
                                setTelegramId('')
                                setShowSuccess(true)
                                setTimeout(() => setShowSuccess(false), 2000)
                              } catch (error) {
                                console.error('Failed to connect Telegram:', error)
                              } finally {
                                setIsConnecting(false)
                              }
                            }}
                          >
                            {isConnecting ? "连接中..." : "连接"}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                  {telegramConnected && user?.telegram_id && (
                    <p className="text-xs text-muted-foreground">
                      Telegram ID: {user.telegram_id}
                    </p>
                  )}
                  {!telegramConnected && (
                    <Alert>
                      <MessageSquare className="h-4 w-4" />
                      <AlertDescription>
                        <div className="space-y-2">
                          <span>连接Telegram账户后可以接收实时新闻推送。在Telegram中搜索并启动您的NEWRSS机器人，然后输入您的Telegram ID。</span>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={async () => {
                              setIsConnecting(true)
                              try {
                                await connectTelegram("123456789")
                                setShowSuccess(true)
                                setTimeout(() => setShowSuccess(false), 2000)
                              } catch (error) {
                                console.error('Failed to connect demo Telegram:', error)
                              } finally {
                                setIsConnecting(false)
                              }
                            }}
                            disabled={isConnecting}
                          >
                            {isConnecting ? "连接中..." : "演示连接 (ID: 123456789)"}
                          </Button>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Privacy Settings */}
          {activeSection === 'privacy' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  隐私安全
                </CardTitle>
                <CardDescription>
                  管理您的隐私和安全设置
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label>数据分析</Label>
                      <p className="text-sm text-muted-foreground">
                        允许收集匿名使用数据以改进服务
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label>阅读历史</Label>
                      <p className="text-sm text-muted-foreground">
                        保存您的新闻阅读历史
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label>个性化推荐</Label>
                      <p className="text-sm text-muted-foreground">
                        基于阅读偏好推荐相关新闻
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Appearance Settings */}
          {activeSection === 'appearance' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  外观主题
                </CardTitle>
                <CardDescription>
                  自定义应用的外观和主题
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>主题模式</Label>
                  <Select value={theme} onValueChange={setTheme}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">浅色模式</SelectItem>
                      <SelectItem value="dark">深色模式</SelectItem>
                      <SelectItem value="system">跟随系统</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-4">
                  <h4 className="text-sm font-medium">新闻卡片设置</h4>
                  <div className="flex items-center justify-between">
                    <Label>显示完整内容</Label>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>显示重要度标签</Label>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>显示发布时间</Label>
                    <Switch defaultChecked />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Data Management */}
          {activeSection === 'data' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  数据管理
                </CardTitle>
                <CardDescription>
                  管理您的数据和存储设置
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">缓存设置</h4>
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label>本地缓存</Label>
                      <p className="text-sm text-muted-foreground">
                        在本地保存新闻数据以提升加载速度
                      </p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label>离线阅读</Label>
                      <p className="text-sm text-muted-foreground">
                        保存新闻内容以供离线阅读
                      </p>
                    </div>
                    <Switch />
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-sm font-medium">数据清理</h4>
                  <div className="grid grid-cols-1 gap-3">
                    <Button variant="outline" className="justify-start">
                      <Database className="mr-2 h-4 w-4" />
                      清除缓存数据
                    </Button>
                    <Button variant="outline" className="justify-start">
                      <Clock className="mr-2 h-4 w-4" />
                      清除阅读历史
                    </Button>
                    <Button variant="destructive" className="justify-start">
                      <AlertTriangle className="mr-2 h-4 w-4" />
                      重置所有设置
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between">
            <div className="space-x-2">
              {onClose && (
                <Button variant="outline" onClick={onClose}>
                  关闭
                </Button>
              )}
            </div>
            <Button 
              onClick={handleSaveSettings}
              disabled={isUpdating}
            >
              {isUpdating ? '保存中...' : '保存所有设置'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}