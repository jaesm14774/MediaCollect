"""
測試 Twitter Hashtag Collector
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from platforms.twitter_collector import TwitterHashtagCollector
from config.platform_config import APIFY_TOKEN

def test_twitter_hashtag():
    """測試 Twitter Hashtag 收集"""
    
    if not APIFY_TOKEN:
        print("錯誤: 未設定 APIFY_TOKEN")
        return
    
    # 測試 hashtag
    test_hashtag = "timelessbruno"
    
    print("=" * 60)
    print(f"測試 Twitter Hashtag 收集器")
    print("=" * 60)
    print(f"Hashtag: #{test_hashtag}")
    print(f"API Token: {APIFY_TOKEN[:20]}...")
    print("=" * 60)
    
    # 建立收集器
    collector = TwitterHashtagCollector(
        hashtag=test_hashtag,
        api_token=APIFY_TOKEN,
        results_limit=10  # 測試時只抓 10 筆
    )
    
    # 執行收集
    print("\n開始收集...")
    result = collector.collect_hashtag()
    
    # 顯示結果
    print("\n" + "=" * 60)
    print("收集結果")
    print("=" * 60)
    print(f"成功: {result.success}")
    print(f"貼文數: {len(result.posts)}")
    print(f"執行時長: {result.duration_seconds} 秒")
    
    if not result.success:
        print(f"錯誤訊息: {result.error_message}")
    else:
        # 顯示前 3 筆貼文
        print("\n前 3 筆貼文:")
        for i, post in enumerate(result.posts[:3], 1):
            print(f"\n{i}. {post.author_username} (@{post.author_id})")
            print(f"   內容: {post.text[:100]}...")
            print(f"   讚數: {post.like_count}, 回覆數: {post.comment_count}")
            print(f"   URL: {post.post_url}")
            print(f"   Hashtags: {post.hashtags}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_twitter_hashtag()

