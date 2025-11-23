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
from config.platform_config import APIFY_ACTORS


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
    PROFILE_SCRAPER = APIFY_ACTORS['instagram']['profile']
    POST_SCRAPER = APIFY_ACTORS['instagram']['post']
    REEL_SCRAPER = APIFY_ACTORS['instagram']['reel']
    STORY_SCRAPER = APIFY_ACTORS['instagram']['story']
    
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
            
            raw = items[0]
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
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
                raw_data=raw_data_json
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
    
    def fetch_reels(self, limit: int = 3) -> List[SocialPost]:
        """抓取使用者 Reels"""
        try:
            run_input = {
                "username": [self.username],
                "resultsLimit": limit,
                "skipPinnedPosts": True,
                "includeSharesCount": True
            }
            
            items = self.call_apify_actor(self.REEL_SCRAPER, run_input)
            
            if not items:
                print(f"  [Instagram] ℹ 未取得 Reel 資料（可能原因：無 Reel、帳號私密、網路錯誤）")
                return []
            
            reels = []
            for item in items:
                reel = self._parse_reel(item)
                if reel:
                    reels.append(reel)
            
            if len(reels) == 0 and len(items) > 0:
                print(f"  [Instagram] ⚠ 取得了 {len(items)} 筆原始資料，但解析後無有效 Reel")
            
            return reels
        
        except Exception as e:
            print(f"[Instagram] ✗ 抓取 Reel 失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """抓取限時動態"""
        try:
            run_input = {
                "usernames": [self.username]
            }

            result_items = self.call_apify_actor(self.STORY_SCRAPER, run_input)

            if not result_items:
                print(f"  [Instagram] ℹ 未取得限時動態資料（可能原因：無限時動態、帳號私密、網路錯誤）")
                return []

            stories = []
            for item in result_items:
                # 過濾掉狀態訊息 (新格式會返回 type: "status" 的項目)
                if isinstance(item, dict) and item.get('type') == 'status':
                    continue

                # 新格式：直接是扁平的 story 物件
                # 舊格式：stories 巢狀在 item['stories'] 下
                if 'stories' in item and isinstance(item['stories'], list):
                    # 舊格式處理
                    for story_raw in item['stories']:
                        story = self._parse_story(story_raw)
                        if story:
                            stories.append(story)
                else:
                    # 新格式處理
                    story = self._parse_story(item)
                    if story:
                        stories.append(story)

            if len(stories) == 0 and len(result_items) > 0:
                print(f"  [Instagram] ℹ 取得了原始資料但無有效限時動態（可能該使用者目前沒有限時動態）")

            if limit is not None and len(stories) > limit:
                stories = stories[:limit]

            return stories

        except Exception as e:
            print(f"[Instagram] ✗ 抓取限時動態失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def collect_all(
        self, 
        post_limit: int = 50, 
        story_limit: Optional[int] = None,
        include_stories: bool = True,
        reel_limit: Optional[int] = None,
        include_reels: bool = True,
        photo_limit: Optional[int] = None,
        include_photos: bool = False,
        posts_newer_than: Optional[str] = None,
        posts_older_than: Optional[str] = None,
        caption_text: bool = False
    ):
        """
        執行完整的資料收集流程（包含 Reels）
        
        參數:
            post_limit: 要抓取的貼文數量
            story_limit: 要抓取的限時動態數量
            include_stories: 是否抓取限時動態
            reel_limit: 要抓取的 Reel 數量
            include_reels: 是否抓取 Reels
            photo_limit: 要抓取的照片數量
            include_photos: 是否抓取照片
            posts_newer_than: 只抓取此日期之後的貼文
            posts_older_than: 只抓取此日期之前的貼文
            caption_text: 是否提取影片字幕
        
        返回:
            CollectionResult 物件
        """
        from datetime import datetime
        from core.data_models import CollectionResult
        
        started_at = datetime.now()
        
        try:
            print(f"[{self.platform.value}] 開始抓取使用者 {self.username} 的資料...")
            user = self.fetch_user_profile()
            
            if not user:
                finished_at = datetime.now()
                duration = int((finished_at - started_at).total_seconds())
                return CollectionResult(
                    platform=self.platform,
                    success=False,
                    error_message=f"無法取得使用者 {self.username} 的資料",
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=duration
                )
            
            self.user_info = user
            print(f"  ✓ 使用者資料: {user.display_name or user.username}")
            
            print(f"[{self.platform.value}] 開始抓取貼文（限制: {post_limit} 筆）...")
            posts = self.fetch_posts(limit=post_limit)
            print(f"  ✓ 成功抓取 {len(posts)} 筆貼文")
            
            # 收集 Reels
            reels = []
            if include_reels:
                if reel_limit is None:
                    from config.platform_config import get_platform_setting
                    reel_limit = get_platform_setting('instagram', 'reel_limit', 3)
                
                print(f"[{self.platform.value}] 開始抓取 Reels（限制: {reel_limit} 筆）...")
                reels = self.fetch_reels(limit=reel_limit)
                print(f"  ✓ 成功抓取 {len(reels)} 筆 Reels")
                # 將 Reels 加入到 posts 列表中（因為它們都是 SocialPost）
                posts.extend(reels)
            
            stories = []
            if include_stories:
                print(f"[{self.platform.value}] 開始抓取限時動態...")
                stories = self.fetch_stories(limit=story_limit)
                print(f"  ✓ 成功抓取 {len(stories)} 筆限時動態")
            
            photos = []
            if include_photos and hasattr(self, 'fetch_photos'):
                print(f"[{self.platform.value}] 開始抓取照片...")
                photos = self.fetch_photos(limit=photo_limit or 10)
                print(f"  ✓ 成功抓取 {len(photos)} 張照片")
                posts.extend(photos)
            
            finished_at = datetime.now()
            duration = int((finished_at - started_at).total_seconds())
            
            return CollectionResult(
                platform=self.platform,
                success=True,
                user=user,
                posts=posts,
                stories=stories,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration
            )
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            print(f"[錯誤] {error_msg}")
            
            finished_at = datetime.now()
            duration = int((finished_at - started_at).total_seconds())
            
            return CollectionResult(
                platform=self.platform,
                success=False,
                error_message=error_msg,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration
            )
    
    async def collect_all_async(
        self, 
        post_limit: int = 50, 
        story_limit: Optional[int] = None,
        include_stories: bool = True,
        reel_limit: Optional[int] = None,
        include_reels: bool = True,
        photo_limit: Optional[int] = None,
        include_photos: bool = False,
        posts_newer_than: Optional[str] = None,
        posts_older_than: Optional[str] = None,
        caption_text: bool = False
    ):
        """
        執行完整的資料收集流程（異步版本，包含 Reels）
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.collect_all(
                post_limit, story_limit, include_stories, reel_limit, include_reels,
                photo_limit, include_photos, posts_newer_than, posts_older_than, caption_text
            )
        )
    
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
            print(f"[Instagram] 下載媒體失敗: {e}")
            return False
    
    def _parse_post(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析貼文資料"""
        try:
            post_id = raw.get('shortCode') or raw.get('code', '')
            if not post_id:
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            owner = raw.get('ownerUsername') or raw.get('owner', {})
            if isinstance(owner, dict):
                author_username = owner.get('username', self.username)
                author_id = owner.get('id', '')
            else:
                author_username = owner or self.username
                author_id = ''
            
            product_type = raw.get('productType', '').lower()
            if 'reel' in product_type or 'clips' in product_type:
                content_type = ContentType.REEL
            else:
                content_type = ContentType.POST
            
            timestamp = raw.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    created_at = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            else:
                created_at = None
            
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
                raw_data=raw_data_json
            )
            
            post.media_items = self._parse_media(raw)
            post.hashtags = self._extract_hashtags(post.text)
            
            return post
        
        except Exception as e:
            print(f"[Instagram] 解析貼文失敗: {e}")
            return None
    
    def _parse_reel(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析 Reel 資料"""
        try:
            post_id = raw.get('shortCode') or raw.get('id', '')
            if not post_id:
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            author_username = raw.get('ownerUsername', self.username)
            author_id = raw.get('ownerId', '')
            author_display_name = raw.get('ownerFullName', '')
            
            timestamp = raw.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    created_at = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            else:
                created_at = None
            
            reel = SocialPost(
                platform=PlatformType.INSTAGRAM,
                post_id=post_id,
                content_type=ContentType.REEL,
                author_id=author_id,
                author_username=author_username,
                author_display_name=author_display_name,
                text=raw.get('caption', ''),
                like_count=raw.get('likesCount', 0),
                comment_count=raw.get('commentsCount', 0),
                view_count=raw.get('videoViewCount') or raw.get('videoPlayCount') or raw.get('playCount', 0),
                comments_disabled=raw.get('isCommentsDisabled', False),
                is_pinned=raw.get('isPinned', False),
                is_promoted=raw.get('isSponsored', False),
                created_at=created_at,
                post_url=raw.get('url') or f"https://www.instagram.com/p/{post_id}/",
                raw_data=raw_data_json
            )
            
            # 解析媒體項目
            video_url = raw.get('videoUrl')
            if video_url:
                reel.media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=video_url,
                    thumbnail_url=raw.get('displayUrl'),
                    duration=raw.get('videoDuration'),
                    width=raw.get('dimensionsWidth'),
                    height=raw.get('dimensionsHeight')
                ))
            else:
                # 如果沒有 videoUrl，嘗試從 images 中取得
                images = raw.get('images', [])
                if images and len(images) > 0:
                    reel.media_items.append(MediaItem(
                        media_type=MediaType.IMAGE,
                        url=images[0],
                        width=raw.get('dimensionsWidth'),
                        height=raw.get('dimensionsHeight')
                    ))
            
            # 提取 hashtags 和 mentions
            if 'hashtags' in raw and isinstance(raw['hashtags'], list):
                reel.hashtags = raw['hashtags']
            else:
                reel.hashtags = self._extract_hashtags(reel.text)
            
            if 'mentions' in raw and isinstance(raw['mentions'], list):
                reel.mentions = raw['mentions']
            
            return reel
        
        except Exception as e:
            print(f"[Instagram] 解析 Reel 失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_story(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析限時動態資料"""
        try:
            # 新格式檢查：必須有 media_url
            media_url = raw.get('media_url')
            if not media_url:
                # 嘗試舊格式
                return self._parse_story_old_format(raw)

            raw_data_json = json.dumps(raw, ensure_ascii=False)

            # 新格式欄位
            username = raw.get('username', self.username)
            user_id = raw.get('user_id') or ''

            # 解析時間戳記（ISO 格式字串）
            timestamp_str = raw.get('timestamp')
            if timestamp_str:
                try:
                    created_at = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    expires_at = created_at + datetime.timedelta(days=1)
                except Exception:
                    created_at = None
                    expires_at = None
            else:
                created_at = None
                expires_at = None

            # 生成 story_id（新格式沒有 pk，使用 URL hash 或時間戳）
            import hashlib
            story_id = hashlib.md5(media_url.encode()).hexdigest()[:16]

            story = SocialPost(
                platform=PlatformType.INSTAGRAM,
                post_id=story_id,
                content_type=ContentType.STORY,
                author_id=str(user_id),
                author_username=username,
                created_at=created_at,
                expires_at=expires_at,
                raw_data=raw_data_json
            )

            # 判斷媒體類型
            has_audio = raw.get('has_audio', False)
            duration = raw.get('duration', 0)
            thumbnail_url = raw.get('thumbnail_url')

            # 根據 has_audio 或 URL 判斷是影片還是圖片
            is_video = has_audio or duration > 0 or '.mp4' in media_url.lower()

            if is_video:
                story.media_items.append(MediaItem(
                    media_type=MediaType.VIDEO,
                    url=media_url,
                    thumbnail_url=thumbnail_url,
                    duration=duration if duration > 0 else None
                ))
            else:
                story.media_items.append(MediaItem(
                    media_type=MediaType.IMAGE,
                    url=media_url,
                    thumbnail_url=thumbnail_url
                ))

            return story

        except Exception as e:
            print(f"[Instagram] 解析限時動態失敗: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_story_old_format(self, raw: Dict[str, Any]) -> Optional[SocialPost]:
        """解析限時動態資料（舊格式）"""
        try:
            story_id = raw.get('pk')
            if not story_id:
                return None

            raw_data_json = json.dumps(raw, ensure_ascii=False)

            user = raw.get('user', {})
            author_id = user.get('id', '')
            author_username = user.get('username', self.username)

            taken_at = raw.get('taken_at')
            if taken_at:
                created_at = datetime.datetime.fromtimestamp(taken_at)
                expires_at = created_at + datetime.timedelta(days=1)
            else:
                created_at = None
                expires_at = None

            story = SocialPost(
                platform=PlatformType.INSTAGRAM,
                post_id=str(story_id),
                content_type=ContentType.STORY,
                author_id=str(author_id),
                author_username=author_username,
                created_at=created_at,
                expires_at=expires_at,
                raw_data=raw_data_json
            )

            video_versions = raw.get('video_versions', [])
            if video_versions:
                video_url = video_versions[0].get('url')
                if video_url:
                    story.media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=video_url,
                        width=video_versions[0].get('width'),
                        height=video_versions[0].get('height')
                    ))

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
            print(f"[Instagram] 解析限時動態失敗（舊格式）: {e}")
            return None
    
    def _parse_media(self, raw: Dict[str, Any]) -> List[MediaItem]:
        """解析媒體項目"""
        media_items = []
        media_type = raw.get('type')
        
        if media_type == 'Sidecar':
            children = raw.get('childPosts') or raw.get('sidecarChildren', [])
            for child in children:
                if child.get('type') == 'Video' or child.get('videoUrl'):
                    video_url = child.get('videoUrl')
                    if video_url:
                        media_items.append(MediaItem(
                            media_type=MediaType.VIDEO,
                            url=video_url,
                            thumbnail_url=child.get('displayUrl') or child.get('imageUrl'),
                            duration=child.get('videoDuration')
                        ))
                else:
                    image_url = child.get('displayUrl') or child.get('imageUrl')
                    if image_url:
                        media_items.append(MediaItem(
                            media_type=MediaType.IMAGE,
                            url=image_url
                        ))
        else:
            if media_type == 'Video' or raw.get('videoUrl'):
                video_url = raw.get('videoUrl')
                if video_url:
                    media_items.append(MediaItem(
                        media_type=MediaType.VIDEO,
                        url=video_url,
                        thumbnail_url=raw.get('displayUrl') or raw.get('imageUrl'),
                        duration=raw.get('videoDuration')
                    ))
            
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
    HASHTAG_SCRAPER = APIFY_ACTORS['instagram']['hashtag']
    
    def __init__(self, hashtag, api_token: str, results_type: str = "posts", results_limit: int = 50):
        """
        初始化 Instagram Hashtag 收集器
        
        參數:
            hashtag: Instagram hashtag 或 hashtag 列表（可含或不含 # 符號）
                    - 單個 hashtag: str，例如 "elonmusk"
                    - 多個 hashtag: List[str]，例如 ["elonmusk", "travel", "food"]
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
            
            print(f"\n[步驟 1/1] 抓取 hashtag 貼文...")
            posts = self._fetch_hashtag_posts(clean_hashtags, r_type, r_limit)
            
            finished_at = datetime.datetime.now()
            duration_seconds = int((finished_at - started_at).total_seconds())
            
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
            
            posts = []
            for item in items:
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
            post_id = raw.get('shortCode') or raw.get('id', '')
            if not post_id:
                return None
            
            raw_data_json = json.dumps(raw, ensure_ascii=False)
            
            author_username = raw.get('ownerUsername', '')
            author_id = raw.get('ownerId', '')
            author_display_name = raw.get('ownerFullName', '')
            
            product_type = raw.get('productType', '').lower()
            post_type = raw.get('type', '').lower()
            
            if 'reel' in product_type or 'clips' in product_type or 'video' in post_type:
                content_type = ContentType.REEL
            else:
                content_type = ContentType.POST
            
            timestamp = raw.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = timestamp.replace('Z', '+00:00')
                    created_at = datetime.datetime.fromisoformat(timestamp)
                else:
                    created_at = datetime.datetime.fromtimestamp(timestamp)
            else:
                created_at = None
            
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
            
            post.media_items = self._parse_media(raw)
            
            if 'hashtags' in raw and isinstance(raw['hashtags'], list):
                post.hashtags = raw['hashtags']
            else:
                post.hashtags = self._extract_hashtags(post.text)
            
            if 'mentions' in raw and isinstance(raw['mentions'], list):
                post.mentions = raw['mentions']
            
            return post
        
        except Exception as e:
            print(f"[Instagram Hashtag] 解析貼文失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
            hashtag_dir = os.path.join(save_dir, f"hashtag_{self.hashtags[0]}")
            os.makedirs(hashtag_dir, exist_ok=True)
            
            success_count = 0
            for index, media in enumerate(post.media_items):
                ext = 'mp4' if media.media_type == MediaType.VIDEO else 'jpg'
                filename = f"{post.post_id}_{index}.{ext}"
                file_path = os.path.join(hashtag_dir, filename)
                
                if self.downloader.download(media.url, file_path):
                    media.local_path = file_path
                    success_count += 1
            
            return success_count > 0
        
        except Exception as e:
            print(f"[Instagram Hashtag] 下載媒體失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

