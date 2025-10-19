"""
社群媒體收集器抽象基類
定義所有平台收集器必須實作的介面
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .data_models import (
    PlatformType, PlatformUser, SocialPost, 
    CollectionResult, ContentType
)
import pandas as pd


class BaseSocialMediaCollector(ABC):
    """
    社群媒體收集器抽象基類
    
    所有平台的收集器都必須繼承此類別並實作抽象方法
    """
    
    def __init__(self, username: str, api_token: str, platform: PlatformType):
        """
        初始化收集器
        
        參數:
            username: 目標使用者名稱
            api_token: API 金鑰
            platform: 平台類型
        """
        self.username = username
        self.api_token = api_token
        self.platform = platform
        self.user_info: Optional[PlatformUser] = None
    
    # =========================================================================
    # 必須實作的抽象方法（子類別必須覆寫）
    # =========================================================================
    
    @abstractmethod
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """
        抓取使用者基本資料
        
        返回:
            PlatformUser 物件，若失敗則返回 None
        """
        pass
    
    @abstractmethod
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """
        抓取使用者貼文
        
        參數:
            limit: 要抓取的貼文數量
        
        返回:
            SocialPost 物件列表
        """
        pass
    
    @abstractmethod
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """
        抓取限時動態（如果平台支援）
        
        參數:
            limit: 要抓取的限時動態數量（None 表示全部抓取）
        
        返回:
            SocialPost 物件列表
        """
        pass
    
    @abstractmethod
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """
        下載貼文中的媒體檔案
        
        參數:
            post: 社群貼文物件
            save_dir: 儲存目錄
        
        返回:
            是否成功下載
        """
        pass
    
    # =========================================================================
    # 可選的方法（子類別可以覆寫）
    # =========================================================================
    
    def fetch_comments(self, post_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        抓取貼文留言（選用功能）
        
        參數:
            post_id: 貼文 ID
            limit: 要抓取的留言數量
        
        返回:
            留言資料列表
        """
        return []
    
    def fetch_user_followers(self, limit: int = 100) -> List[str]:
        """
        抓取使用者的追蹤者列表（選用功能）
        
        參數:
            limit: 要抓取的追蹤者數量
        
        返回:
            追蹤者使用者名稱列表
        """
        return []
    
    def fetch_user_following(self, limit: int = 100) -> List[str]:
        """
        抓取使用者的追蹤中列表（選用功能）
        
        參數:
            limit: 要抓取的追蹤中數量
        
        返回:
            追蹤中使用者名稱列表
        """
        return []
    
    # =========================================================================
    # 通用方法（所有子類別共用）
    # =========================================================================
    
    def collect_all(
        self, 
        post_limit: int = 50, 
        story_limit: Optional[int] = None,
        include_stories: bool = True
    ) -> CollectionResult:
        """
        執行完整的資料收集流程
        
        參數:
            post_limit: 要抓取的貼文數量
            story_limit: 要抓取的限時動態數量
            include_stories: 是否抓取限時動態
        
        返回:
            CollectionResult 物件
        """
        try:
            # 1. 抓取使用者資料
            print(f"[{self.platform.value}] 開始抓取使用者 {self.username} 的資料...")
            user = self.fetch_user_profile()
            
            if not user:
                return CollectionResult(
                    platform=self.platform,
                    success=False,
                    error_message=f"無法取得使用者 {self.username} 的資料"
                )
            
            self.user_info = user
            print(f"  ✓ 使用者資料: {user.display_name or user.username}")
            
            # 2. 抓取貼文
            print(f"[{self.platform.value}] 開始抓取貼文（限制: {post_limit} 筆）...")
            posts = self.fetch_posts(limit=post_limit)
            print(f"  ✓ 成功抓取 {len(posts)} 筆貼文")
            
            # 3. 抓取限時動態（如果支援）
            stories = []
            if include_stories:
                print(f"[{self.platform.value}] 開始抓取限時動態...")
                stories = self.fetch_stories(limit=story_limit)
                print(f"  ✓ 成功抓取 {len(stories)} 筆限時動態")
            
            return CollectionResult(
                platform=self.platform,
                success=True,
                user=user,
                posts=posts,
                stories=stories
            )
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            print(f"[錯誤] {error_msg}")
            
            return CollectionResult(
                platform=self.platform,
                success=False,
                error_message=error_msg
            )
    
    def validate_username(self) -> bool:
        """
        驗證使用者名稱是否有效
        
        返回:
            是否有效
        """
        if not self.username or len(self.username) == 0:
            return False
        return True
    
    def get_platform_name(self) -> str:
        """取得平台名稱"""
        return self.platform.value
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(platform={self.platform.value}, username={self.username})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ApifyBasedCollector(BaseSocialMediaCollector):
    """
    基於 Apify 的收集器基類
    為使用 Apify API 的平台提供共用功能
    """
    
    def __init__(self, username: str, api_token: str, platform: PlatformType):
        super().__init__(username, api_token, platform)
        
        # 延遲載入 ApifyClient 以避免未安裝時報錯
        try:
            from apify_client import ApifyClient
            self.apify_client = ApifyClient(api_token)
        except ImportError:
            raise ImportError(
                "請安裝 apify-client 套件: pip install apify-client"
            )
    
    def call_apify_actor(
        self, 
        actor_id: str, 
        run_input: Dict[str, Any],
        timeout: int = 300
    ) -> List[Dict[str, Any]]:
        """
        呼叫 Apify Actor 並取得結果
        
        參數:
            actor_id: Apify Actor ID
            run_input: 輸入參數
            timeout: 超時時間（秒）
        
        返回:
            結果資料列表
        """
        try:
            print(f"  [Apify] 呼叫 Actor: {actor_id}")
            print(f"  [Apify] 輸入參數: {run_input}")
            
            # 執行 Actor
            run = self.apify_client.actor(actor_id).call(
                run_input=run_input,
                timeout_secs=timeout
            )
            
            # 檢查執行狀態
            run_status = run.get("status")
            if run_status != "SUCCEEDED":
                print(f"  [Apify] ⚠ Actor 執行狀態異常: {run_status}")
                # 即使狀態異常，仍嘗試取得資料
            
            # 取得結果
            items = list(
                self.apify_client.dataset(run["defaultDatasetId"]).iterate_items()
            )
            
            # 根據結果數量輸出不同訊息
            if len(items) == 0:
                print(f"  [Apify] ✓ 執行完成，但無符合條件的資料（可能是正常情況）")
            else:
                print(f"  [Apify] ✓ 成功取得 {len(items)} 筆資料")
            
            return items
        
        except Exception as e:
            print(f"  [Apify] ✗ 呼叫失敗: {e}")
            print(f"  [Apify] ℹ 將返回空資料，繼續執行其他任務")
            import traceback
            traceback.print_exc()
            return []

