import { NewsItem } from '@/types/news';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { formatTimeAgo } from '@/lib/utils';

interface NewsCardProps {
  news: NewsItem;
  onRead: (id: number) => void;
}

export function NewsCard({ news, onRead }: NewsCardProps) {
  return (
    <Card 
      className="hover:shadow-lg transition-shadow cursor-pointer" 
      onClick={() => onRead(news.id)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Badge variant={news.isUrgent ? "destructive" : "secondary"}>
            {news.source}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {formatTimeAgo(news.publishedAt)}
          </span>
        </div>
        <h3 className="font-semibold line-clamp-2">{news.title}</h3>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
          {news.summary || news.content}
        </p>
        <div className="flex items-center justify-between">
          <Badge variant="outline">{news.category || 'general'}</Badge>
          <div className="flex items-center space-x-1">
            <span className="text-xs">重要度:</span>
            <div className="flex">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full mr-1 ${
                    i < news.importanceScore ? 'bg-red-500' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
        {news.keyTokens && news.keyTokens.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {news.keyTokens.slice(0, 3).map((token) => (
              <Badge key={token} variant="outline" className="text-xs">
                {token}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}