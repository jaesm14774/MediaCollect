"""
Instagram 收集器
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


class InstagramCollector(ApifyBasedCollector):
    """
    Instagram 資料收集器
    
    功能:
    - 抓取使用者資料
    - 抓取貼文（含輪播）
    - 抓取限時動態
    - 下載媒體檔案
    """
    
    # Apify Actor IDs
    PROFILE_SCRAPER = "apify/instagram-profile-scraper"
    POST_SCRAPER = "apify/instagram-post-scraper"
    STORY_SCRAPER = "igview-owner/instagram-story-viewer"
    
    def __init__(self, username: str, api_token: str):
        """
        初始化 Instagram 收集器
        
        參數:
            username: Instagram 使用者名稱
            api_token: Apify API Token
        """
        super().__init__(
            username=username, 
            api_token=api_token, 
            platform=PlatformType.INSTAGRAM
        )
        self.downloader = MediaDownloader()
    
    # =========================================================================
    # 實作抽象方法
    # =========================================================================
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """抓取使用者基本資料"""
        try:
            run_input = {
                "usernames": [f"https://www.instagram.com/{self.username}/"],
                "resultsLimit": 1
            }
            
            items = self.call_apify_actor(self.PROFILE_SCRAPER, run_input)
            
            if not items:
                print(f"  [Instagram] ℹ 未取得使用者資料（可能原因：帳號不存在、帳號私密、網路錯誤）")
                return None
            
            # 解析 Apify 資料為通用格式
            raw = items[0]
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 處理 category 欄位（避免字串 "None" 的問題）
            category_value = raw.get('businessCategoryName')
            if category_value == "None" or category_value == "null":
                category_value = None
            
            user = PlatformUser(
                platform=PlatformType.INSTAGRAM,
                user_id=raw.get('id', ''),
                username=raw.get('username', self.username),
                display_name=raw.get('fullName', ''),
                is_verified=raw.get('verified', False),
                is_private=raw.get('private', False),
                is_business=raw.get('isBusinessAccount', False),
                description=raw.get('biography', ''),
                profile_image_url=raw.get('profilePicUrlHD') or raw.get('profilePicUrl'),
                category=category_value,
                follower_count=raw.get('followersCount', 0),
                following_count=raw.get('followsCount', 0),
                post_count=raw.get('postsCount', 0),
                external_url=raw.get('externalUrl'),
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            return user
        
        except Exception as e:
            print(f"[Instagram] ✗ 抓取使用者資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """抓取使用者貼文"""
        try:
            run_input = {
                "username": [self.username],
                "resultsLimit": limit,
                "addParentData": True,
                "skipPinnedPosts": True,
                "onlyPostsNewerThan": "7 day"
            }
            
            items = self.call_apify_actor(self.POST_SCRAPER, run_input)
            
            if not items:
                print(f"  [Instagram] ℹ 未取得貼文資料（可能原因：無新貼文、帳號私密、網路錯誤）")
                return []
            
            # 解析貼文
            posts = []
            for item in items:
                post = self._parse_post(item)
                if post:
                    posts.append(post)
            
            if len(posts) == 0 and len(items) > 0:
                print(f"  [Instagram] ⚠ 取得了 {len(items)} 筆原始資料，但解析後無有效貼文")
            
            return posts
        
        except Exception as e:
            print(f"[Instagram] ✗ 抓取貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """抓取限時動態"""
        try:
            run_input = {
                "username": self.username
            }
            
            result_items = self.call_apify_actor(self.STORY_SCRAPER, run_input)
            
            if not result_items:
                print(f"  [Instagram] ℹ 未取得限時動態資料（可能原因：無限時動態、帳號私密、網路錯誤）")
                return []
            
            # 解析限時動態（新格式: [{"requested": "username", "stories": [...]}]）
            stories = []
            for item in result_items:
                if 'stories' in item and isinstance(item['stories'], list):
                    for story_raw in item['stories']:
                        story = self._parse_story(story_raw)
                        if story:
                            stories.append(story)
            
            if len(stories) == 0 and len(result_items) > 0:
                print(f"  [Instagram] ℹ 取得了原始資料但無有效限時動態（可能該使用者目前沒有限時動態）")
            
            # 套用數量限制
            if limit is not None and len(stories) > limit:
                stories = stories[:limit]
            
            return stories
        
        except Exception as e:
            print(f"[Instagram] ✗ 抓取限時動態失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """下載貼文中的媒體檔案"""
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
            print(f"[Instagram] 下載媒體失敗: {e}")
            return False
    
    # =========================================================================
    # 私有方法 - 資料解析
    # =========================================================================
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析貼文資料"""
        try:
            # 基本資訊
            post_id = raw.get('shortCode') or raw.get('code', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 作者資訊
            owner = raw.get('ownerUsername') or raw.get('owner', {})
            if isinstance(owner, dict):
                author_username = owner.get('username', self.username)
                author_id = owner.get('id', '')
            else:
                author_username = owner or self.username
                author_id = ''
            
            # 判斷內容類型
            product_type = raw.get('productType', '').lower()
            if 'reel' in product_type or 'clips' in product_type:
                content_type = ContentType.REEL
            else:
                content_type = ContentType.POST
            
            # 時間資訊
            timestamp = raw.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    created_at = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            else:
                created_at = None
            
            # 建立貼文物件
            post = SocialPost(
                platform=PlatformType.INSTAGRAM,
                post_id=post_id,
                content_type=content_type,
                author_id=author_id,
                author_username=author_username,
                text=raw.get('caption') or raw.get('captionsText'),
                title=raw.get('title'),
                like_count=raw.get('likesCount', 0),
                comment_count=raw.get('commentsCount', 0),
                view_count=raw.get('videoViewCount') or raw.get('videoPlayCount') or raw.get('playCount', 0),
                comments_disabled=raw.get('commentsDisabled', False),
                location_name=self._get_location_name(raw),
                created_at=created_at,
                post_url=f"https://www.instagram.com/p/{post_id}/",
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            post.media_items = self._parse_media(raw)
            
            # 解析標籤
            post.hashtags = self._extract_hashtags(post.text)
            
            return post
        
        except Exception as e:
            print(f"[Instagram] 解析貼文失敗: {e}")
            return None
    
    def _parse_story(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析限時動態資料"""
        try:
            # Story ID
            story_id = raw.get('pk')
            if not story_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 作者資訊
            user = raw.get('user', {})
            author_id = user.get('id', '')
            author_username = user.get('username', self.username)
            
            # 時間資訊
            taken_at = raw.get('taken_at')
            if taken_at:
                created_at = datetime.datetime.fromtimestamp(taken_at)
                expires_at = created_at + datetime.timedelta(days=1)
            else:
                created_at = None
                expires_at = None
            
            # 建立限時動態物件
            story = SocialPost(
                platform=PlatformType.INSTAGRAM,
                post_id=str(story_id),
                content_type=ContentType.STORY,
                author_id=str(author_id),
                author_username=author_username,
                created_at=created_at,
                expires_at=expires_at,
                raw_data=raw_data_json  # 儲存完整原始資料
            )
            
            # 解析媒體
            video_versions = raw.get('video_versions', [])
            if video_versions:
                # 影片
                video_url = video_versions[0].get('url')
                if video_url:
                    story.media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=video_url,
                        width=video_versions[0].get('width'),
                        height=video_versions[0].get('height')
                    ))
            # 圖片
            image_versions2 = raw.get('image_versions2', {})
            candidates = image_versions2.get('candidates', [])
            if candidates:
                image_url = candidates[0].get('url')
                if image_url:
                    story.media_items.append(MediaItem(
                        media_type=MediaType.IMAGE,
                        url=image_url,
                        width=candidates[0].get('width'),
                        height=candidates[0].get('height')
                    ))
            
            return story
        
        except Exception as e:
            print(f"[Instagram] 解析限時動態失敗: {e}")
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析媒體項目"""
        media_items = []
        
        # 判斷媒體類型
        media_type = raw.get('type')
        
        if media_type == 'Sidecar':
            # 輪播貼文 - 解析所有子媒體
            children = raw.get('childPosts') or raw.get('sidecarChildren', [])
            for child in children:
                if child.get('type') == 'Video' or child.get('videoUrl'):
                    # 影片
                    video_url = child.get('videoUrl')
                    if video_url:
                        media_items.append(MediaItem(
                            media_type=MediaType.VIDEO,
                            url=video_url,
                            thumbnail_url=child.get('displayUrl') or child.get('imageUrl'),
                            duration=child.get('videoDuration')
                        ))
                else:
                    # 圖片
                    image_url = child.get('displayUrl') or child.get('imageUrl')
                    if image_url:
                        media_items.append(MediaItem(
                            media_type=MediaType.IMAGE,
                            url=image_url
                        ))
        else:
            # 單張圖片或單個影片
            if media_type == 'Video' or raw.get('videoUrl'):
                # 影片
                video_url = raw.get('videoUrl')
                if video_url:
                    media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=video_url,
                        thumbnail_url=raw.get('displayUrl') or raw.get('imageUrl'),
                        duration=raw.get('videoDuration')
                    ))
            
            # 圖片（影片貼文也會有預覽圖）
            image_url = raw.get('displayUrl') or raw.get('imageUrl')
            if image_url and not raw.get('videoUrl'):
                media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=image_url
                ))
        
        return media_items
    
    def _get_location_name(self, raw: Dict[str, Any]) -> Optional[str]:
        """取得地點名稱"""
        location_obj = raw.get('locationName') or raw.get('location')
        if isinstance(location_obj, dict):
            return location_obj.get('name')
        return location_obj
    
    def _extract_hashtags(self, text: Optional[str]) -> List[str]:
        """從文字中提取標籤"""
        if not text:
            return []
        
        import re
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags


class InstagramHashtagCollector(InstagramCollector):
    """
    Instagram Hashtag 收集器
    
    專門用於收集特定 hashtag 的貼文，適合追蹤主題或話題。
    與 InstagramCollector 不同：
    - InstagramCollector: 追蹤特定使用者的貼文
    - InstagramHashtagCollector: 追蹤特定主題標籤的貼文
    """
    
    # Apify Actor ID for hashtag scraping
    HASHTAG_SCRAPER = "apify/instagram-hashtag-scraper"
    
    def __init__(self, hashtag, api_token: str, results_type: str = "posts", results_limit: int = 50):
        """
        初始化 Instagram Hashtag 收集器
        
        參數:
            hashtag: Instagram hashtag 或 hashtag 列表（可含或不含 # 符號）
                    - 單個 hashtag: str，例如 "timelessbruno"
                    - 多個 hashtag: List[str]，例如 ["timelessbruno", "travel", "food"]
            api_token: Apify API Token
            results_type: 結果類型 ("posts" 或 "reels")
            results_limit: 每個 hashtag 的結果數量限制
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
        self.results_type = results_type
        self.results_limit = results_limit
    
    # =========================================================================
    # Hashtag 收集核心功能
    # =========================================================================
    
    def collect_hashtag(
        self,
        hashtag=None,
        results_type: Optional[str] = None,
        results_limit: Optional[int] = None
    ) -> HashtagCollectionResult:
        """
        收集指定 hashtag 的貼文
        
        參數:
            hashtag: Instagram hashtag 或 hashtag 列表（可含或不含 # 符號），預設使用初始化時的 hashtag
                    - 單個 hashtag: str
                    - 多個 hashtag: List[str] 或逗號分隔字串
            results_type: 結果類型 ("posts" 或 "reels")，預設使用初始化時的設定
            results_limit: 每個 hashtag 的結果數量限制，預設使用初始化時的設定
        
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
        
        r_type = results_type or self.results_type
        r_limit = results_limit or self.results_limit
        
        started_at = datetime.datetime.now()
        
        try:
            print(f"\n{'='*60}")
            if len(clean_hashtags) == 1:
                print(f"開始收集 Instagram Hashtag: #{clean_hashtags[0]}")
            else:
                print(f"開始收集 Instagram Hashtags: {', '.join(['#' + h for h in clean_hashtags])}")
            print(f"{'='*60}")
            
            # 抓取貼文
            print(f"\n[步驟 1/1] 抓取 hashtag 貼文...")
            posts = self._fetch_hashtag_posts(clean_hashtags, r_type, r_limit)
            
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
        results_type: str = "posts",
        results_limit: int = 50
    ) -> List[HashtagPost]:
        """
        抓取 hashtag 貼文（內部方法）
        
        參數:
            hashtags: 單個 hashtag (str) 或 hashtag 列表 (List[str])
            results_type: 結果類型 ("posts" 或 "reels")
            results_limit: 結果數量限制
        """
        try:
            # 統一處理為列表
            if isinstance(hashtags, str):
                hashtag_list = [hashtags]
            elif isinstance(hashtags, list):
                hashtag_list = hashtags
            else:
                hashtag_list = [str(hashtags)]
            
            run_input = {
                "hashtags": hashtag_list,
                "resultsType": results_type,
                "resultsLimit": results_limit
            }
            
            items = self.call_apify_actor(self.HASHTAG_SCRAPER, run_input)
            
            if not items:
                print(f"  [Instagram Hashtag] ℹ 未取得貼文資料（可能原因：無相關貼文、網路錯誤）")
                return []
            
            # 解析貼文
            posts = []
            for item in items:
                # 嘗試從 item 中取得該貼文對應的 hashtag
                # Apify 可能會在 item 中包含 hashtag 資訊
                item_hashtag = item.get('hashtag') or item.get('queryHashtag') or hashtag_list[0]
                post = self._parse_hashtag_post(item, item_hashtag)
                if post:
                    posts.append(post)
            
            if len(posts) == 0 and len(items) > 0:
                print(f"  [Instagram Hashtag] ⚠ 取得了 {len(items)} 筆原始資料，但解析後無有效貼文")
            
            return posts
        
        except Exception as e:
            print(f"[Instagram Hashtag] ✗ 抓取 hashtag 貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_hashtag_post(self, raw: Dict[str, Any], hashtag: str) -> Optional[HashtagPost]:
        """解析 hashtag 貼文資料"""
        try:
            # 基本資訊
            post_id = raw.get('shortCode') or raw.get('id', '')
            if not post_id:
                return None
            
            # 將原始資料轉為 JSON 字串
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            # 作者資訊（hashtag 收集的資料結構稍有不同）
            author_username = raw.get('ownerUsername', '')
            author_id = raw.get('ownerId', '')
            author_display_name = raw.get('ownerFullName', '')
            
            # 判斷內容類型
            product_type = raw.get('productType', '').lower()
            post_type = raw.get('type', '').lower()
            
            if 'reel' in product_type or 'clips' in product_type or 'video' in post_type:
                content_type = ContentType.REEL
            else:
                content_type = ContentType.POST
            
            # 時間資訊
            timestamp = raw.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    # 處理 ISO 8601 格式
                    timestamp = timestamp.replace('Z', '+00:00')
                    created_at = datetime.datetime.fromisoformat(timestamp)
                else:
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            else:
                created_at = None
            
            # 建立 hashtag 貼文物件
            post = HashtagPost(
                platform=PlatformType.INSTAGRAM,
                post_id=post_id,
                content_type=content_type,
                author_id=author_id,
                author_username=author_username,
                author_display_name=author_display_name,
                text=raw.get('caption', ''),
                like_count=raw.get('likesCount', 0),
                comment_count=raw.get('commentsCount', 0),
                view_count=raw.get('videoPlayCount') or raw.get('igPlayCount') or raw.get('playCount', 0),
                share_count=raw.get('reshareCount', 0),
                comments_disabled=raw.get('commentsDisabled', False),
                is_promoted=raw.get('isSponsored', False),
                location_name=raw.get('locationName'),
                created_at=created_at,
                post_url=raw.get('url', f"https://www.instagram.com/p/{post_id}/"),
                raw_data=raw_data_json,
                hashtag=hashtag
            )
            
            # 解析媒體（重用父類別的 _parse_media 方法）
            post.media_items = self._parse_media(raw)
            
            # 解析標籤（從 raw 的 hashtags 或從 caption 提取）
            if 'hashtags' in raw and isinstance(raw['hashtags'], list):
                post.hashtags = raw['hashtags']
            else:
                post.hashtags = self._extract_hashtags(post.text)
            
            # 解析提及
            if 'mentions' in raw and isinstance(raw['mentions'], list):
                post.mentions = raw['mentions']
            
            return post
        
        except Exception as e:
            print(f"[Instagram Hashtag] 解析貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
            print(f"[Instagram Hashtag] 下載媒體失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

