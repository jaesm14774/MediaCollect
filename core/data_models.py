"""
通用社群媒體資料模型
定義所有平台共用的資料結構
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PlatformType(Enum):
    """社群平台類型"""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class MediaType(Enum):
    """媒體類型"""
    IMAGE = 1
    VIDEO = 2
    CAROUSEL = 8  # 輪播（多張圖片/影片）
    ALBUM = 9     # 相簿
    LIVE = 10     # 直播
    STORY = 11    # 限時動態


class ContentType(Enum):
    """內容類型"""
    POST = "post"           # 一般貼文
    STORY = "story"         # 限時動態
    REEL = "reel"           # 短影片 (IG Reels)
    TWEET = "tweet"         # 推文
    RETWEET = "retweet"     # 轉推
    THREAD = "thread"       # 串文
    LIVE = "live"           # 直播


@dataclass
class PlatformUser:
    """
    通用使用者資料模型
    適用於所有社群平台
    """
    # 基本資訊
    platform: PlatformType                    # 平台類型
    user_id: str                              # 平台內部 ID
    username: str                             # 使用者名稱
    display_name: Optional[str] = None        # 顯示名稱/全名
    
    # 帳號屬性
    is_verified: bool = False                 # 是否認證
    is_private: bool = False                  # 是否私人帳號
    is_business: bool = False                 # 是否商業帳號
    
    # 個人資訊
    description: Optional[str] = None         # 個人簡介
    profile_image_url: Optional[str] = None   # 頭像 URL
    banner_image_url: Optional[str] = None    # 封面圖 URL
    category: Optional[str] = None            # 分類/類別
    
    # 統計數據
    follower_count: int = 0                   # 追蹤者數
    following_count: int = 0                  # 追蹤中數
    post_count: int = 0                       # 貼文數
    
    # 聯絡資訊
    external_url: Optional[str] = None        # 外部連結
    email: Optional[str] = None               # 電子郵件
    phone: Optional[str] = None               # 電話
    
    # 位置資訊
    location: Optional[str] = None            # 地點
    latitude: Optional[float] = None          # 緯度
    longitude: Optional[float] = None         # 經度
    
    # 時間戳記
    created_at: Optional[datetime] = None     # 帳號建立時間
    updated_at: Optional[datetime] = None     # 資料更新時間
    
    raw_data: Optional[str] = None            # 完整原始 JSON 資料（字串格式）
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'platform': self.platform.value,
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'is_verified': self.is_verified,
            'is_private': self.is_private,
            'is_business': self.is_business,
            'description': self.description,
            'profile_image_url': self.profile_image_url,
            'banner_image_url': self.banner_image_url,
            'category': self.category,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'post_count': self.post_count,
            'external_url': self.external_url,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'raw_data': self.raw_data  # 完整原始 JSON 資料
        }


@dataclass
class MediaItem:
    """媒體項目（圖片或影片）"""
    media_type: MediaType                     # 媒體類型
    url: str                                  # 媒體 URL
    thumbnail_url: Optional[str] = None       # 縮圖 URL
    width: Optional[int] = None               # 寬度
    height: Optional[int] = None              # 高度
    duration: Optional[float] = None          # 影片長度（秒）
    file_size: Optional[int] = None           # 檔案大小（bytes）
    alt_text: Optional[str] = None            # 替代文字
    local_path: Optional[str] = None          # 本地儲存路徑


@dataclass
class SocialPost:
    """
    通用貼文資料模型
    適用於所有社群平台的貼文/推文/限時動態等
    """
    # 基本資訊
    platform: PlatformType                    # 平台類型
    post_id: str                              # 貼文 ID
    content_type: ContentType                 # 內容類型
    
    # 作者資訊
    author_id: str                            # 作者 ID
    author_username: str                      # 作者名稱
    author_display_name: Optional[str] = None # 作者顯示名稱
    
    # 內容資訊
    text: Optional[str] = None                # 文字內容
    title: Optional[str] = None               # 標題
    language: Optional[str] = None            # 語言
    
    # 媒體內容
    media_items: List[MediaItem] = field(default_factory=list)  # 媒體列表
    
    # 互動數據
    like_count: int = 0                       # 按讚數
    comment_count: int = 0                    # 留言數
    share_count: int = 0                      # 分享數
    view_count: int = 0                       # 觀看數
    bookmark_count: int = 0                   # 收藏數
    
    # 貼文屬性
    is_pinned: bool = False                   # 是否置頂
    is_promoted: bool = False                 # 是否為廣告/推廣
    comments_disabled: bool = False           # 是否禁止留言
    
    # 位置資訊
    location_name: Optional[str] = None       # 地點名稱
    location_id: Optional[str] = None         # 地點 ID
    latitude: Optional[float] = None          # 緯度
    longitude: Optional[float] = None         # 經度
    
    # 標籤與提及
    hashtags: List[str] = field(default_factory=list)        # 標籤列表
    mentions: List[str] = field(default_factory=list)        # 提及的使用者
    
    # 時間資訊
    created_at: Optional[datetime] = None     # 發布時間
    updated_at: Optional[datetime] = None     # 更新時間
    expires_at: Optional[datetime] = None     # 過期時間（限時動態）
    
    # 連結資訊
    post_url: Optional[str] = None            # 貼文連結
    
    raw_data: Optional[str] = None            # 完整原始 JSON 資料（字串格式）
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'platform': self.platform.value,
            'post_id': self.post_id,
            'content_type': self.content_type.value,
            'author_id': self.author_id,
            'author_username': self.author_username,
            'author_display_name': self.author_display_name,
            'text': self.text,
            'title': self.title,
            'language': self.language,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'view_count': self.view_count,
            'bookmark_count': self.bookmark_count,
            'is_pinned': self.is_pinned,
            'is_promoted': self.is_promoted,
            'comments_disabled': self.comments_disabled,
            'location_name': self.location_name,
            'location_id': self.location_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'hashtags': ','.join(self.hashtags) if self.hashtags else None,
            'mentions': ','.join(self.mentions) if self.mentions else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'post_url': self.post_url,
            'media_count': len(self.media_items),
            'primary_media_type': self.media_items[0].media_type.value if self.media_items else None,
            'primary_media_url': self.media_items[0].url if self.media_items else None,
            'sub_image_url': ','.join([m.url for m in self.get_images()]),
            'sub_video_url': ','.join([m.url for m in self.get_videos()]),
            'sub_thumbnail_url': ','.join([m.thumbnail_url for m in self.media_items if m.thumbnail_url]),
            'raw_data': self.raw_data  # 完整原始 JSON 資料
        }
    
    def get_images(self) -> List[MediaItem]:
        """取得所有圖片"""
        return [m for m in self.media_items if m.media_type == MediaType.IMAGE]
    
    def get_videos(self) -> List[MediaItem]:
        """取得所有影片"""
        return [m for m in self.media_items if m.media_type == MediaType.VIDEO]


@dataclass
class CollectionResult:
    """收集結果"""
    platform: PlatformType
    success: bool
    user: Optional[PlatformUser] = None
    posts: List[SocialPost] = field(default_factory=list)
    stories: List[SocialPost] = field(default_factory=list)
    error_message: Optional[str] = None
    collected_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None       # 開始時間
    finished_at: Optional[datetime] = None      # 完成時間
    duration_seconds: Optional[int] = None      # 執行時長（秒）
    
    def __str__(self) -> str:
        if self.success:
            duration_str = f"{self.duration_seconds}秒" if self.duration_seconds else "N/A"
            return (
                f"收集成功 [{self.platform.value}]\n"
                f"  使用者: {self.user.username if self.user else 'N/A'}\n"
                f"  貼文數: {len(self.posts)}\n"
                f"  限時動態數: {len(self.stories)}\n"
                f"  執行時長: {duration_str}\n"
                f"  收集時間: {self.collected_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            return f"收集失敗 [{self.platform.value}]: {self.error_message}"

