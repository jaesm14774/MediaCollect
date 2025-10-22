"""
通用社群媒體平台設定檔
"""
import random
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入專案目錄下的 .env 檔案
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path)

# ============================================================================
# Apify API Tokens
# ============================================================================
# 從環境變數讀取多個 Token
APIFY_TOKEN_LIST = []
for i in range(1, 20):  # 支援最多 20 個 Token
    token = os.getenv(f'APIFY_TOKEN_{i}')
    if token:
        APIFY_TOKEN_LIST.append(token)

# 如果沒有設定環境變數，使用預設值（但會顯示警告）
if not APIFY_TOKEN_LIST:
    print("[警告] 未在 .env 中設定 APIFY_TOKEN，請複製 .env.example 為 .env 並填入您的 API Token")
    APIFY_TOKEN = None
else:
    # 隨機選擇一個 Token（分散負載）
    APIFY_TOKEN = random.choice(APIFY_TOKEN_LIST)

# ============================================================================
# 檔案路徑設定
# ============================================================================
# 媒體儲存根目錄
MEDIA_FOLDER_PATH = os.getenv('MEDIA_FOLDER_PATH', './media/')

# 資料庫設定檔路徑（向下相容舊的設定檔方式）
SQL_CONFIGURE_PATH = os.getenv('SQL_CONFIGURE_PATH', 'sql_config.txt')

# 通知設定檔路徑（向下相容舊的設定檔方式）
DISCORD_PATH = os.getenv('DISCORD_PATH', 'Discord.txt')

# ============================================================================
# 各平台收集參數
# ============================================================================
PLATFORM_SETTINGS = {
    'instagram': {
        'enabled': True,
        'post_limit': 5,          # 每個使用者抓取的貼文數
        'story_limit': None,      # 限時動態數量 (None=全部)
        'download_media': True,   # 是否下載媒體
    },
    'facebook': {
        'enabled': False,
        'post_limit': 10,
        'photo_limit': None,        # 照片抓取數量
        'story_limit': None,
        'download_media': True,
        # 時間範圍設定 (用於限制抓取的貼文時間範圍)
        # 格式: YYYY-MM-DD (如 "2024-01-01")
        #      或相對時間 (如 "1 day", "2 months", "3 years")
        #      或完整 ISO 時間戳 (如 "2025-09-23T10:02:01")
        'posts_newer_than': None,  # 只抓取此日期之後的貼文 (None=不限制)
        'posts_older_than': None,  # 只抓取此日期之前的貼文 (None=不限制)
        'caption_text': False,     # 是否提取影片字幕
    },
    'twitter': {
        'enabled': True,
        'post_limit': 20,         # Twitter 推文較短，可多抓一些
        'story_limit': None,
        'download_media': True,
        # Hashtag 搜尋設定
        'hashtag_limit': 1000,      # Hashtag 搜尋的推文數量
        # 進階搜尋設定
        'search_sort': 'Latest',  # 搜尋排序: "Latest" 或 "Top"
    },
    'threads': {
        'enabled': False,
        'post_limit': 15,
        'story_limit': None,
        'download_media': True,
    }
}

# ============================================================================
# 下載設定
# ============================================================================
RETRY_COUNT = 3              # 下載失敗重試次數
DOWNLOAD_TIMEOUT = 30        # 下載超時時間（秒）
REQUEST_TIMEOUT = 30         # 請求超時時間（秒）

# ============================================================================
# 延遲設定（避免被限制）
# ============================================================================
MIN_DELAY = 5                # 最小延遲（秒）
MAX_DELAY = 10               # 最大延遲（秒）
BATCH_DELAY_MIN = 5        # 每批次之間的最小延遲（秒）
BATCH_DELAY_MAX = 60       # 每批次之間的最大延遲（秒）
BATCH_SIZE = 3               # 多少個使用者算一批

# ============================================================================
# Apify Actor IDs (各平台的爬蟲 ID)
# ============================================================================
APIFY_ACTORS = {
    'instagram': {
        'profile': 'apify/instagram-profile-scraper',
        'post': 'apify/instagram-post-scraper',
        'story': 'igview-owner/instagram-story-viewer'
    },
    'facebook': {
        'profile': 'apify/facebook-pages-scraper',
        'post': 'apify/facebook-posts-scraper',
        'photo': 'apify/facebook-photos-scraper',
        'story': None  # Facebook 限時動態需要登入
    },
    'twitter': {
        'profile': 'deepanshusharm/twitter-profile-scraper-no-cookies',
        'post': 'xtdata/twitter-x-scraper',
        'hashtag': 'xtdata/twitter-x-scraper',
        'search': 'xtdata/twitter-x-scraper',
        'story': None  # Twitter 沒有限時動態
    },
    'threads': {
        'profile': 'apify/threads-scraper',
        'post': 'apify/threads-scraper',
        'story': None  # Threads 目前沒有限時動態
    }
}

# ============================================================================
# 欄位值轉換器 (Field Value Transformers)
# ============================================================================
"""
欄位轉換器讓你可以在資料儲存到資料庫前，將特定欄位的值進行轉換
使用場景：
  - 將數字代碼轉換為易讀的字串（如 media type: 1 -> "IMAGE"）
  - 標準化資料格式
  - 移除不需要的資料
"""

def transform_media_type(value):
    """
    轉換媒體類型數字為易讀字串
    1 -> IMAGE
    2 -> VIDEO
    8 -> CAROUSEL
    其他 -> UNKNOWN_{value}
    """
    media_type_mapping = {
        1: "IMAGE",
        2: "VIDEO",
        8: "CAROUSEL",
        9: "ALBUM",
        10: "LIVE",
        11: "STORY"
    }
    if value is None:
        return None
    return media_type_mapping.get(value, f"UNKNOWN_{value}")

def transform_boolean_to_text(value):
    """
    將布林值轉換為易讀字串
    True -> "是"
    False -> "否"
    """
    if value is None:
        return None
    return "是" if value else "否"

def transform_count_to_display(value):
    """
    將數字轉換為易讀格式
    1234 -> "1.2K"
    1234567 -> "1.2M"
    """
    if value is None:
        return "0"
    
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)


# 欄位轉換規則設定
# 格式：'欄位名稱': 轉換函式
# 設定後，該欄位的值會在儲存到資料庫前經過轉換函式處理
FIELD_TRANSFORMERS = {
    # 媒體類型轉換（將數字轉為字串）
    'primary_media_type': transform_media_type,
    
    # 如果你想轉換其他欄位，可以在這裡新增：
    # 'is_verified': transform_boolean_to_text,
    # 'follower_count': transform_count_to_display,
}

def apply_field_transformers(data_dict: dict) -> dict:
    """
    對字典中的欄位套用轉換規則
    
    參數:
        data_dict: 要轉換的資料字典
    
    返回:
        轉換後的資料字典
    """
    transformed = data_dict.copy()
    
    # 先處理所有欄位，將字串 "None" 轉換為真正的 None
    for key, value in transformed.items():
        if value == "None" or value == "null" or value == "NULL":
            transformed[key] = None
    
    # 再套用特定欄位的轉換規則
    for field_name, transformer_func in FIELD_TRANSFORMERS.items():
        if field_name in transformed:
            try:
                original_value = transformed[field_name]
                transformed[field_name] = transformer_func(original_value)
            except Exception as e:
                print(f"[Config] 欄位轉換失敗 - {field_name}: {e}")
                # 轉換失敗時保留原值
    
    return transformed


# ============================================================================
# 輔助函式
# ============================================================================
def get_platform_setting(platform: str, key: str, default=None):
    """
    取得指定平台的設定值
    
    參數:
        platform: 平台名稱
        key: 設定鍵
        default: 預設值
    
    返回:
        設定值
    """
    return PLATFORM_SETTINGS.get(platform, {}).get(key, default)

def is_platform_enabled(platform: str) -> bool:
    """
    檢查平台是否啟用
    
    參數:
        platform: 平台名稱
    
    返回:
        是否啟用
    """
    return PLATFORM_SETTINGS.get(platform, {}).get('enabled', False)

def get_enabled_platforms() -> list:
    """
    取得所有啟用的平台列表
    
    返回:
        平台名稱列表
    """
    return [
        platform for platform, settings in PLATFORM_SETTINGS.items()
        if settings.get('enabled', False)
    ]

# ============================================================================
# 顯示設定資訊
# ============================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("通用社群媒體平台設定")
    print("=" * 60)
    print(f"\n使用的 Apify Token: {APIFY_TOKEN[:20]}...")
    print(f"媒體儲存路徑: {MEDIA_FOLDER_PATH}")
    print(f"\n啟用的平台: {', '.join(get_enabled_platforms())}")
    print("\n各平台設定:")
    for platform, settings in PLATFORM_SETTINGS.items():
        if settings['enabled']:
            print(f"  - {platform.upper()}")
            print(f"      貼文數: {settings['post_limit']}")
            print(f"      限時動態數: {settings['story_limit'] or '全部'}")
            print(f"      下載媒體: {'是' if settings['download_media'] else '否'}")
    print("=" * 60)

