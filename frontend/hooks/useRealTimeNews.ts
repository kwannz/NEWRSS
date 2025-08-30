import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { NewsItem } from '@/types/news';
import { useNewsStore } from '@/lib/store';

export function useRealTimeNews() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const { addNews, setConnected } = useNewsStore();

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
      // 显示紧急新闻通知
      if (typeof window !== 'undefined' && 'Notification' in window) {
        if (Notification.permission === 'granted') {
          new Notification(newsItem.title, {
            body: newsItem.content.substring(0, 100) + '...',
            icon: '/favicon.ico',
            tag: 'urgent-news'
          });
        } else if (Notification.permission !== 'denied') {
          Notification.requestPermission().then((permission) => {
            if (permission === 'granted') {
              new Notification(newsItem.title, {
                body: newsItem.content.substring(0, 100) + '...',
                icon: '/favicon.ico',
                tag: 'urgent-news'
              });
            }
          });
        }
      }
      addNews(newsItem);
    });
    
    setSocket(socketInstance);
    
    return () => {
      socketInstance.close();
    };
  }, [addNews, setConnected]);

  return { socket };
}