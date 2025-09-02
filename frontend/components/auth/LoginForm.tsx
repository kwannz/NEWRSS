"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { getErrorMessage } from '@/lib/utils'

interface LoginFormProps {
  onSwitchToRegister?: () => void
  onSuccess?: () => void
}

export function LoginForm({ onSwitchToRegister, onSuccess }: LoginFormProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  
  const { login, isLoading } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('请填写用户名和密码')
      return
    }

    try {
      await login(username.trim(), password)
      onSuccess?.()
    } catch (err) {
      const message = getErrorMessage(err)
      if (message.includes('401') || message.includes('Unauthorized')) {
        setError('用户名或密码错误')
      } else {
        setError('登录失败，请稍后重试')
      }
    }
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>登录</CardTitle>
        <CardDescription>登录您的 NEWRSS 账户以获取个性化新闻体验</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">用户名</Label>
            <Input
              id="username"
              type="text"
              placeholder="输入用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              autoComplete="username"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <Input
              id="password"
              type="password"
              placeholder="输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="current-password"
              required
            />
          </div>
          
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <Button 
            type="submit" 
            className="w-full" 
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>
          
          {onSwitchToRegister && (
            <div className="text-center text-sm">
              <span className="text-muted-foreground">还没有账户？</span>
              <Button
                type="button"
                variant="link"
                className="p-0 ml-1"
                onClick={onSwitchToRegister}
              >
                立即注册
              </Button>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  )
}