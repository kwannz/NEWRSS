import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { NewsItem, NewsFilter, User } from '@/types/news'

class ApiClient {
  private client: AxiosInstance
  private token: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Token interceptor
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`
      }
      return config
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.token = null
          localStorage.removeItem('auth_token')
        }
        return Promise.reject(error)
      }
    )
  }

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  loadToken() {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      if (token) {
        this.token = token
      }
    }
  }

  // Auth endpoints
  async login(username: string, password: string) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await this.client.post('/auth/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    return response.data
  }

  async register(username: string, email: string, password: string) {
    const response = await this.client.post('/auth/register', {
      username,
      email,
      password
    })
    return response.data
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  // News endpoints
  async getNews(params?: {
    page?: number
    limit?: number
    category?: string
    source?: string
    urgent_only?: boolean
    min_importance?: number
  }): Promise<NewsItem[]> {
    const response = await this.client.get('/news', { params })
    return response.data
  }

  async getNewsItem(id: number): Promise<NewsItem> {
    const response = await this.client.get(`/news/${id}`)
    return response.data
  }

  // User preferences (placeholder for future backend implementation)
  async updateUserPreferences(preferences: {
    urgent_notifications?: boolean
    daily_digest?: boolean
    min_importance_score?: number
    max_daily_notifications?: number
    categories?: string[]
  }) {
    // TODO: Implement when backend user preferences API is available
    const response = await this.client.patch('/auth/me/preferences', preferences)
    return response.data
  }

  async getUserPreferences() {
    // TODO: Implement when backend user preferences API is available
    const response = await this.client.get('/auth/me/preferences')
    return response.data
  }

  // Telegram connection endpoints
  async connectTelegram(telegramId: string) {
    const formData = new FormData()
    formData.append('telegram_id', telegramId)
    
    const response = await this.client.post('/telegram/connect', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    return response.data
  }

  async disconnectTelegram() {
    const response = await this.client.post('/telegram/disconnect')
    return response.data
  }
}

export const apiClient = new ApiClient()

// Initialize token on load
if (typeof window !== 'undefined') {
  apiClient.loadToken()
}