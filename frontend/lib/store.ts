import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { NewsItem, User, NewsFilter } from '@/types/news'
import { apiClient } from './api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
  updatePreferences: (preferences: any) => Promise<void>
}

interface NewsState {
  news: NewsItem[]
  isConnected: boolean
  filters: NewsFilter
  loading: boolean
  error: string | null
  addNews: (item: NewsItem) => void
  setNews: (items: NewsItem[]) => void
  setConnected: (connected: boolean) => void
  setFilters: (filters: Partial<NewsFilter>) => void
  clearError: () => void
  setError: (error: string) => void
  setLoading: (loading: boolean) => void
}

interface NotificationState {
  browserPermission: NotificationPermission | null
  telegramConnected: boolean
  preferences: {
    urgentNotifications: boolean
    dailyDigest: boolean
    browserNotifications: boolean
    telegramNotifications: boolean
    minImportance: number
    maxDailyNotifications: number
  }
  requestBrowserPermission: () => Promise<NotificationPermission>
  updatePreferences: (prefs: Partial<NotificationState['preferences']>) => void
  checkTelegramConnection: () => Promise<void>
  connectTelegram: (telegramId: string) => Promise<any>
  disconnectTelegram: () => Promise<void>
}

// Auth Store
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      token: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true })
        try {
          const response = await apiClient.login(username, password)
          const { access_token } = response
          apiClient.setToken(access_token)
          
          // Get user info
          const user = await apiClient.getCurrentUser()
          
          set({
            user,
            isAuthenticated: true,
            token: access_token,
            isLoading: false
          })
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      register: async (username: string, email: string, password: string) => {
        set({ isLoading: true })
        try {
          const user = await apiClient.register(username, email, password)
          // Auto login after registration
          await get().login(username, password)
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => {
        apiClient.setToken(null)
        set({
          user: null,
          isAuthenticated: false,
          token: null
        })
      },

      loadUser: async () => {
        const { token } = get()
        if (!token) return
        
        set({ isLoading: true })
        try {
          apiClient.setToken(token)
          const user = await apiClient.getCurrentUser()
          set({ user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          // Token invalid, clear auth state
          get().logout()
          set({ isLoading: false })
        }
      },

      updatePreferences: async (preferences: any) => {
        try {
          await apiClient.updateUserPreferences(preferences)
          const user = await apiClient.getCurrentUser()
          set({ user })
        } catch (error) {
          throw error
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        token: state.token, 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      })
    }
  )
)

// News Store
export const useNewsStore = create<NewsState>()((set, get) => ({
  news: [],
  isConnected: false,
  filters: {},
  loading: false,
  error: null,

  addNews: (item: NewsItem) => {
    set((state) => {
      // Prevent duplicates
      const exists = state.news.find(n => n.id === item.id)
      if (exists) return state
      
      // Add to beginning and limit to 1000 items
      const newNews = [item, ...state.news].slice(0, 1000)
      return { news: newNews }
    })
  },

  setNews: (items: NewsItem[]) => set({ news: items }),
  
  setConnected: (connected: boolean) => set({ isConnected: connected }),
  
  setFilters: (filters: Partial<NewsFilter>) => {
    set((state) => ({ filters: { ...state.filters, ...filters } }))
  },
  
  clearError: () => set({ error: null }),
  
  setError: (error: string) => set({ error }),
  
  setLoading: (loading: boolean) => set({ loading })
}))

// Notification Store
export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      browserPermission: typeof window !== 'undefined' ? Notification.permission : null,
      telegramConnected: false,
      preferences: {
        urgentNotifications: true,
        dailyDigest: false,
        browserNotifications: true,
        telegramNotifications: false,
        minImportance: 3,
        maxDailyNotifications: 10
      },

      requestBrowserPermission: async () => {
        if (typeof window === 'undefined' || !('Notification' in window)) {
          return 'denied'
        }
        
        const permission = await Notification.requestPermission()
        set({ browserPermission: permission })
        return permission
      },

      updatePreferences: (prefs: Partial<NotificationState['preferences']>) => {
        set((state) => ({
          preferences: { ...state.preferences, ...prefs }
        }))
      },

      checkTelegramConnection: async () => {
        try {
          const user = await apiClient.getCurrentUser()
          set({ telegramConnected: !!user.telegram_id })
        } catch (error) {
          console.error('Failed to check Telegram connection:', error)
        }
      },

      connectTelegram: async (telegramId: string) => {
        try {
          const result = await apiClient.connectTelegram(telegramId)
          set({ telegramConnected: true })
          // Update auth store to reflect new telegram_id
          const authStore = useAuthStore.getState()
          if (authStore.loadUser) {
            await authStore.loadUser()
          }
          return result
        } catch (error) {
          console.error('Failed to connect Telegram:', error)
          throw error
        }
      },

      disconnectTelegram: async () => {
        try {
          await apiClient.disconnectTelegram()
          set({ telegramConnected: false })
          // Update auth store to reflect cleared telegram_id
          const authStore = useAuthStore.getState()
          if (authStore.loadUser) {
            await authStore.loadUser()
          }
        } catch (error) {
          console.error('Failed to disconnect Telegram:', error)
          throw error
        }
      }
    }),
    {
      name: 'notification-settings',
      partialize: (state) => ({ preferences: state.preferences })
    }
  )
)