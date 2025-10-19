"""
Facebook 收集器
基於 Apify API 實作
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_collector import ApifyBasedCollector
from core.data_models import (
    PlatformType, PlatformUser, SocialPost, 
    MediaItem, MediaType, ContentType
)
from lib.media_downloader import MediaDownloader
from typing import List, Optional, Dict, Any
import datetime
import json


class FacebookCollector(ApifyBasedCollector):
    """
    Facebook 資料收集器
    
    功能:
    - 抓取粉絲專頁資料
    - 抓取貼文
    - 下載媒體檔案
    
    Apify Actors:
    - apify/facebook-pages-scraper (粉絲專頁爬蟲)
    - apify/facebook-posts-scraper (貼文爬蟲)
    """
    
    # Apify Actor IDs
    PAGE_SCRAPER = "apify/facebook-pages-scraper"
    POST_SCRAPER = "apify/facebook-posts-scraper"
    
    def __init__(self, username: str, api_token: str):
        """
        初始化 Facebook 收集器
        
        參數:
            username: Facebook 粉絲專頁名稱或 ID
            api_token: Apify API Token
        """
        super().__init__(
            username=username, 
            api_token=api_token, 
            platform=PlatformType.FACEBOOK
        )
        self.downloader = MediaDownloader()
    
    # =========================================================================
    # 實作抽象方法
    # =========================================================================
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """抓取粉絲專頁基本資料"""
        try:
            run_input = {
                "startUrls": [f"https://www.facebook.com/{self.username}"],
                "maxPosts": 0  # 只抓取專頁資訊，不抓貼文
            }
            
            items = self.call_apify_actor(self.PAGE_SCRAPER, run_input)
            
            if not items:
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            user = PlatformUser(
                platform=PlatformType.FACEBOOK,
                user_id=raw.get('pageId', ''),
                username=raw.get('username', self.username),
                display_name=raw.get('title') or raw.get('name', ''),
                is_verified=raw.get('verified', False),
                description=raw.get('about', ''),
                profile_image_url=raw.get('profilePicture'),
                banner_image_url=raw.get('coverPhoto'),
                category=raw.get('category'),
                follower_count=raw.get('likes', 0),  # Facebook 的「讚」相當於追蹤數
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            return user
        
        except Exception as e:
            print(f"[Facebook] 抓取粉絲專頁資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """抓取粉絲專頁貼文"""
        try:
            run_input = {
                "startUrls": [f"https://www.facebook.com/{self.username}"],
                "maxPosts": limit
            }
            
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)
            
            if not items:
                return []
            
            # 解析貼文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            return posts
        
        except Exception as e:
            print(f"[Facebook] 抓取貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """
        抓取 Facebook 限時動態
        
        注意: Facebook 限時動態需要登入，Apify 公開 Actor 可能無法抓取
        """
        print("[Facebook] 警告: Facebook 限時動態抓取功能尚未實作")
        return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """下載貼文中的媒體檔案"""
        try:
            # 建立粉絲專頁目錄
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
            print(f"[Facebook] 下載媒體失敗: {e}")
            return False
    
    # =========================================================================
    # 私有方法 - 資料解析
    # =========================================================================
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析貼文資料"""
        try:
            # 基本資訊
            post_id = raw.get('postId', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 時間資訊
            created_at = raw.get('time')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            
            # 建立貼文物件
            post = SocialPost(
                platform=PlatformType.FACEBOOK,
                post_id=post_id,
                content_type=ContentType.POST,
                author_id=raw.get('pageId', ''),
                author_username=self.username,
                text=raw.get('text', ''),
                like_count=raw.get('likes', 0),
                comment_count=raw.get('comments', 0),
                share_count=raw.get('shares', 0),
                created_at=created_at,
                post_url=raw.get('url'),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            return post
        
        except Exception as e:
            print(f"[Facebook] 解析貼文失敗: {e}")
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析媒體項目"""
        media_items = []
        
        # 圖片
        images = raw.get('images', [])
        for image_url in images:
            if image_url:
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=image_url
                ))
        
        # 影片
        video_url = raw.get('video')
        if video_url:
            media_items.append(MediaItem(
                media_type=MediaType.VIDEO,
                url=video_url
            ))
        
        return media_items

