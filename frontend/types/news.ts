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
  isActive: boolean;
  telegramId?: string;
  telegramUsername?: string;
  urgentNotifications: boolean;
  dailyDigest: boolean;
}