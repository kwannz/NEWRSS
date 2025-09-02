#!/usr/bin/env python3
"""
Test script for the real-time news broadcasting pipeline
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.broadcast_service import BroadcastService
from app.core.logging import setup_logging, get_service_logger

async def test_broadcast_pipeline():
    """Test the complete news broadcasting pipeline"""
    
    # Setup logging
    setup_logging()
    logger = get_service_logger("test_broadcast")
    
    logger.info("Starting broadcast pipeline test")
    
    try:
        # Initialize broadcast service
        broadcast_service = BroadcastService()
        
        # Create test news items
        test_news_items = [
            {
                "title": "📊 Test: Bitcoin Reaches New All-Time High",
                "content": "Bitcoin has reached a new all-time high of $100,000, marking a historic milestone for the cryptocurrency market. This breakthrough comes amid increased institutional adoption and regulatory clarity. Market analysts predict continued growth as more companies add Bitcoin to their treasury reserves. The surge has also positively impacted other cryptocurrencies.",
                "url": f"https://example.com/btc-ath-test-{int(datetime.now().timestamp())}",
                "source": "Test News Source",
                "category": "bitcoin",
                "published_at": datetime.now(),
                "importance_score": 5,
                "is_urgent": False,
                "content_hash": f"test-btc-{int(datetime.now().timestamp())}"
            },
            {
                "title": "🚨 URGENT: Major Exchange Security Breach Reported",
                "content": "BREAKING: A major cryptocurrency exchange has reported a security breach affecting user funds. The exchange has temporarily halted all withdrawals while investigating. Users are advised to change passwords immediately. This is an urgent security alert requiring immediate attention from all crypto traders.",
                "url": f"https://example.com/security-breach-test-{int(datetime.now().timestamp())}",
                "source": "Security Alert System", 
                "category": "security",
                "published_at": datetime.now(),
                "importance_score": 5,
                "is_urgent": True,
                "content_hash": f"urgent-security-{int(datetime.now().timestamp())}"
            },
            {
                "title": "💼 Ethereum Upgrade Announcement",
                "content": "The Ethereum Foundation has announced the next major network upgrade scheduled for next quarter. The upgrade will include improvements to scalability and gas fee optimization. Developers are encouraged to test their applications on the testnet. This update represents a significant step forward for the Ethereum ecosystem.",
                "url": f"https://example.com/eth-upgrade-test-{int(datetime.now().timestamp())}",
                "source": "Ethereum Foundation",
                "category": "ethereum",
                "published_at": datetime.now(),
                "importance_score": 4,
                "is_urgent": False,
                "content_hash": f"eth-upgrade-{int(datetime.now().timestamp())}"
            }
        ]
        
        logger.info(f"Created {len(test_news_items)} test news items")
        
        # Process through the complete pipeline
        logger.info("Processing news items through broadcast pipeline...")
        
        pipeline_stats = await broadcast_service.process_and_broadcast_news(test_news_items)
        
        # Log results
        logger.info("Pipeline test completed successfully!")
        logger.info("Pipeline Statistics:")
        for key, value in pipeline_stats.items():
            logger.info(f"  {key}: {value}")
        
        # Get system statistics
        system_stats = await broadcast_service.get_broadcast_statistics()
        logger.info("System Statistics:")
        logger.info(f"  User Statistics: {system_stats.get('user_statistics', {})}")
        logger.info(f"  System Status: {system_stats.get('system_status', {})}")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}", exc_info=True)
        return False

async def test_user_filtering():
    """Test the user filtering system"""
    
    from app.services.user_filter_service import UserFilterService
    
    logger = get_service_logger("test_user_filter")
    logger.info("Testing user filtering system...")
    
    try:
        user_filter = UserFilterService()
        
        test_news = {
            "title": "Test News for Filtering",
            "content": "This is a test news item for user filtering.",
            "category": "test",
            "importance_score": 3,
            "is_urgent": False
        }
        
        # Test different delivery types
        for delivery_type in ["regular", "urgent", "digest"]:
            filtered_users = await user_filter.get_filtered_users_for_news(test_news, delivery_type)
            logger.info(f"  {delivery_type}: {len(filtered_users)} eligible users")
        
        return True
        
    except Exception as e:
        logger.error(f"User filtering test failed: {str(e)}", exc_info=True)
        return False

async def main():
    """Main test function"""
    
    logger = get_service_logger("test_main")
    logger.info("="*60)
    logger.info("🚀 Starting Real-Time Broadcasting Pipeline Tests")
    logger.info("="*60)
    
    tests = [
        ("User Filtering System", test_user_filtering),
        ("Complete Broadcast Pipeline", test_broadcast_pipeline),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"Running test: {test_name}")
        try:
            result = await test_func()
            results[test_name] = "PASS" if result else "FAIL"
            logger.info(f"Test '{test_name}': {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results[test_name] = f"ERROR: {str(e)}"
            logger.error(f"Test '{test_name}' error: {str(e)}", exc_info=True)
        
        logger.info("-" * 40)
    
    # Summary
    logger.info("="*60)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*60)
    
    for test_name, result in results.items():
        status_icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
        logger.info(f"{status_icon} {test_name}: {result}")
    
    passed_tests = sum(1 for result in results.values() if result == "PASS")
    total_tests = len(results)
    
    logger.info(f"")
    logger.info(f"Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Real-time broadcasting pipeline is ready.")
    else:
        logger.warning("⚠️  Some tests failed. Please check the logs above.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test runner failed: {str(e)}")
        sys.exit(1)