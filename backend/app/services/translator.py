"""
Translation service for news content
"""
import re
from typing import Dict, Optional

class SimpleTranslator:
    """简单的中英文翻译服务"""
    
    def __init__(self):
        self.zh_to_en = {
            # 常用词汇
            "比特币": "Bitcoin",
            "以太坊": "Ethereum", 
            "加密货币": "cryptocurrency",
            "区块链": "blockchain",
            "数字货币": "digital currency",
            "去中心化": "decentralized",
            "智能合约": "smart contract",
            "挖矿": "mining",
            "交易所": "exchange",
            "钱包": "wallet",
            "代币": "token",
            "市值": "market cap",
            "涨幅": "gain",
            "跌幅": "decline",
            "交易量": "trading volume",
            "流动性": "liquidity",
            "分叉": "fork",
            "算力": "hash rate",
            "节点": "node",
            "共识": "consensus",
            "治理": "governance",
            "质押": "staking",
            "收益": "yield",
            "协议": "protocol",
            "生态": "ecosystem",
            "基金会": "foundation",
            "监管": "regulation",
            "合规": "compliance",
            "审计": "audit",
            "安全": "security",
            "漏洞": "vulnerability",
            "黑客": "hacker",
            "攻击": "attack",
            "恢复": "recovery",
            "升级": "upgrade",
            "更新": "update",
            "发布": "release",
            "启动": "launch",
            "测试网": "testnet",
            "主网": "mainnet",
            "侧链": "sidechain",
            "跨链": "cross-chain",
            "桥接": "bridge",
            "预言机": "oracle",
            "闪电网络": "Lightning Network",
            "第二层": "Layer 2",
            "扩容": "scaling",
            "分片": "sharding",
            
            # 新闻相关
            "消息": "news",
            "报告": "report", 
            "分析": "analysis",
            "预测": "prediction",
            "观点": "opinion",
            "评论": "comment",
            "声明": "statement",
            "公告": "announcement",
            "披露": "disclosure",
            "确认": "confirmation",
            "否认": "denial",
            "澄清": "clarification",
            "回应": "response",
            "采访": "interview",
            "会议": "conference",
            "峰会": "summit",
            "论坛": "forum",
            "研讨会": "seminar",
            
            # 时间相关
            "今天": "today",
            "昨天": "yesterday", 
            "明天": "tomorrow",
            "本周": "this week",
            "上周": "last week",
            "下周": "next week",
            "本月": "this month",
            "上月": "last month",
            "今年": "this year",
            "去年": "last year",
            "小时前": "hours ago",
            "分钟前": "minutes ago",
            "天前": "days ago",
            "刚刚": "just now",
            
            # 动作词
            "宣布": "announced",
            "推出": "launched",
            "发布": "released",
            "更新": "updated",
            "升级": "upgraded",
            "部署": "deployed",
            "集成": "integrated",
            "合作": "partnered",
            "收购": "acquired",
            "投资": "invested",
            "融资": "raised funding",
            "上市": "listed",
            "支持": "supports",
            "采用": "adopted",
            "暂停": "suspended",
            "恢复": "resumed",
            "关闭": "closed",
            "开放": "opened",
            
            # 其他
            "用户": "users",
            "开发者": "developers",
            "团队": "team",
            "社区": "community",
            "项目": "project",
            "平台": "platform",
            "网络": "network",
            "系统": "system",
            "服务": "service",
            "功能": "feature",
            "应用": "application",
            "工具": "tool",
            "API": "API",
            "SDK": "SDK",
            "文档": "documentation",
            "教程": "tutorial",
            "指南": "guide",
            "说明": "instructions"
        }
        
        self.en_to_zh = {v: k for k, v in self.zh_to_en.items()}
    
    def translate_to_english(self, text: str) -> str:
        """将中文翻译成英文"""
        if not text:
            return ""
            
        translated = text
        
        # 按长度排序，先替换长词组
        sorted_terms = sorted(self.zh_to_en.items(), key=lambda x: len(x[0]), reverse=True)
        
        for zh_term, en_term in sorted_terms:
            # 使用词边界匹配，避免部分匹配
            pattern = r'\b' + re.escape(zh_term) + r'\b'
            translated = re.sub(pattern, en_term, translated)
        
        return translated
    
    def translate_to_chinese(self, text: str) -> str:
        """将英文翻译成中文"""
        if not text:
            return ""
            
        translated = text
        
        # 按长度排序，先替换长词组
        sorted_terms = sorted(self.en_to_zh.items(), key=lambda x: len(x[0]), reverse=True)
        
        for en_term, zh_term in sorted_terms:
            # 使用词边界匹配
            pattern = r'\b' + re.escape(en_term) + r'\b'
            translated = re.sub(pattern, zh_term, translated, flags=re.IGNORECASE)
        
        return translated
    
    def get_bilingual_content(self, text: str) -> Dict[str, str]:
        """获取双语内容"""
        # 检测主要语言
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        en_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if zh_chars > en_chars:
            # 原文是中文
            return {
                "zh": text,
                "en": self.translate_to_english(text)
            }
        else:
            # 原文是英文
            return {
                "en": text,
                "zh": self.translate_to_chinese(text)
            }

# 全局翻译实例
translator = SimpleTranslator()