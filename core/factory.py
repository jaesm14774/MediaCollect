"""
社群媒體收集器工廠
自動選擇並建立對應平台的收集器
"""
from typing import Optional, Dict, Type
from .base_collector import BaseSocialMediaCollector
from .data_models import PlatformType


class CollectorFactory:
    """
    收集器工廠類別
    
    使用範例:
        factory = CollectorFactory()
        collector = factory.create_collector(
            platform="instagram",
            username="example_user",
            api_token="your_token"
        )
        result = collector.collect_all()
    """
    
    # 儲存已註冊的收集器類別
    _collectors: Dict[PlatformType, Type[BaseSocialMediaCollector]] = {}
    
    @classmethod
    def register_collector(
        cls, 
        platform: PlatformType, 
        collector_class: Type[BaseSocialMediaCollector]
    ):
        """
        註冊收集器類別
        
        參數:
            platform: 平台類型
            collector_class: 收集器類別
        """
        cls._collectors[platform] = collector_class
        print(f"[Factory] 已註冊 {platform.value} 收集器: {collector_class.__name__}")
    
    @classmethod
    def create_collector(
        cls,
        platform: str,
        username: str,
        api_token: str,
        **kwargs
    ) -> Optional[BaseSocialMediaCollector]:
        """
        建立指定平台的收集器
        
        參數:
            platform: 平台名稱 (instagram, facebook, twitter, threads 等)
            username: 目標使用者名稱
            api_token: API 金鑰
            **kwargs: 其他平台特定參數
        
        返回:
            收集器實例，若平台不支援則返回 None
        """
        # 將字串轉換為 PlatformType
        try:
            platform_enum = PlatformType(platform.lower())
        except ValueError:
            print(f"[Factory] 不支援的平台: {platform}")
            print(f"[Factory] 支援的平台: {', '.join([p.value for p in PlatformType])}")
            return None
        
        # 檢查是否已註冊該平台的收集器
        if platform_enum not in cls._collectors:
            print(f"[Factory] {platform} 收集器尚未實作")
            print(f"[Factory] 已實作的平台: {', '.join([p.value for p in cls._collectors.keys()])}")
            return None
        
        # 建立收集器實例
        collector_class = cls._collectors[platform_enum]
        try:
            collector = collector_class(
                username=username,
                api_token=api_token,
                **kwargs
            )
            print(f"[Factory] 成功建立 {platform} 收集器")
            return collector
        except Exception as e:
            print(f"[Factory] 建立收集器失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """
        取得所有已註冊的平台列表
        
        返回:
            平台名稱列表
        """
        return [platform.value for platform in cls._collectors.keys()]
    
    @classmethod
    def is_platform_supported(cls, platform: str) -> bool:
        """
        檢查平台是否已支援
        
        參數:
            platform: 平台名稱
        
        返回:
            是否支援
        """
        try:
            platform_enum = PlatformType(platform.lower())
            return platform_enum in cls._collectors
        except ValueError:
            return False


def register_all_collectors():
    """
    註冊所有已實作的收集器
    在主程式啟動時呼叫此函式
    """
    from .data_models import PlatformType
    
    # Instagram
    try:
        from platforms.instagram_collector import InstagramCollector
        CollectorFactory.register_collector(PlatformType.INSTAGRAM, InstagramCollector)
    except ImportError as e:
        print(f"[Factory] 無法載入 Instagram 收集器: {e}")
    
    # Facebook
    try:
        from platforms.facebook_collector import FacebookCollector
        CollectorFactory.register_collector(PlatformType.FACEBOOK, FacebookCollector)
    except ImportError as e:
        print(f"[Factory] 無法載入 Facebook 收集器: {e}")
    
    # Twitter
    try:
        from platforms.twitter_collector import TwitterCollector
        CollectorFactory.register_collector(PlatformType.TWITTER, TwitterCollector)
    except ImportError as e:
        print(f"[Factory] 無法載入 Twitter 收集器: {e}")
    
    # Threads
    try:
        from platforms.threads_collector import ThreadsCollector
        CollectorFactory.register_collector(PlatformType.THREADS, ThreadsCollector)
    except ImportError as e:
        print(f"[Factory] 無法載入 Threads 收集器: {e}")
    
    print(f"\n[Factory] 已註冊 {len(CollectorFactory.get_supported_platforms())} 個平台收集器")
    print(f"[Factory] 支援的平台: {', '.join(CollectorFactory.get_supported_platforms())}\n")

