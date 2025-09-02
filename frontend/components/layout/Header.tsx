"use client"

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AuthModal } from '@/components/auth/AuthModal'
import { UserMenu } from '@/components/auth/UserMenu'
import { useAuthStore, useNewsStore } from '@/lib/store'
import { Wifi, WifiOff, Filter } from 'lucide-react'

interface HeaderProps {
  onOpenFilters?: () => void
  onOpenSettings?: () => void
  onOpenNotifications?: () => void
}

export function Header({ 
  onOpenFilters, 
  onOpenSettings, 
  onOpenNotifications 
}: HeaderProps) {
  const { isAuthenticated, loadUser, isLoading } = useAuthStore()
  const { isConnected } = useNewsStore()
  const [mounted, setMounted] = useState(false)

  // Ensure component is mounted before accessing localStorage
  useEffect(() => {
    setMounted(true)
    if (!isLoading) {
      loadUser()
    }
  }, [loadUser, isLoading])

  if (!mounted) {
    return (
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center px-4">
          <div className="mr-4 flex">
            <h1 className="text-xl font-bold">NEWRSS</h1>
          </div>
          <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
            <div className="w-full flex-1 md:w-auto md:flex-none">
              {/* Skeleton loading state */}
            </div>
          </div>
        </div>
      </header>
    )
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center px-4">
        <div className="mr-4 flex items-center space-x-2">
          <h1 className="text-xl font-bold">加密新闻</h1>
          <Badge 
            variant={isConnected ? "default" : "destructive"}
            className="ml-2"
          >
            {isConnected ? (
              <>
                <Wifi className="mr-1 h-3 w-3" />
                实时
              </>
            ) : (
              <>
                <WifiOff className="mr-1 h-3 w-3" />
                离线
              </>
            )}
          </Badge>
        </div>
        
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <div className="flex items-center space-x-2">
            {/* Filter button - show for all users */}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onOpenFilters}
            >
              <Filter className="mr-2 h-4 w-4" />
              筛选
            </Button>
            
            {/* Authentication area */}
            {isAuthenticated ? (
              <UserMenu 
                onOpenSettings={onOpenSettings}
                onOpenNotifications={onOpenNotifications}
              />
            ) : (
              <AuthModal />
            )}
          </div>
        </div>
      </div>
    </header>
  )
}