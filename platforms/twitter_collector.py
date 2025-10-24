"""
Twitter(X) 收集器
基於 Apify API 實作

功能:
- 抓取使用者資料 (deepanshusharm/twitter-profile-scraper-no-cookies)
- 抓取使用者推文 (xtdata/twitter-x-scraper)
- Hashtag 搜尋 (xtdata/twitter-x-scraper)
- 進階搜尋 (支援 Twitter Advanced Search 操作符)
- 下載媒體檔案
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_collector import ApifyBasedCollector
from core.data_models import (
    PlatformType, PlatformUser, SocialPost, HashtagPost,
    MediaItem, MediaType, ContentType, HashtagCollectionResult
)
from lib.media_downloader import MediaDownloader
from lib.logger import get_logger
from typing import List, Optional, Dict, Any
import datetime


class TwitterCollector(ApifyBasedCollector):
    """
    Twitter(X) 資料收集器
    
    功能:
    - 抓取使用者資料
    - 抓取使用者推文
    - 下載媒體檔案
    
    Apify Actors:
    - deepanshusharm/twitter-profile-scraper-no-cookies (用戶資料)
    - xtdata/twitter-x-scraper (推文抓取)
    """
    
    # Apify Actor IDs
    PROFILE_SCRAPER = "deepanshusharm/twitter-profile-scraper-no-cookies"
    POST_SCRAPER = "xtdata/twitter-x-scraper"
    
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
        self.logger = get_logger('TwitterCollector')
    
    # =========================================================================
    # 實作抽象方法
    # =========================================================================
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """
        抓取使用者基本資料
        使用 deepanshusharm/twitter-profile-scraper-no-cookies
        """
        try:
            run_input = {
                "usernames": [self.username]
            }
            
            self.logger.info(f"正在抓取 Twitter 用戶資料: @{self.username}")
            items = self.call_apify_actor(self.PROFILE_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得用戶資料: @{self.username}")
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 解析 website 物件
            website_url = None
            if raw.get('website'):
                if isinstance(raw['website'], dict):
                    website_url = raw['website'].get('expanded_url') or raw['website'].get('display_url')
                else:
                    website_url = raw.get('website')
            
            user = PlatformUser(
                platform=PlatformType.TWITTER,
                user_id=raw.get('user_id') or raw.get('username', self.username),  # 如果沒有 user_id，使用 username
                username=raw.get('username', self.username),
                display_name=raw.get('display_name', ''),
                is_verified=raw.get('verified', False),
                description=raw.get('bio', ''),
                profile_image_url=raw.get('profile_image_url'),
                banner_image_url=raw.get('banner_image_url'),
                follower_count=raw.get('followers_count', 0),
                following_count=raw.get('following_count', 0),
                post_count=raw.get('posts_count', 0) or raw.get('tweet_count', 0),
                external_url=website_url,
                location=raw.get('location'),
                created_at=self._parse_twitter_date(raw.get('joined_date')),
                raw_data=raw_data_json
            )
            
            self.logger.info(f"成功抓取用戶: {user.display_name} (@{user.username})")
            return user
        
        except Exception as e:
            self.logger.error(f"抓取使用者資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_posts(self, limit: int = 50, only_posts_newer_than: Optional[str] = None, only_posts_older_than: Optional[str] = None, **kwargs) -> List[SocialPost]:
        """
        抓取使用者推文
        使用 xtdata/twitter-x-scraper
        
        參數:
            limit: 抓取推文數量限制
            only_posts_newer_than: 只抓取此日期之後的貼文 (格式: YYYY-MM-DD)
            only_posts_older_than: 只抓取此日期之前的貼文 (格式: YYYY-MM-DD)
        """
        try:
            # 建構基本搜尋詞
            search_term = f"from:{self.username}"
            
            # 加入時間過濾條件
            if only_posts_newer_than:
                # 將日期格式轉換為 YYYY-MM-DD（如果是相對時間則需要轉換）
                date_str = self._parse_date_string(only_posts_newer_than)
                if date_str:
                    search_term += f" since:{date_str}"
                    self.logger.info(f"  - 時間過濾: 只抓取 {date_str} 之後的貼文")
            
            if only_posts_older_than:
                # 將日期格式轉換為 YYYY-MM-DD（如果是相對時間則需要轉換）
                date_str = self._parse_date_string(only_posts_older_than)
                if date_str:
                    search_term += f" until:{date_str}"
                    self.logger.info(f"  - 時間過濾: 只抓取 {date_str} 之前的貼文")
            
            run_input = {
                "searchTerms": [search_term],
                "maxItems": limit,
                "sort": "Latest"  # 最新優先
            }
            
            self.logger.info(f"正在抓取推文 (limit={limit}): @{self.username}")
            self.logger.debug(f"搜尋條件: {search_term}")
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得任何推文: @{self.username}")
                return []
            
            # 解析推文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            self.logger.info(f"成功抓取 {len(posts)} 則推文")
            return posts
        
        except Exception as e:
            self.logger.error(f"抓取推文失敗: {e}")
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
                elif media.media_type == MediaType.IMAGE:
                    # 從 URL 判斷圖片格式，預設為 jpg
                    url_lower = media.url.lower()
                    if '.png' in url_lower:
                        ext = 'png'
                    elif '.gif' in url_lower:
                        ext = 'gif'
                    elif '.webp' in url_lower:
                        ext = 'webp'
                    else:
                        ext = 'jpg'
                else:
                    ext = 'jpg'
                
                # 建立檔名
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(user_dir, filename)
                
                # 下載
                if self.downloader.download(media.url, file_path):
                    media.local_path = file_path
                    success_count += 1
                    self.logger.debug(f"成功下載媒體: {filename}")
                else:
                    self.logger.warning(f"下載媒體失敗: {media.url}")
            
            if success_count > 0:
                self.logger.info(f"成功下載 {success_count}/{len(post.media_items)} 個媒體檔案")
            
            return success_count > 0
        
        except Exception as e:
            self.logger.error(f"下載媒體失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # =========================================================================
    # 私有方法 - 資料解析
    # =========================================================================
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析推文資料 (from xtdata/twitter-x-scraper)"""
        try:
            # 基本資訊 - 支援多種欄位名稱格式
            post_id = raw.get('id') or raw.get('tweetId') or raw.get('id_str', '')
            if not post_id:
                self.logger.debug("跳過沒有 id/tweetId 的項目")
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 判斷內容類型
            is_retweet = raw.get('isRetweet', False) or raw.get('retweeted', False)
            is_reply = raw.get('isReply', False)
            is_quote = raw.get('is_quote_status', False)
            
            if is_retweet:
                content_type = ContentType.RETWEET
            elif is_reply:
                content_type = ContentType.TWEET  # 回覆也算推文
            else:
                content_type = ContentType.TWEET
            
            # 從 author 物件或頂層欄位取得作者資訊
            author_info = raw.get('author', {})
            author_id = raw.get('authorId') or raw.get('user_id_str') or author_info.get('id_str', '')
            author_username = raw.get('username') or author_info.get('screen_name', self.username)
            author_display_name = raw.get('name') or author_info.get('name')
            
            # 建立推文物件
            post = SocialPost(
                platform=PlatformType.TWITTER,
                post_id=str(post_id),
                content_type=content_type,
                author_id=str(author_id),
                author_username=author_username,
                author_display_name=author_display_name,
                text=raw.get('text') or raw.get('full_text', ''),
                language=raw.get('lang'),
                like_count=raw.get('likeCount') or raw.get('favorite_count', 0),
                comment_count=raw.get('replyCount') or raw.get('reply_count', 0),
                share_count=raw.get('retweetCount') or raw.get('retweet_count', 0),
                view_count=raw.get('viewCount', 0),
                bookmark_count=raw.get('bookmarkCount') or raw.get('bookmark_count', 0),
                created_at=self._parse_twitter_date(raw.get('createdAt') or raw.get('created_at')),
                post_url=raw.get('url') or raw.get('twitterUrl'),
                raw_data=raw_data_json
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            # 解析標籤和提及 - 支援多種格式
            # 格式 1: 直接的 hashtags 陣列
            post.hashtags = raw.get('hashtags', [])
            
            # 格式 2: entities.hashtags 陣列
            if not post.hashtags:
                entities = raw.get('entities', {})
                hashtag_objs = entities.get('hashtags', [])
                post.hashtags = [h.get('text', h) if isinstance(h, dict) else h for h in hashtag_objs]
            
            # 提及
            post.mentions = raw.get('mentions', [])
            if not post.mentions:
                entities = raw.get('entities', {})
                mention_objs = entities.get('user_mentions', [])
                post.mentions = [m.get('screen_name', m) if isinstance(m, dict) else m for m in mention_objs]
            
            return post
        
        except Exception as e:
            self.logger.error(f"解析推文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """
        解析媒體項目 (支援多種格式)
        優先順序: extended_entities > entities > photos/videos 欄位
        """
        media_items = []
        
        # 方法 1: 從 extended_entities.media 解析 (優先，最完整)
        extended_entities = raw.get('extended_entities', {})
        if extended_entities and isinstance(extended_entities, dict):
            media_list = extended_entities.get('media', [])
            if media_list:
                for media in media_list:
                    item = self._parse_media_entity(media)
                    if item:
                        media_items.append(item)
                return media_items  # 如果有 extended_entities，直接返回
        
        # 方法 2: 從 entities.media 解析
        entities = raw.get('entities', {})
        if entities and isinstance(entities, dict):
            media_list = entities.get('media', [])
            if media_list:
                for media in media_list:
                    item = self._parse_media_entity(media)
                    if item:
                        media_items.append(item)
                return media_items  # 如果有 entities.media，直接返回
        
        # 方法 3: 從簡化的 photos/videos 欄位解析 (備用格式)
        # 照片
        photos = raw.get('photos', [])
        if photos and isinstance(photos, list):
            for photo in photos:
                if isinstance(photo, dict):
                    url = photo.get('url')
                    if url:
                        media_items.append(MediaItem(
                            media_type=MediaType.IMAGE,
                            url=url,
                            width=photo.get('width'),
                            height=photo.get('height')
                        ))
                elif isinstance(photo, str):
                    # 有時候 photos 是字串數組
                    media_items.append(MediaItem(
                        media_type=MediaType.IMAGE,
                        url=photo
                    ))
        
        # 影片
        videos = raw.get('videos', [])
        if videos and isinstance(videos, list):
            for video in videos:
                if isinstance(video, dict):
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
                elif isinstance(video, str):
                    media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=video
                    ))
        
        return media_items
    
    def _parse_media_entity(self, media: Dict[str, Any]) -> Optional[MediaItem]:
        """
        解析單個媒體實體 (from entities 或 extended_entities)
        
        支援格式:
        - type: "photo" -> 照片
        - type: "video" -> 影片
        - type: "animated_gif" -> GIF
        """
        if not isinstance(media, dict):
            return None
        
        media_type_str = media.get('type', '')
        
        # 判斷媒體類型
        if media_type_str == 'photo':
            # 照片：使用 media_url_https
            url = media.get('media_url_https')
            if not url:
                return None
            
            # 獲取最大尺寸
            original_info = media.get('original_info', {})
            sizes = media.get('sizes', {})
            large_size = sizes.get('large', {})
            
            return MediaItem(
                media_type=MediaType.IMAGE,
                url=url,
                width=original_info.get('width') or large_size.get('w'),
                height=original_info.get('height') or large_size.get('h')
            )
        
        elif media_type_str in ['video', 'animated_gif']:
            # 影片或 GIF：從 video_info.variants 中選擇最高品質
            video_info = media.get('video_info', {})
            variants = video_info.get('variants', [])
            
            if not variants:
                return None
            
            # 選擇 mp4 格式且最高 bitrate 的版本
            best_variant = None
            max_bitrate = 0
            
            for variant in variants:
                content_type = variant.get('content_type', '')
                if content_type == 'video/mp4':
                    bitrate = variant.get('bitrate', 0)
                    if bitrate > max_bitrate:
                        max_bitrate = bitrate
                        best_variant = variant
            
            # 如果沒有找到 mp4，使用第一個可用的
            if not best_variant and variants:
                best_variant = variants[0]
            
            if not best_variant:
                return None
            
            url = best_variant.get('url')
            if not url:
                return None
            
            # 獲取縮圖和尺寸
            thumbnail_url = media.get('media_url_https')
            original_info = media.get('original_info', {})
            
            # 獲取影片時長（毫秒轉秒）
            duration_millis = video_info.get('duration_millis')
            duration = None
            if duration_millis:
                duration = duration_millis / 1000.0
            
            return MediaItem(
                media_type=MediaType.VIDEO,
                url=url,
                thumbnail_url=thumbnail_url,
                duration=duration,
                width=original_info.get('width'),
                height=original_info.get('height')
            )
        
        return None
    
    def _parse_twitter_date(self, date_str: Optional[str]) -> Optional[datetime.datetime]:
        """解析 Twitter 日期格式"""
        if not date_str:
            return None
        
        try:
            # 嘗試 ISO 格式
            return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        
        try:
            # 嘗試 Twitter API 格式: "Wed Feb 05 06:17:13 +0000 2025"
            return datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        except:
            pass
        
        try:
            # 嘗試常見的日期格式 (如 "Joined December 2020")
            if 'Joined' in date_str:
                date_str = date_str.replace('Joined ', '')
            return datetime.datetime.strptime(date_str, "%B %Y")
        except:
            pass
        
        # 無法解析時回傳 None
        return None
    
    def _parse_date_string(self, date_input: str) -> Optional[str]:
        """
        解析日期字串並轉換為 YYYY-MM-DD 格式
        
        支援格式:
        - YYYY-MM-DD (直接返回)
        - "1 day", "2 weeks", "3 months", "1 year" (相對日期)
        
        參數:
            date_input: 日期字串
        
        返回:
            YYYY-MM-DD 格式的日期字串，若解析失敗則返回 None
        """
        if not date_input:
            return None
        
        date_input = date_input.strip()
        
        # 檢查是否已經是 YYYY-MM-DD 格式
        try:
            parsed = datetime.datetime.strptime(date_input, "%Y-%m-%d")
            return date_input
        except:
            pass
        
        # 解析相對日期 (如 "1 day", "2 months")
        import re
        relative_pattern = r'^(\d+)\s+(day|days|week|weeks|month|months|year|years)$'
        match = re.match(relative_pattern, date_input.lower())
        
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            
            now = datetime.datetime.now()
            
            if unit in ['day', 'days']:
                target_date = now - datetime.timedelta(days=amount)
            elif unit in ['week', 'weeks']:
                target_date = now - datetime.timedelta(weeks=amount)
            elif unit in ['month', 'months']:
                # 近似計算：1個月 = 30天
                target_date = now - datetime.timedelta(days=amount * 30)
            elif unit in ['year', 'years']:
                # 近似計算：1年 = 365天
                target_date = now - datetime.timedelta(days=amount * 365)
            else:
                return None
            
            return target_date.strftime("%Y-%m-%d")
        
        # 嘗試其他常見格式
        for fmt in ["%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
            try:
                parsed = datetime.datetime.strptime(date_input, fmt)
                return parsed.strftime("%Y-%m-%d")
            except:
                pass
        
        self.logger.warning(f"無法解析日期格式: {date_input}")
        return None


class TwitterHashtagCollector(TwitterCollector):
    """
    Twitter Hashtag 收集器
    繼承自 TwitterCollector，僅覆寫 hashtag 特定的邏輯
    
    功能:
    - 根據 hashtag 搜尋推文
    - 重用 TwitterCollector 的所有解析邏輯
    """
    
    def __init__(self, hashtag: str, api_token: str, results_limit: int = 50, **kwargs):
        """
        初始化 Twitter Hashtag 收集器
        
        參數:
            hashtag: 要搜尋的 hashtag (可含或不含 # 符號)
            api_token: Apify API Token
            results_limit: 結果數量限制
        """
        # 移除開頭的 # 符號（如果有的話）
        clean_hashtag = hashtag.lstrip('#')
        
        # 使用 hashtag 作為 username (用於識別)
        super().__init__(
            username=clean_hashtag,
            api_token=api_token
        )
        self.hashtag = clean_hashtag
        self.results_limit = results_limit
        self.logger = get_logger('TwitterHashtagCollector')
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """Hashtag 收集器不需要用戶資料"""
        return None
    
    def fetch_posts(
        self,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort: str = "Top",
        **kwargs
    ) -> List[SocialPost]:
        """
        使用 Hashtag 搜尋推文

        參數:
            limit: 抓取推文數量限制
            start_date: 開始日期 (YYYY-MM-DD)，用於時間過濾
            end_date: 結束日期 (YYYY-MM-DD)，用於時間過濾
            sort: 排序方式 ("Latest" 或 "Top")
        """
        try:
            # 建構搜尋查詢
            search_term = f"{self.hashtag}"

            # 添加時間過濾條件
            if start_date:
                search_term += f" since:{start_date}"
                self.logger.info(f"  - 時間過濾: 從 {start_date} 開始")

            if end_date:
                search_term += f" until:{end_date}"
                self.logger.info(f"  - 時間過濾: 到 {end_date} 結束")

            run_input = {
                "searchTerms": [search_term],
                "maxItems": limit,
                "sort": sort,
                "onlyImage": False,
                "onlyQuote": False,
                "onlyTwitterBlue": False,
                "onlyVerifiedUsers": False,
                "onlyVideo": False
            }

            self.logger.info(f"正在搜尋 Hashtag 推文 (limit={limit}): {search_term}")
            self.logger.debug(f"搜尋參數: {run_input}")
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)

            if not items:
                self.logger.warning(f"未取得任何推文: {search_term}")
                return []

            # 重用父類的 _parse_post 方法解析推文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)

            self.logger.info(f"成功抓取 {len(posts)} 則 Hashtag 推文")
            return posts

        except Exception as e:
            self.logger.error(f"搜尋 Hashtag 推文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """下載推文中的媒體檔案（覆寫以使用 hashtag 目錄）"""
        try:
            # 建立 hashtag 目錄
            hashtag_dir = os.path.join(save_dir, f"hashtag_{self.hashtag}")
            os.makedirs(hashtag_dir, exist_ok=True)
            
            # 下載所有媒體
            success_count = 0
            for index, media in enumerate(post.media_items):
                # 決定副檔名
                if media.media_type == MediaType.VIDEO:
                    ext = 'mp4'
                elif media.media_type == MediaType.IMAGE:
                    # 從 URL 判斷圖片格式，預設為 jpg
                    url_lower = media.url.lower()
                    if '.png' in url_lower:
                        ext = 'png'
                    elif '.gif' in url_lower:
                        ext = 'gif'
                    elif '.webp' in url_lower:
                        ext = 'webp'
                    else:
                        ext = 'jpg'
                else:
                    ext = 'jpg'
                
                # 建立檔名
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(hashtag_dir, filename)
                
                # 下載
                if self.downloader.download(media.url, file_path):
                    media.local_path = file_path
                    success_count += 1
                    self.logger.debug(f"成功下載媒體: {filename}")
                else:
                    self.logger.warning(f"下載媒體失敗: {media.url}")
            
            if success_count > 0:
                self.logger.info(f"成功下載 {success_count}/{len(post.media_items)} 個媒體檔案")
            
            return success_count > 0
        
        except Exception as e:
            self.logger.error(f"下載媒體失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def collect_hashtag(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort: str = "Top"
    ) -> HashtagCollectionResult:
        """
        執行 Hashtag 收集

        參數:
            limit: 抓取推文數量限制,若為 None 則使用初始化時的 results_limit
            start_date: 開始日期 (YYYY-MM-DD)，用於時間過濾
            end_date: 結束日期 (YYYY-MM-DD)，用於時間過濾
            sort: 排序方式 ("Latest" 或 "Top")

        返回:
            HashtagCollectionResult 物件
        """
        started_at = datetime.datetime.now()

        # 若未指定 limit,使用初始化時的 results_limit
        if limit is None:
            limit = self.results_limit

        try:
            self.logger.info(f"[Twitter] 開始收集 Hashtag: #{self.hashtag}")

            # 抓取推文（支援時間過濾）
            posts = self.fetch_posts(
                limit=limit,
                start_date=start_date,
                end_date=end_date,
                sort=sort
            )
            
            # 轉換為 HashtagPost
            hashtag_posts = []
            for post in posts:
                hashtag_post = HashtagPost(
                    platform=post.platform,
                    post_id=post.post_id,
                    content_type=post.content_type,
                    author_id=post.author_id,
                    author_username=post.author_username,
                    author_display_name=post.author_display_name,
                    text=post.text,
                    title=post.title,
                    language=post.language,
                    media_items=post.media_items,
                    like_count=post.like_count,
                    comment_count=post.comment_count,
                    share_count=post.share_count,
                    view_count=post.view_count,
                    bookmark_count=post.bookmark_count,
                    is_pinned=post.is_pinned,
                    is_promoted=post.is_promoted,
                    comments_disabled=post.comments_disabled,
                    location_name=post.location_name,
                    location_id=post.location_id,
                    latitude=post.latitude,
                    longitude=post.longitude,
                    hashtags=post.hashtags,
                    mentions=post.mentions,
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                    expires_at=post.expires_at,
                    post_url=post.post_url,
                    raw_data=post.raw_data,
                    hashtag=self.hashtag
                )
                hashtag_posts.append(hashtag_post)
            
            finished_at = datetime.datetime.now()
            duration = int((finished_at - started_at).total_seconds())
            
            return HashtagCollectionResult(
                platform=PlatformType.TWITTER,
                hashtag=self.hashtag,
                success=True,
                posts=hashtag_posts,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration
            )
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(f"[錯誤] {error_msg}")
            
            finished_at = datetime.datetime.now()
            duration = int((finished_at - started_at).total_seconds())
            
            return HashtagCollectionResult(
                platform=PlatformType.TWITTER,
                hashtag=self.hashtag,
                success=False,
                error_message=error_msg,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration
            )


class TwitterAdvancedSearchCollector(TwitterHashtagCollector):
    """
    Twitter 進階搜尋收集器
    
    功能:
    - 支援完整的 Twitter Advanced Search 操作符
    - 彈性搜尋過濾條件
    
    搜尋操作符範例:
    - 關鍵字: "keyword1 keyword2"
    - 排除: "-keyword"
    - 完整匹配: '"exact phrase"'
    - 用戶: "from:username" 或 "to:username" 或 "@username"
    - Hashtag: "#hashtag"
    - 最小互動數: "min_faves:100" 或 "min_retweets:50"
    - 時間: "since:2024-01-01" 或 "until:2024-12-31"
    - 語言: "lang:en"
    - 驗證用戶: "filter:verified"
    - 包含媒體: "filter:images" 或 "filter:videos"
    - 安全搜尋: "filter:safe"
    
    組合範例:
    - "#AI lang:en min_faves:100 filter:images"
    - "from:elonmusk since:2024-01-01"
    - '"machine learning" -crypto filter:verified'
    """
    
    def __init__(self, search_query: str, api_token: str, results_limit: int = 50, **kwargs):
        """
        初始化 Twitter 進階搜尋收集器
        
        參數:
            search_query: Twitter 進階搜尋查詢字串
            api_token: Apify API Token
            results_limit: 結果數量限制
        """
        # 使用查詢字串作為識別
        super(TwitterHashtagCollector, self).__init__(
            username=search_query,
            api_token=api_token,
            platform=PlatformType.TWITTER
        )
        self.search_query = search_query
        self.results_limit = results_limit
        self.downloader = MediaDownloader()
        self.logger = get_logger('TwitterAdvancedSearchCollector')
    
    def fetch_posts(
        self, 
        limit: int = 50,
        sort: str = "Latest",
        language: Optional[str] = None,
        verified_only: bool = False,
        media_type: Optional[str] = None,
        min_likes: Optional[int] = None,
        min_retweets: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> List[SocialPost]:
        """
        使用進階搜尋抓取推文
        
        參數:
            limit: 抓取推文數量限制
            sort: 排序方式 ("Latest" 或 "Top")
            language: 語言過濾 (如 "en", "zh", "ja")，None 表示不限制語言
            verified_only: 是否只搜尋認證用戶
            media_type: 媒體類型過濾 ("images" 或 "videos")
            min_likes: 最小點讚數
            min_retweets: 最小轉推數
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        """
        try:
            # 建構搜尋查詢
            search_terms = [self.search_query]
            
            # 添加額外過濾條件
            filters = []
            
            if language:
                filters.append(f"lang:{language}")
            
            if verified_only:
                filters.append("filter:verified")
            
            if media_type:
                filters.append(f"filter:{media_type}")
            
            if min_likes:
                filters.append(f"min_faves:{min_likes}")
            
            if min_retweets:
                filters.append(f"min_retweets:{min_retweets}")
            
            if start_date:
                filters.append(f"since:{start_date}")
            
            if end_date:
                filters.append(f"until:{end_date}")
            
            # 組合查詢字串
            if filters:
                search_terms[0] = f"{self.search_query} {' '.join(filters)}"
            
            # 建立符合官方 API 格式的 run_input
            run_input = {
                "searchTerms": search_terms,
                "maxItems": limit,
                "sort": sort,
                "onlyImage": False,
                "onlyQuote": False,
                "onlyTwitterBlue": False,
                "onlyVerifiedUsers": verified_only,
                "onlyVideo": False
            }
            
            self.logger.info(f"正在執行進階搜尋: {search_terms[0]}")
            self.logger.info(f"  - 數量限制: {limit}")
            self.logger.info(f"  - 排序方式: {sort}")
            if language:
                self.logger.info(f"  - 語言限制: {language}")
            self.logger.debug(f"搜尋參數: {run_input}")
            
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)
            
            if not items:
                self.logger.warning(f"未取得任何搜尋結果")
                return []
            
            # 解析推文
            posts = []
            for item in items:
                post = self._parse_search_post(item)
                if post:
                    posts.append(post)
            
            self.logger.info(f"成功抓取 {len(posts)} 則搜尋結果")
            return posts
        
        except Exception as e:
            self.logger.error(f"進階搜尋失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_search_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析搜尋結果推文"""
        try:
            post_id = raw.get('tweetId', '')
            if not post_id:
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            is_retweet = raw.get('isRetweet', False)
            content_type = ContentType.RETWEET if is_retweet else ContentType.TWEET
            
            post = SocialPost(
                platform=PlatformType.TWITTER,
                post_id=post_id,
                content_type=content_type,
                author_id=raw.get('authorId', ''),
                author_username=raw.get('username', ''),
                author_display_name=raw.get('name'),
                text=raw.get('text', ''),
                language=raw.get('lang'),
                like_count=raw.get('likeCount', 0),
                comment_count=raw.get('replyCount', 0),
                share_count=raw.get('retweetCount', 0),
                view_count=raw.get('viewCount', 0),
                bookmark_count=raw.get('bookmarkCount', 0),
                created_at=self._parse_twitter_date(raw.get('createdAt')),
                post_url=raw.get('url'),
                raw_data=raw_data_json
            )
            
            post.media_items = self._parse_media(raw)
            post.hashtags = raw.get('hashtags', [])
            post.mentions = raw.get('mentions', [])
            
            return post
        
        except Exception as e:
            self.logger.error(f"解析搜尋結果失敗: {e}")
            return None

