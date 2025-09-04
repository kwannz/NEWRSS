# Telegram Bot 集成设置指南

## 开发环境现状

NEWRSS 平台已实现基本的 Telegram Bot 功能集成，当前运行在开发模式下。

### 已实现功能

#### Webhook 端点
- **POST /telegram/webhook** - 处理 Telegram 消息更新
- **GET /telegram/users** - 查看注册用户列表
- **POST /telegram/broadcast** - 向订阅用户广播消息

#### Bot 命令支持
- `/start` - 欢迎消息和功能介绍
- `/subscribe` - 订阅新闻推送
- `/unsubscribe` - 取消订阅 
- `/status` - 查看订阅状态
- `/help` - 帮助信息

#### 用户管理
- 内存存储用户信息（开发模式）
- 订阅状态跟踪
- 中文界面支持

### 测试结果

✅ Webhook 端点工作正常  
✅ 用户注册功能正常  
✅ 订阅/取消订阅功能正常  
✅ 状态查询功能正常  

### 生产环境配置

要在生产环境中使用，需要：

1. **获取 Telegram Bot Token**
   ```bash
   # 与 @BotFather 对话创建 bot
   # 获取 token 格式: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```

2. **配置环境变量**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_WEBHOOK_URL="https://your-domain.com/telegram/webhook"
   export TELEGRAM_SECRET_TOKEN="your_secret_token"
   ```

3. **设置 Webhook**
   ```bash
   curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
   -H "Content-Type: application/json" \
   -d '{"url":"https://your-domain.com/telegram/webhook","secret_token":"your_secret_token"}'
   ```

### 当前开发测试

后端已启动在 http://localhost:8000，包含以下 Telegram 功能：

- 用户可以与 bot 交互（模拟模式）
- 支持订阅管理
- 中文命令响应
- 用户状态跟踪

### 下一步开发

要完成完整的 Telegram 集成：

1. 连接真实的 Telegram Bot API
2. 实现数据库持久化存储
3. 添加新闻推送功能
4. 集成 WebSocket 实时更新

### API 端点示例

```bash
# 查看用户列表
curl http://localhost:8000/telegram/users

# 模拟广播消息
curl -X POST http://localhost:8000/telegram/broadcast -F "message=测试消息"

# 模拟 webhook 消息
curl -X POST http://localhost:8000/telegram/webhook \
-H "Content-Type: application/json" \
-d '{"message":{"chat":{"id":123},"from":{"first_name":"用户"},"text":"/start"}}'
```

当前 Telegram 功能已集成到简单后端，可以进行基本的 bot 交互测试。