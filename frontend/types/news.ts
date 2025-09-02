export interface NewsItem {
  id: number;
  title: string;
  content: string;
  summary?: string;
  url: string;
  source: string;
  category?: string;
  publishedAt: string;
  importanceScore: number;
  isUrgent: boolean;
  marketImpact: number;
  sentimentScore?: number;
  keyTokens?: string[];
  keyPrices?: string[];
  isProcessed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface NewsFilter {
  category?: string;
  source?: string;
  timeRange?: 'hour' | 'day' | 'week';
  importance?: number;
  urgent?: boolean;
}

export interface NewsSource {
  id: number;
  name: string;
  url: string;
  sourceType: string;
  category?: string;
  isActive: boolean;
  fetchInterval: number;
  lastFetched?: string;
  priority: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  telegram_id?: string;
  telegram_username?: string;
  urgent_notifications?: boolean;
  daily_digest?: boolean;
  min_importance_score?: number;
  max_daily_notifications?: number;
  timezone?: string;
}

export interface UserPreferences {
  urgentNotifications: boolean;
  dailyDigest: boolean;
  browserNotifications: boolean;
  telegramNotifications: boolean;
  minImportance: number;
  maxDailyNotifications: number;
  categories: string[];
  sources: string[];
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}