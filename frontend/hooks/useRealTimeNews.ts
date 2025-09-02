import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { NewsItem } from '@/types/news';
import { useNewsStore, useNotificationStore } from '@/lib/store';

export function useRealTimeNews() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const { addNews, setConnected } = useNewsStore();
  const { preferences, browserPermission } = useNotificationStore();

  useEffect(() => {
    const socketInstance = io(process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000');
    
    socketInstance.on('connect', () => {
      setConnected(true);
      console.log('WebSocket connected');
    });
    
    socketInstance.on('disconnect', () => {
      setConnected(false);
      console.log('WebSocket disconnected');
    });
    
    socketInstance.on('new_news', (newsItem: NewsItem) => {
      addNews(newsItem);
    });
    
    socketInstance.on('urgent_news', (newsItem: NewsItem) => {
      // Add to news feed first
      addNews(newsItem);
      
      // Show browser notification if enabled and permitted
      if (
        preferences.browserNotifications && 
        preferences.urgentNotifications &&
        typeof window !== 'undefined' && 
        'Notification' in window &&
        browserPermission === 'granted'
      ) {
        // Check importance threshold
        if (newsItem.importanceScore >= preferences.minImportance) {
          new Notification(newsItem.title, {
            body: newsItem.summary || newsItem.content.substring(0, 100) + '...',
            icon: '/favicon.ico',
            tag: 'urgent-news',
            requireInteraction: true
          });
        }
      }
    });
    
    setSocket(socketInstance);
    
    return () => {
      socketInstance.close();
    };
  }, [addNews, setConnected, preferences, browserPermission]);

  return { socket };
}