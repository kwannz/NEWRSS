"use client"

import { useState } from 'react'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'
import { User } from 'lucide-react'

interface AuthModalProps {
  children?: React.ReactNode
  trigger?: React.ReactNode
}

export function AuthModal({ children, trigger }: AuthModalProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')

  const handleSuccess = () => {
    setIsOpen(false)
    // Reset to login mode for next time
    setMode('login')
  }

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <User className="mr-2 h-4 w-4" />
            登录
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        {mode === 'login' ? (
          <LoginForm
            onSwitchToRegister={switchMode}
            onSuccess={handleSuccess}
          />
        ) : (
          <RegisterForm
            onSwitchToLogin={switchMode}
            onSuccess={handleSuccess}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}