"""
Twitter(X) 收集器
基於 Apify API 實作
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_collector import ApifyBasedCollector
from core.data_models import (
    PlatformType, PlatformUser, SocialPost, 
    MediaItem, MediaType, ContentType
)
from lib.media_downloader import MediaDownloader
from typing import List, Optional, Dict, Any
import datetime


class TwitterCollector(ApifyBasedCollector):
    """
    Twitter(X) 資料收集器
    
    功能:
    - 抓取使用者資料
    - 抓取推文
    - 下載媒體檔案
    
    Apify Actors:
    - apify/twitter-scraper (Twitter 爬蟲)
    - apify/tweet-scraper (推文爬蟲)
    """
    
    # Apify Actor IDs
    TWITTER_SCRAPER = "apify/twitter-scraper"
    TWEET_SCRAPER = "apify/tweet-scraper"
    
    def __init__(self, username: str, api_token: str):
        """
        初始化 Twitter 收集器
        
        參數:
            username: Twitter 使用者名稱 (不含 @)
            api_token: Apify API Token
        """
        super().__init__(
            username=username, 
            api_token=api_token, 
            platform=PlatformType.TWITTER
        )
        self.downloader = MediaDownloader()
    
    # =========================================================================
    # 實作抽象方法
    # =========================================================================
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """抓取使用者基本資料"""
        try:
            run_input = {
                "handles": [self.username],
                "searchMode": "user",
                "maxItems": 1
            }
            
            items = self.call_apify_actor(self.TWITTER_SCRAPER, run_input)
            
            if not items:
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            author = raw.get('author', {})
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            user = PlatformUser(
                platform=PlatformType.TWITTER,
                user_id=author.get('id', ''),
                username=author.get('userName', self.username),
                display_name=author.get('name', ''),
                is_verified=author.get('isVerified', False) or author.get('isBlueVerified', False),
                description=author.get('description', ''),
                profile_image_url=author.get('profilePicture'),
                banner_image_url=author.get('banner'),
                follower_count=author.get('followers', 0),
                following_count=author.get('following', 0),
                post_count=author.get('tweets', 0),
                external_url=author.get('url'),
                location=author.get('location'),
                created_at=self._parse_twitter_date(author.get('createdAt')),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            return user
        
        except Exception as e:
            print(f"[Twitter] 抓取使用者資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """抓取推文"""
        try:
            run_input = {
                "handles": [self.username],
                "tweetsDesired": limit,
                "searchMode": "user"
            }
            
            items = self.call_apify_actor(self.TWITTER_SCRAPER, run_input)
            
            if not items:
                return []
            
            # 解析推文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            return posts
        
        except Exception as e:
            print(f"[Twitter] 抓取推文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """
        Twitter 沒有限時動態功能
        """
        return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """下載推文中的媒體檔案"""
        try:
            # 建立使用者目錄
            user_dir = os.path.join(save_dir, self.username)
            os.makedirs(user_dir, exist_ok=True)
            
            # 下載所有媒體
            success_count = 0
            for index, media in enumerate(post.media_items):
                # 決定副檔名
                if media.media_type == MediaType.VIDEO:
                    ext = 'mp4'
                else:
                    ext = 'jpg'
                
                # 建立檔名
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(user_dir, filename)
                
                # 下載
                if self.downloader.download(media.url, file_path):
                    media.local_path = file_path
                    success_count += 1
            
            return success_count > 0
        
        except Exception as e:
            print(f"[Twitter] 下載媒體失敗: {e}")
            return False
    
    # =========================================================================
    # 私有方法 - 資料解析
    # =========================================================================
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析推文資料"""
        try:
            # 基本資訊
            post_id = raw.get('id', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            author = raw.get('author', {})
            
            # 判斷內容類型
            is_retweet = raw.get('isRetweet', False)
            content_type = ContentType.RETWEET if is_retweet else ContentType.TWEET
            
            # 建立推文物件
            post = SocialPost(
                platform=PlatformType.TWITTER,
                post_id=post_id,
                content_type=content_type,
                author_id=author.get('id', ''),
                author_username=author.get('userName', self.username),
                author_display_name=author.get('name'),
                text=raw.get('text', ''),
                language=raw.get('lang'),
                like_count=raw.get('likeCount', 0),
                comment_count=raw.get('replyCount', 0),
                share_count=raw.get('retweetCount', 0),
                view_count=raw.get('viewCount', 0),
                bookmark_count=raw.get('bookmarkCount', 0),
                created_at=self._parse_twitter_date(raw.get('createdAt')),
                post_url=raw.get('url'),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            # 解析標籤和提及
            post.hashtags = [tag.get('text', '') for tag in raw.get('hashtags', [])]
            post.mentions = [mention.get('userName', '') for mention in raw.get('mentions', [])]
            
            return post
        
        except Exception as e:
            print(f"[Twitter] 解析推文失敗: {e}")
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析媒體項目"""
        media_items = []
        
        # 照片
        photos = raw.get('photos', [])
        for photo in photos:
            url = photo.get('url')
            if url:
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=url,
                    width=photo.get('width'),
                    height=photo.get('height')
                ))
        
        # 影片
        videos = raw.get('videos', [])
        for video in videos:
            url = video.get('url')
            if url:
                media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=url,
                    thumbnail_url=video.get('thumbnail'),
                    duration=video.get('duration'),
                    width=video.get('width'),
                    height=video.get('height')
                ))
        
        return media_items
    
    def _parse_twitter_date(self, date_str: Optional[str]) -> Optional[datetime.datetime]:
        """解析 Twitter 日期格式"""
        if not date_str:
            return None
        
        try:
            return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None

