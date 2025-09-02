"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { getErrorMessage, validateEmail } from '@/lib/utils'

interface RegisterFormProps {
  onSwitchToLogin?: () => void
  onSuccess?: () => void
}

export function RegisterForm({ onSwitchToLogin, onSuccess }: RegisterFormProps) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  })
  const [error, setError] = useState('')
  
  const { register, isLoading } = useAuthStore()

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (error) setError('')
  }

  const validateForm = () => {
    const { username, email, password, confirmPassword } = formData
    
    if (!username.trim()) {
      return '请输入用户名'
    }
    
    if (username.length < 3) {
      return '用户名至少3个字符'
    }
    
    if (!email.trim()) {
      return '请输入邮箱地址'
    }
    
    if (!validateEmail(email)) {
      return '请输入有效的邮箱地址'
    }
    
    if (!password) {
      return '请输入密码'
    }
    
    if (password.length < 6) {
      return '密码至少6个字符'
    }
    
    if (password !== confirmPassword) {
      return '两次输入的密码不一致'
    }
    
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    try {
      await register(formData.username.trim(), formData.email.trim(), formData.password)
      onSuccess?.()
    } catch (err) {
      const message = getErrorMessage(err)
      if (message.includes('already registered') || message.includes('已注册')) {
        setError('用户名或邮箱已被使用')
      } else {
        setError('注册失败，请稍后重试')
      }
    }
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>注册</CardTitle>
        <CardDescription>创建您的 NEWRSS 账户，享受个性化加密货币新闻服务</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reg-username">用户名</Label>
            <Input
              id="reg-username"
              type="text"
              placeholder="输入用户名（3个字符以上）"
              value={formData.username}
              onChange={(e) => handleChange('username', e.target.value)}
              disabled={isLoading}
              autoComplete="username"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="reg-email">邮箱地址</Label>
            <Input
              id="reg-email"
              type="email"
              placeholder="输入邮箱地址"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              disabled={isLoading}
              autoComplete="email"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="reg-password">密码</Label>
            <Input
              id="reg-password"
              type="password"
              placeholder="输入密码（6个字符以上）"
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              disabled={isLoading}
              autoComplete="new-password"
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="reg-confirm-password">确认密码</Label>
            <Input
              id="reg-confirm-password"
              type="password"
              placeholder="再次输入密码"
              value={formData.confirmPassword}
              onChange={(e) => handleChange('confirmPassword', e.target.value)}
              disabled={isLoading}
              autoComplete="new-password"
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
                注册中...
              </>
            ) : (
              '注册'
            )}
          </Button>
          
          {onSwitchToLogin && (
            <div className="text-center text-sm">
              <span className="text-muted-foreground">已有账户？</span>
              <Button
                type="button"
                variant="link"
                className="p-0 ml-1"
                onClick={onSwitchToLogin}
              >
                立即登录
              </Button>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  )
}