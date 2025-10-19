"""
Threads 收集器
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


class ThreadsCollector(ApifyBasedCollector):
    """
    Threads 資料收集器
    
    功能:
    - 抓取使用者資料
    - 抓取串文 (threads)
    - 下載媒體檔案
    
    Apify Actors:
    - apify/threads-scraper (Threads 爬蟲)
    """
    
    # Apify Actor IDs
    THREADS_SCRAPER = "apify/threads-scraper"
    
    def __init__(self, username: str, api_token: str):
        """
        初始化 Threads 收集器
        
        參數:
            username: Threads 使用者名稱 (不含 @)
            api_token: Apify API Token
        """
        super().__init__(
            username=username, 
            api_token=api_token, 
            platform=PlatformType.THREADS
        )
        self.downloader = MediaDownloader()
    
    # =========================================================================
    # 實作抽象方法
    # =========================================================================
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """抓取使用者基本資料"""
        try:
            run_input = {
                "directUrls": [f"https://www.threads.net/@{self.username}"],
                "maxPostsPerProfile": 0  # 只抓取個人資料
            }
            
            items = self.call_apify_actor(self.THREADS_SCRAPER, run_input)
            
            if not items:
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            user = PlatformUser(
                platform=PlatformType.THREADS,
                user_id=raw.get('userId', ''),
                username=raw.get('username', self.username),
                display_name=raw.get('fullName', ''),
                is_verified=raw.get('isVerified', False),
                description=raw.get('bio', ''),
                profile_image_url=raw.get('profilePictureUrl'),
                follower_count=raw.get('followersCount', 0),
                post_count=raw.get('threadsCount', 0),
                external_url=raw.get('externalUrl'),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            return user
        
        except Exception as e:
            print(f"[Threads] 抓取使用者資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """抓取串文"""
        try:
            run_input = {
                "directUrls": [f"https://www.threads.net/@{self.username}"],
                "maxPostsPerProfile": limit
            }
            
            items = self.call_apify_actor(self.THREADS_SCRAPER, run_input)
            
            if not items:
                return []
            
            # 解析串文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            return posts
        
        except Exception as e:
            print(f"[Threads] 抓取串文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """
        Threads 目前沒有限時動態功能
        """
        return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """下載串文中的媒體檔案"""
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
            print(f"[Threads] 下載媒體失敗: {e}")
            return False
    
    # =========================================================================
    # 私有方法 - 資料解析
    # =========================================================================
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析串文資料"""
        try:
            # 基本資訊
            post_id = raw.get('threadId', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 時間資訊
            created_at = raw.get('timestamp')
            if isinstance(created_at, (int, float)):
                created_at = datetime.datetime.fromtimestamp(created_at)
            elif isinstance(created_at, str):
                try:
                    created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            
            # 建立串文物件
            post = SocialPost(
                platform=PlatformType.THREADS,
                post_id=post_id,
                content_type=ContentType.THREAD,
                author_id=raw.get('userId', ''),
                author_username=raw.get('username', self.username),
                author_display_name=raw.get('fullName'),
                text=raw.get('text', ''),
                like_count=raw.get('likesCount', 0),
                comment_count=raw.get('repliesCount', 0),
                share_count=raw.get('repostsCount', 0),
                created_at=created_at,
                post_url=raw.get('url'),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            return post
        
        except Exception as e:
            print(f"[Threads] 解析串文失敗: {e}")
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
        videos = raw.get('videos', [])
        for video in videos:
            if isinstance(video, dict):
                url = video.get('url')
                if url:
                    media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=url,
                        thumbnail_url=video.get('thumbnailUrl')
                    ))
            elif isinstance(video, str):
                media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=video
                ))
        
        return media_items

