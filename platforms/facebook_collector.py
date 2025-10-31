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
from lib.logger import get_logger
from typing import List, Optional, Dict, Any
import datetime
import json
from config.platform_config import APIFY_ACTORS


class FacebookCollector(ApifyBasedCollector):
    """
    Facebook 資料收集器
    
    功能:
    - 抓取粉絲專頁資料
    - 抓取貼文
    - 抓取照片
    - 下載媒體檔案
    
    Apify Actors (適合 Free User):
    - apify/facebook-pages-scraper (粉絲專頁基本資料)
    - apify/facebook-posts-scraper (粉絲專頁貼文)
    - apify/facebook-photos-scraper (粉絲專頁照片)
    """
    
    # Apify Actor IDs
    PAGE_SCRAPER = APIFY_ACTORS['facebook']['profile']
    POST_SCRAPER = APIFY_ACTORS['facebook']['post']
    PHOTO_SCRAPER = APIFY_ACTORS['facebook']['photo']
    
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
        self.logger = get_logger('FacebookCollector')
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """
        抓取粉絲專頁基本資料
        使用 apify/facebook-pages-scraper
        """
        try:
            page_url = f"https://www.facebook.com/{self.username}"
            run_input = {"startUrls": [{"url": page_url}]}
            
            self.logger.info(f"正在抓取粉絲專頁資料: {page_url}")
            items = self.call_apify_actor(self.PAGE_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得粉絲專頁資料: {self.username}")
                return None
            
            raw = items[0]
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            user = PlatformUser(
                platform=PlatformType.FACEBOOK,
                user_id=raw.get('pageId') or raw.get('facebookId', ''),
                username=raw.get('pageName', self.username),
                display_name=raw.get('title', ''),
                is_verified=self._check_verified(raw),
                description=self._get_description(raw),
                profile_image_url=raw.get('profilePictureUrl'),
                banner_image_url=raw.get('coverPhotoUrl'),
                category=self._get_categories(raw),
                follower_count=raw.get('likes') or raw.get('followers', 0),
                following_count=raw.get('followings', 0),
                external_url=raw.get('website'),
                email=raw.get('email'),
                phone=raw.get('phone'),
                location=raw.get('address'),
                raw_data=raw_data_json
            )
            
            self.logger.info(f"成功抓取粉絲專頁: {user.display_name} (@{user.username})")
            return user
        
        except Exception as e:
            self.logger.error(f"抓取粉絲專頁資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _check_verified(self, raw: Dict[str, Any]) -> bool:
        """檢查是否為認證專頁"""
        # 檢查多個可能的認證欄位
        if raw.get('verified'):
            return True
        if raw.get('CONFIRMED_OWNER_LABEL'):
            return True
        return False
    
    def _get_description(self, raw: Dict[str, Any]) -> str:
        """取得專頁描述"""
        # 優先使用 intro，其次使用 about
        if raw.get('intro'):
            return raw['intro']
        if raw.get('about_me') and isinstance(raw['about_me'], dict):
            return raw['about_me'].get('text', '')
        return ''
    
    def _get_categories(self, raw: Dict[str, Any]) -> str:
        """取得專頁分類"""
        categories = raw.get('categories', [])
        if categories and isinstance(categories, list):
            # 過濾掉 "Page" 這個通用分類
            filtered = [c for c in categories if c != "Page"]
            return ', '.join(filtered) if filtered else ''
        return ''
    
    def fetch_posts(
        self, 
        limit: int = 50,
        only_posts_newer_than: Optional[str] = None,
        only_posts_older_than: Optional[str] = None,
        caption_text: bool = False
    ) -> List[SocialPost]:
        """
        抓取粉絲專頁貼文
        使用 apify/facebook-posts-scraper
        
        參數:
            limit: 抓取貼文數量限制
            only_posts_newer_than: 只抓取此日期之後的貼文
                                   格式: YYYY-MM-DD (如 "2024-01-01")
                                   或相對時間 (如 "1 day", "2 months", "3 years")
                                   或完整 ISO 時間戳 (如 "2025-09-23T10:02:01")
            only_posts_older_than: 只抓取此日期之前的貼文
                                   格式同上
            caption_text: 是否提取影片字幕 (預設 False)
        """
        try:
            page_url = f"https://www.facebook.com/{self.username}"
            run_input = {
                "startUrls": [{"url": page_url}],
                "resultsLimit": limit
            }
            
            if only_posts_newer_than:
                run_input["onlyPostsNewerThan"] = only_posts_newer_than
            if only_posts_older_than:
                run_input["onlyPostsOlderThan"] = only_posts_older_than
            if caption_text:
                run_input["captionText"] = True
            
            time_range_info = ""
            if only_posts_newer_than or only_posts_older_than:
                time_range_parts = []
                if only_posts_newer_than:
                    time_range_parts.append(f"newer than {only_posts_newer_than}")
                if only_posts_older_than:
                    time_range_parts.append(f"older than {only_posts_older_than}")
                time_range_info = f" [{', '.join(time_range_parts)}]"
            
            self.logger.info(f"正在抓取貼文 (limit={limit}{time_range_info}): {page_url}")
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得任何貼文: {self.username}")
                return []
            
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            self.logger.info(f"成功抓取 {len(posts)} 則貼文")
            return posts
        
        except Exception as e:
            self.logger.error(f"抓取貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_photos(self, limit: int = 10) -> List[SocialPost]:
        """
        抓取粉絲專頁照片
        使用 apify/facebook-photos-scraper
        """
        try:
            page_url = f"https://www.facebook.com/{self.username}"
            run_input = {
                "startUrls": [{"url": page_url}],
                "resultsLimit": limit
            }
            
            self.logger.info(f"正在抓取照片 (limit={limit}): {page_url}")
            items = self.call_apify_actor(self.PHOTO_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得任何照片: {self.username}")
                return []
            
            posts = []
            for item in items:
                post = self._parse_photo(item)
                if post:
                    posts.append(post)
            
            self.logger.info(f"成功抓取 {len(posts)} 張照片")
            return posts
        
        except Exception as e:
            self.logger.error(f"抓取照片失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """
        抓取 Facebook 限時動態
        
        注意: Facebook 限時動態需要登入，Apify 公開 Actor 可能無法抓取
        """
        self.logger.warning("Facebook 限時動態抓取功能尚未實作（需要登入）")
        return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        try:
            user_dir = os.path.join(save_dir, self.username)
            os.makedirs(user_dir, exist_ok=True)
            
            success_count = 0
            for index, media in enumerate(post.media_items):
                ext = 'mp4' if media.media_type == MediaType.VIDEO else 'jpg'
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(user_dir, filename)
                
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
        """
        解析貼文資料（from apify/facebook-posts-scraper）
        """
        try:
            post_id = raw.get('postId') or raw.get('postFacebookId', '')
            if not post_id:
                self.logger.debug("跳過沒有 postId 的項目")
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            created_at = self._parse_timestamp(raw)
            
            post = SocialPost(
                platform=PlatformType.FACEBOOK,
                post_id=post_id,
                content_type=ContentType.POST,
                author_id=raw.get('pageId') or raw.get('facebookId', ''),
                author_username=self.username,
                author_display_name=raw.get('pageName'),
                text=raw.get('text', ''),
                like_count=raw.get('likes', 0),
                comment_count=raw.get('comments', 0),
                share_count=raw.get('shares', 0),
                created_at=created_at,
                post_url=raw.get('url') or raw.get('topLevelUrl'),
                raw_data=raw_data_json
            )
            
            post.media_items = self._parse_post_media(raw)
            return post
        
        except Exception as e:
            self.logger.error(f"解析貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_photo(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """
        解析照片資料（from apify/facebook-photos-scraper）
        """
        try:
            photo_url = raw.get('url', '')
            photo_id = raw.get('id', '')
            
            if not photo_id and not photo_url:
                self.logger.debug("跳過沒有 ID 的照片")
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            post = SocialPost(
                platform=PlatformType.FACEBOOK,
                post_id=photo_id or photo_url,
                content_type=ContentType.POST,
                author_id='',  # photo scraper 不提供 pageId
                author_username=self.username,
                text=raw.get('ocrText', ''),  # 使用 OCR 識別的文字
                like_count=0,
                comment_count=0,
                share_count=0,
                post_url=photo_url,
                raw_data=raw_data_json
            )
            
            image_url = raw.get('image')
            if image_url:
                post.media_items = [MediaItem(
                    media_type=MediaType.IMAGE,
                    url=image_url
                )]
            
            return post
        
        except Exception as e:
            self.logger.error(f"解析照片失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_timestamp(self, raw: Dict[str, Any]) -> Optional[datetime.datetime]:
        """解析時間戳記"""
        timestamp = raw.get('timestamp')
        if timestamp:
            try:
                return datetime.datetime.fromtimestamp(timestamp / 1000.0)
            except:
                pass
        
        time_str = raw.get('time')
        if time_str and isinstance(time_str, str):
            try:
                return datetime.datetime.strptime(time_str, "%A, %d %B %Y at %H:%M")
            except:
                try:
                    return datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except:
                    pass
        
        return None
    
    def _parse_post_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """
        解析貼文中的媒體項目
        支援多種媒體格式（圖片、影片、縮圖等）
        """
        media_items = []
        
        media_array = raw.get('media', [])
        if media_array and isinstance(media_array, list):
            for media_obj in media_array:
                if not isinstance(media_obj, dict):
                    continue
                
                typename = media_obj.get('__typename', '')
                is_playable = media_obj.get('is_playable', False)
                
                if typename == 'Video' or is_playable:
                    video_url = media_obj.get('playable_url') or media_obj.get('video_url')
                    if video_url:
                        thumbnail = media_obj.get('thumbnail') or media_obj.get('photo_image', {}).get('uri')
                        media_items.append(MediaItem(
                            media_type=MediaType.VIDEO,
                            url=video_url,
                            thumbnail_url=thumbnail
                        ))
                        continue
                
                if typename == 'Photo' or 'photo_image' in media_obj or 'image' in media_obj:
                    image_url = None
                    thumbnail_url = None
                    
                    if 'photo_image' in media_obj and isinstance(media_obj['photo_image'], dict):
                        image_url = media_obj['photo_image'].get('uri')
                    elif 'image' in media_obj and isinstance(media_obj['image'], dict):
                        image_url = media_obj['image'].get('uri')
                    elif 'url' in media_obj and isinstance(media_obj['url'], str):
                        url_str = media_obj['url']
                        if any(ext in url_str.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'fbcdn.net']):
                            image_url = url_str
                    
                    thumbnail_url = media_obj.get('thumbnail')
                    
                    if image_url:
                        media_items.append(MediaItem(
                            media_type=MediaType.IMAGE,
                            url=image_url,
                            thumbnail_url=thumbnail_url or image_url
                        ))
        
        if not media_items:
            thumb_url = raw.get('thumb')
            if thumb_url:
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=thumb_url,
                    thumbnail_url=thumb_url
                ))
            
            link_url = raw.get('link')
            if link_url and link_url not in [m.url for m in media_items]:
                if any(ext in link_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    media_items.append(MediaItem(
                        media_type=MediaType.IMAGE,
                        url=link_url
                    ))
            
            images = raw.get('images', [])
            for image_url in images:
                if image_url and image_url not in [m.url for m in media_items]:
                    media_items.append(MediaItem(
                        media_type=MediaType.IMAGE,
                        url=image_url
                    ))
            
            video_url = raw.get('video')
            if video_url:
                media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=video_url,
                    thumbnail_url=thumb_url
                ))
        
        return media_items

