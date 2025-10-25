"""
Threads 收集器
基於 Apify API 實作
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_collector import ApifyBasedCollector
from core.data_models import (
    PlatformType, PlatformUser, SocialPost, HashtagPost,
    MediaItem, MediaType, ContentType, HashtagCollectionResult
)
from lib.media_downloader import MediaDownloader
from typing import List, Optional, Dict, Any
import datetime
import json
from config.platform_config import APIFY_ACTORS


class ThreadsCollector(ApifyBasedCollector):
    """
    Threads 資料收集器
    
    功能:
    - 抓取使用者資料
    - 抓取串文 (threads)
    - 下載媒體檔案
    
    Apify Actors:
    - apify/threads-profile-api-scraper (使用者資料)
    - futurizerush/meta-threads-scraper (貼文資料)
    """
    
    # Apify Actor IDs
    THREADS_PROFILE_SCRAPER = APIFY_ACTORS['threads']['profile']
    THREADS_POST_SCRAPER = APIFY_ACTORS['threads']['post']
    
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
            # 使用新的 threads-profile-api-scraper
            run_input = {
                "usernames": [self.username]  # 只需要使用者名稱，不含 @
            }
            
            items = self.call_apify_actor(self.THREADS_PROFILE_SCRAPER, run_input)
            
            if not items or len(items) == 0:
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 從 text_app_biography 提取 bio 文字
            biography = raw.get('biography', '')
            text_app_bio = raw.get('text_app_biography', {})
            if text_app_bio:
                text_fragments = text_app_bio.get('text_fragments', {})
                fragments = text_fragments.get('fragments', [])
                if fragments:
                    # 組合所有 fragment 的文字
                    biography = ''.join([f.get('plaintext', '') for f in fragments])
            
            # 取得 profile_pic_url (優先使用高解析度版本)
            profile_pic_url = raw.get('profile_pic_url', '')
            hd_versions = raw.get('hd_profile_pic_versions', [])
            if hd_versions and len(hd_versions) > 0:
                # 使用最高解析度的圖片 (通常是列表中的最後一個)
                profile_pic_url = hd_versions[-1].get('url', profile_pic_url)
            
            user = PlatformUser(
                platform=PlatformType.THREADS,
                user_id=raw.get('pk', raw.get('id', '')),  # pk 或 id
                username=raw.get('username', self.username),
                display_name=raw.get('full_name', ''),
                is_verified=raw.get('is_verified', False),
                is_private=raw.get('is_private', False),
                description=biography,
                profile_image_url=profile_pic_url,
                follower_count=raw.get('follower_count', 0),
                post_count=0,  # profile API 不提供貼文數
                external_url=raw.get('url'),  # Threads profile URL
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
            # 使用 futurizerush/meta-threads-scraper 抓取貼文            # mode: "user" 代表抓取特定使用者的貼文
            # max_posts: 設定抓取的貼文數量 (20-100)
            max_posts = min(max(limit, 20), 100)  # 限制在 20-100 之間
            
            run_input = {
                "mode": "user",
                "username": self.username,  # 不含 @
                "max_posts": max_posts
            }
            
            items = self.call_apify_actor(self.THREADS_POST_SCRAPER, run_input)
            
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
            # 基本資訊 - 使用 post_code 作為 post_id
            post_id = raw.get('post_code', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 時間資訊 - 優先使用 created_at，備用 created_at_timestamp
            created_at = raw.get('created_at')
            if isinstance(created_at, str):
                try:
                    # 處理 ISO 8601 格式，如 "2025-04-10T15:51:29+00:00"
                    created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            
            # 如果 created_at 解析失敗，嘗試使用 created_at_timestamp
            if not created_at:
                timestamp = raw.get('created_at_timestamp')
                if isinstance(timestamp, (int, float)):
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            
            # 解析 hashtags 和 mentions
            hashtags = raw.get('hashtags', [])
            mentions = raw.get('mentions', [])
            
            # 建立串文物件
            post = SocialPost(
                platform=PlatformType.THREADS,
                post_id=post_id,
                content_type=ContentType.THREAD,
                author_id=raw.get('username', ''),  # 使用 username 作為 author_id
                author_username=raw.get('username', self.username),
                author_display_name=raw.get('display_name'),
                text=raw.get('text_content', ''),
                like_count=raw.get('like_count', 0),
                comment_count=raw.get('comment_count', 0),
                share_count=raw.get('share_count', 0),
                view_count=raw.get('repost_count', 0),  # 使用 repost_count 作為額外的互動數據
                created_at=created_at,
                post_url=raw.get('post_url'),
                hashtags=hashtags,
                mentions=mentions,
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            return post
        
        except Exception as e:
            print(f"[Threads] 解析串文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析媒體項目"""
        media_items = []
        
        # 檢查是否有媒體
        has_media = raw.get('has_media', False)
        if not has_media:
            return media_items
        
        # 解析 media_items 列表
        raw_media_items = raw.get('media_items', [])
        for media in raw_media_items:
            if not isinstance(media, dict):
                continue
            
            media_type_str = media.get('media_type', '')
            media_url = media.get('media_url', '')
            thumbnail_url = media.get('thumbnail_url')
            
            if not media_url:
                continue
            
            # 判斷媒體類型
            if media_type_str == 'image':
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=media_url,
                    thumbnail_url=thumbnail_url
                ))
            elif media_type_str == 'video':
                media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=media_url,
                    thumbnail_url=thumbnail_url
                ))

        return media_items


class ThreadsHashtagCollector(ThreadsCollector):
    """
    Threads Hashtag 收集器

    專門用於收集特定 hashtag 的貼文，適合追蹤主題或話題。
    與 ThreadsCollector 不同：
    - ThreadsCollector: 追蹤特定使用者的貼文
    - ThreadsHashtagCollector: 追蹤特定主題標籤的貼文
    """

    # Apify Actor ID for hashtag scraping
    HASHTAG_SCRAPER = APIFY_ACTORS['threads']['hashtag']

    def __init__(self, hashtag, api_token: str, results_type: str = "posts", results_limit: int = 50, sort_by_recent: bool = True, **kwargs):
        """
        初始化 Threads Hashtag 收集器

        參數:
            hashtag: Threads hashtag 或 hashtag 列表（可含或不含 # 符號）
                    - 單個 hashtag: str，例如 "AI"
                    - 多個 hashtag: List[str]，例如 ["AI", "Python", "Meta"]
            api_token: Apify API Token
            results_type: 結果類型 (為了與其他平台相容，Threads 會忽略此參數)
            results_limit: 每個 keyword 的最大貼文數量 (1-2000, 預設: 50)
            sort_by_recent: 是否依照最新排序 (True) 或依照相關性排序 (False, 預設: True)
            **kwargs: 其他參數（為了與工廠模式相容）
        """
        # 處理 hashtag 參數，統一轉為列表
        if isinstance(hashtag, str):
            # 檢查是否為逗號分隔的字串
            if ',' in hashtag:
                self.hashtags = [h.strip().lstrip('#') for h in hashtag.split(',') if h.strip()]
            else:
                self.hashtags = [hashtag.lstrip('#')]
        elif isinstance(hashtag, list):
            self.hashtags = [h.lstrip('#') if isinstance(h, str) else str(h).lstrip('#') for h in hashtag]
        else:
            self.hashtags = [str(hashtag).lstrip('#')]

        # 使用第一個 hashtag 作為 username（為了相容基類）
        super().__init__(username=self.hashtags[0], api_token=api_token)

        # 保留舊的 self.hashtag 屬性以向下相容（單數形式）
        self.hashtag = self.hashtags[0] if self.hashtags else ''
        self.results_limit = results_limit
        self.sort_by_recent = sort_by_recent

    # =========================================================================
    # Hashtag 收集核心功能
    # =========================================================================

    def collect_hashtag(
        self,
        hashtag=None,
        results_limit: Optional[int] = None,
        sort_by_recent: Optional[bool] = None
    ) -> HashtagCollectionResult:
        """
        收集指定 hashtag 的貼文

        參數:
            hashtag: Threads hashtag 或 hashtag 列表（可含或不含 # 符號），預設使用初始化時的 hashtag
                    - 單個 hashtag: str
                    - 多個 hashtag: List[str] 或逗號分隔字串
            results_limit: 每個 keyword 的最大貼文數量，預設使用初始化時的設定
            sort_by_recent: 是否依照最新排序，預設使用初始化時的設定

        返回:
            HashtagCollectionResult 物件
        """
        # 處理 hashtag 參數
        if hashtag is None:
            clean_hashtags = self.hashtags
        elif isinstance(hashtag, str):
            if ',' in hashtag:
                clean_hashtags = [h.strip().lstrip('#') for h in hashtag.split(',') if h.strip()]
            else:
                clean_hashtags = [hashtag.lstrip('#')]
        elif isinstance(hashtag, list):
            clean_hashtags = [h.lstrip('#') if isinstance(h, str) else str(h).lstrip('#') for h in hashtag]
        else:
            clean_hashtags = [str(hashtag).lstrip('#')]

        max_items = results_limit or self.results_limit
        sort_recent = sort_by_recent if sort_by_recent is not None else self.sort_by_recent

        started_at = datetime.datetime.now()

        try:
            print(f"\n{'='*60}")
            if len(clean_hashtags) == 1:
                print(f"開始收集 Threads Hashtag: #{clean_hashtags[0]}")
            else:
                print(f"開始收集 Threads Hashtags: {', '.join(['#' + h for h in clean_hashtags])}")
            print(f"{'='*60}")

            # 抓取貼文
            print(f"\n[步驟 1/1] 抓取 hashtag 貼文...")
            posts = self._fetch_hashtag_posts(clean_hashtags, max_items, sort_recent)

            # 計算執行時長
            finished_at = datetime.datetime.now()
            duration_seconds = int((finished_at - started_at).total_seconds())

            # 返回結果（hashtag 欄位使用第一個或逗號連接的形式）
            hashtag_display = ','.join(clean_hashtags)
            result = HashtagCollectionResult(
                platform=self.platform,
                hashtag=hashtag_display,
                success=True,
                posts=posts,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration_seconds
            )

            print(f"\n{'='*60}")
            print(f"✓ Hashtag 收集完成！")
            if len(clean_hashtags) == 1:
                print(f"  - Hashtag: #{clean_hashtags[0]}")
            else:
                print(f"  - Hashtags: {', '.join(['#' + h for h in clean_hashtags])}")
            print(f"  - 貼文數: {len(posts)}")
            print(f"  - 執行時長: {duration_seconds} 秒")
            print(f"{'='*60}\n")

            return result

        except Exception as e:
            finished_at = datetime.datetime.now()
            duration_seconds = int((finished_at - started_at).total_seconds())

            error_msg = str(e)
            print(f"\n✗ Hashtag 收集失敗: {error_msg}")

            hashtag_display = ','.join(clean_hashtags) if clean_hashtags else ''
            return HashtagCollectionResult(
                platform=self.platform,
                hashtag=hashtag_display,
                success=False,
                error_message=error_msg,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration_seconds
            )

    def _fetch_hashtag_posts(
        self,
        hashtags,
        results_limit: int = 50,
        sort_by_recent: bool = True
    ) -> List[HashtagPost]:
        """
        抓取 hashtag 貼文（內部方法）

        參數:
            hashtags: 單個 hashtag (str) 或 hashtag 列表 (List[str])
            results_limit: 每個 keyword 的最大貼文數量
            sort_by_recent: 是否依照最新排序
        """
        try:
            # 統一處理為列表
            if isinstance(hashtags, str):
                hashtag_list = [hashtags]
            elif isinstance(hashtags, list):
                hashtag_list = hashtags
            else:
                hashtag_list = [str(hashtags)]

            # 建立 keywords 列表（加上 # 符號）
            keywords = [f"#{tag}" for tag in hashtag_list]

            run_input = {
                "keywords": keywords,
                "maxItemsPerKeyword": results_limit,
                "sortByRecent": sort_by_recent,
                "outputFormat": "json"
            }

            items = self.call_apify_actor(self.HASHTAG_SCRAPER, run_input)

            if not items:
                print(f"  [Threads Hashtag] ℹ 未取得貼文資料（可能原因：無相關貼文、網路錯誤）")
                return []

            # 解析貼文
            posts = []
            for item in items:
                # 嘗試從 item 中取得該貼文對應的 hashtag
                # 從 hashtags 欄位中提取，或使用第一個搜尋的 hashtag
                item_hashtags = item.get('hashtags', [])
                if item_hashtags and len(item_hashtags) > 0:
                    item_hashtag = item_hashtags[0]
                else:
                    item_hashtag = hashtag_list[0]

                post = self._parse_hashtag_post(item, item_hashtag)
                if post:
                    posts.append(post)

            if len(posts) == 0 and len(items) > 0:
                print(f"  [Threads Hashtag] ⚠ 取得了 {len(items)} 筆原始資料，但解析後無有效貼文")

            return posts

        except Exception as e:
            print(f"[Threads Hashtag] ✗ 抓取 hashtag 貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_hashtag_post(self, raw: Dict[str, Any], hashtag: str) -> Optional[HashtagPost]:
        """解析 hashtag 貼文資料"""
        try:
            # 基本資訊
            post_id = raw.get('id', '')
            if not post_id:
                return None

            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)

            # 作者資訊
            author_username = raw.get('author', '')
            author_id = raw.get('author_id', '')
            author_display_name = raw.get('author_name', '')

            # 判斷內容類型（Threads 主要是串文）
            content_type = ContentType.THREAD

            # 時間資訊
            created_at_timestamp = raw.get('created_at')
            if created_at_timestamp:
                if isinstance(created_at_timestamp, (int, float)):
                    created_at = datetime.datetime.fromtimestamp(created_at_timestamp)
                else:
                    created_at = None
            else:
                created_at = None

            # 建立 hashtag 貼文物件
            post = HashtagPost(
                platform=PlatformType.THREADS,
                post_id=post_id,
                content_type=content_type,
                author_id=author_id,
                author_username=author_username,
                author_display_name=author_display_name,
                text=raw.get('text', ''),
                like_count=raw.get('like_count', 0),
                comment_count=raw.get('reply_count', 0),
                share_count=raw.get('repost_count', 0),
                view_count=raw.get('view_count', 0),
                created_at=created_at,
                post_url=raw.get('url', ''),
                raw_data=raw_data_json,
                hashtag=hashtag
            )

            # 解析媒體
            post.media_items = self._parse_hashtag_media(raw)

            # 解析標籤和提及
            post.hashtags = raw.get('hashtags', [])
            post.mentions = raw.get('mentions', [])

            return post

        except Exception as e:
            print(f"[Threads Hashtag] 解析貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_hashtag_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析 hashtag 貼文的媒體項目"""
        media_items = []

        # 從 media 陣列中解析媒體
        raw_media_items = raw.get('media', [])
        if not raw_media_items:
            return media_items

        for media in raw_media_items:
            if not isinstance(media, dict):
                continue

            media_type_str = media.get('type', '')
            media_url = media.get('url', '')
            video_url = media.get('video_url')

            if not media_url and not video_url:
                continue

            # 判斷媒體類型
            if media_type_str == 'image' or (media_url and not video_url):
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=media_url,
                    width=media.get('width'),
                    height=media.get('height')
                ))
            elif media_type_str == 'video' or video_url:
                # 影片使用 video_url，縮圖使用 url
                media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=video_url,
                    thumbnail_url=media_url,
                    width=media.get('width'),
                    height=media.get('height'),
                    has_audio=media.get('has_audio')
                ))

        return media_items

    # =========================================================================
    # 實作基類的抽象方法（這些方法在 hashtag 收集中不使用）
    # =========================================================================

    def fetch_user_profile(self):
        """不使用於 hashtag 收集"""
        return None

    def fetch_posts(self, limit: int = 50):
        """不使用於 hashtag 收集"""
        return []

    def fetch_stories(self, limit: Optional[int] = None):
        """不使用於 hashtag 收集"""
        return []

    def download_media(self, post, save_dir: str) -> bool:
        """
        下載 hashtag 貼文中的媒體檔案

        參數:
            post: HashtagPost 物件
            save_dir: 基礎儲存目錄

        返回:
            是否成功下載
        """
        try:
            # 建立 hashtag 目錄（使用第一個關鍵詞）
            hashtag_dir = os.path.join(save_dir, f"hashtag_{self.hashtags[0]}")
            os.makedirs(hashtag_dir, exist_ok=True)

            # 下載所有媒體
            success_count = 0
            for index, media in enumerate(post.media_items):
                # 決定副檔名
                if media.media_type == MediaType.VIDEO:
                    ext = 'mp4'
                else:
                    ext = 'jpg'

                # 建立檔名（使用 post_id 和 index）
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(hashtag_dir, filename)

                # 下載
                if self.downloader.download(media.url, file_path):
                    media.local_path = file_path
                    success_count += 1

            return success_count > 0

        except Exception as e:
            print(f"[Threads Hashtag] 下載媒體失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

