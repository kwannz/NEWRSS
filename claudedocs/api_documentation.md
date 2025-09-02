# 📋 API Documentation Index

## 🎯 API Overview

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**Authentication**: JWT Bearer Token  
**Content-Type**: `application/json`

---

## 🔐 Authentication Endpoints

### POST `/auth/register`
**User Registration**
```typescript
Body: {
  username: string;
  email: string;
  password: string;
}
Response: UserResponse
```

### POST `/auth/token` 
**User Login**
```typescript
Body: OAuth2PasswordRequestForm
Response: {
  access_token: string;
  token_type: "bearer";
}
```

### GET `/auth/me`
**Get Current User** 🔒
```typescript
Headers: { Authorization: "Bearer <token>" }
Response: UserResponse
```

---

## 📰 News Endpoints

### GET `/news/`
**List News Items**
```typescript
Query Parameters:
  page?: number = 1           // Pagination
  limit?: number = 20         // Items per page (max 100)
  category?: string           // Filter by category
  source?: string            // Filter by source
  urgent_only?: boolean      // Urgent news only
  min_importance?: number    // Importance filter (1-5)

Response: NewsItemResponse[]
```

### GET `/news/{news_id}`
**Get News Item Details**
```typescript
Path: news_id: number
Response: NewsItemResponse
```

### POST `/news/broadcast` 🔒
**Trigger WebSocket Broadcast**
```typescript
Body: { news_id: number }
Response: {
  status: "ok";
  broadcasted: "new_news" | "urgent_news";
  id: number;
}
```

---

## 📡 RSS Sources Endpoints

### GET `/sources/`
**List RSS Sources**
```typescript
Query Parameters:
  category?: string          // Filter by category
  active_only?: boolean = true  // Active sources only

Response: NewsSourceResponse[]
```

### GET `/sources/categories`
**Get Source Categories**
```typescript
Response: {
  categories: string[];
}
```

### GET `/sources/stats`
**Source Statistics**
```typescript
Response: {
  total: number;
  active: number;
  inactive: number;
  by_category: Record<string, number>;
  by_type: Record<string, number>;
}
```

### POST `/sources/` 🔒
**Create RSS Source**
```typescript
Body: NewsSourceCreate
Response: NewsSourceResponse
```

### PUT `/sources/{source_id}` 🔒
**Update RSS Source**
```typescript
Path: source_id: number
Body: NewsSourceUpdate
Response: NewsSourceResponse
```

### DELETE `/sources/{source_id}` 🔒
**Delete RSS Source**
```typescript
Path: source_id: number
Response: { message: string }
```

### POST `/sources/{source_id}/toggle` 🔒
**Toggle Source Status**
```typescript
Path: source_id: number
Response: {
  message: string;
  is_active: boolean;
}
```

---

## 📡 Telegram Webhook

### POST `/telegram/webhook`
**Telegram Bot Webhook**
```typescript
Headers: { X-Telegram-Bot-Api-Secret-Token?: string }
Body: TelegramUpdate
Response: { status: "ok" }
```

---

## 🔄 WebSocket Events

### Connection
**Endpoint**: `ws://localhost:8000/socket.io/`

### Events

#### `new_news`
**Regular News Broadcast**
```typescript
Payload: NewsItemResponse
```

#### `urgent_news`
**Urgent News Broadcast**
```typescript
Payload: NewsItemResponse
```

---

## 📝 Data Models

### NewsItemResponse
```typescript
interface NewsItemResponse {
  id: number;
  title: string;
  titleEn?: string;           // English translation
  content: string;
  contentEn?: string;         // English translation
  summary?: string;           // AI-generated summary
  summaryEn?: string;         // English summary
  url: string;
  source: string;
  category?: string;
  publishedAt: string;        // ISO timestamp
  importanceScore: number;    // 1-5 scale
  isUrgent: boolean;
  marketImpact: number;       // 1-5 scale
  sentimentScore?: number;    // -1 to 1
  keyTokens?: string[];       // Extracted tokens
  keyPrices?: string[];       // Extracted prices
  createdAt: string;          // ISO timestamp
}
```

### NewsSourceResponse
```typescript
interface NewsSourceResponse {
  id: number;
  name: string;
  url: string;
  source_type: string;        // "rss", "api", etc.
  category: string;
  is_active: boolean;
  fetch_interval: number;     // Seconds
  last_fetched?: string;      // ISO timestamp
  priority: number;           // Higher = more important
  created_at: string;         // ISO timestamp
  updated_at?: string;        // ISO timestamp
}
```

### UserResponse
```typescript
interface UserResponse {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  telegram_id?: string;
}
```

---

## 🚨 Error Responses

### Standard Error Format
```typescript
{
  detail: string;              // Error message
  status_code: number;         // HTTP status code
}
```

### Common Status Codes
- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (authentication required)
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

---

## 🔧 Development Tools

### Health Check
**GET `/health`**
```typescript
Response: { status: "healthy" }
```

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🌐 CORS Configuration

**Allowed Origins**: 
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:8000`
- `http://127.0.0.1:8000`

**Methods**: All (`*`)  
**Headers**: All (`*`)  
**Credentials**: Enabled

---

*🔒 = Requires Authentication*