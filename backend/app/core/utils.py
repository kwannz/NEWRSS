"""
Core utility functions for the application
"""
import hashlib
import re
from typing import Optional


def generate_hash(content: str) -> str:
    """
    Generate SHA-256 hash of content for deduplication
    
    Args:
        content: String content to hash
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def validate_email(email: str) -> bool:
    """
    Validate email format using regex
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length
        
    Returns:
        Truncated text with ellipsis if necessary
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def sanitize_html(text: str) -> str:
    """
    Basic HTML sanitization - remove common HTML tags
    
    Args:
        text: Text that may contain HTML
        
    Returns:
        Text with HTML tags removed
    """
    if not text:
        return ""
    
    # Remove common HTML tags
    import re
    html_pattern = re.compile(r'<[^>]+>')
    return html_pattern.sub('', text)


def format_importance_score(score: int) -> str:
    """
    Format importance score as descriptive text
    
    Args:
        score: Numeric importance score (1-5)
        
    Returns:
        Descriptive importance level
    """
    score_map = {
        1: "Very Low",
        2: "Low", 
        3: "Medium",
        4: "High",
        5: "Critical"
    }
    
    return score_map.get(score, "Unknown")


def extract_price_mentions(text: str) -> list[str]:
    """
    Extract price mentions from text (simple pattern matching)
    
    Args:
        text: Text to search for price mentions
        
    Returns:
        List of found price strings
    """
    if not text:
        return []
    
    # Pattern for common price formats: $1000, $1,000, $1.5K, etc.
    price_pattern = r'\$[\d,]+(?:\.\d{1,2})?[KMB]?'
    prices = re.findall(price_pattern, text, re.IGNORECASE)
    
    return list(set(prices))  # Remove duplicates


def calculate_content_similarity(content1: str, content2: str) -> float:
    """
    Calculate simple content similarity based on common words
    
    Args:
        content1: First content string
        content2: Second content string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not content1 or not content2:
        return 0.0
    
    # Simple word-based similarity
    words1 = set(content1.lower().split())
    words2 = set(content2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0