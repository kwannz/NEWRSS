"use client";

import { useEffect, useState, useCallback } from 'react';
import { useRealTimeNews } from '@/hooks/useRealTimeNews';
import { NewsItem } from '@/types/news';
import { NewsCard } from '@/components/NewsCard';

export default function Home() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const { socket } = useRealTimeNews();

  const fetchInitial = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/news/?limit=20`);
      const data = await res.json();
      setNews(data);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    fetchInitial();
  }, [fetchInitial]);

  useEffect(() => {
    if (!socket) return;
    const onNew = (item: NewsItem) => setNews(prev => [item, ...prev]);
    socket.on('new_news', onNew);
    return () => {
      socket.off('new_news', onNew);
    };
  }, [socket]);

  const handleRead = (id: number) => {
    // 占位：可上报已读
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-8">
      <div className="w-full max-w-5xl">
        <h1 className="text-2xl font-bold mb-4">实时新闻</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {news.map((n) => (
            <NewsCard key={n.id} news={n} onRead={handleRead} />
          ))}
        </div>
      </div>
    </main>
  );
}