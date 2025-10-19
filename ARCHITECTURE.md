# 🏗️ 架構設計文檔

## 概述

本系統採用**策略模式 + 工廠模式 + 抽象基類**的設計，實現了一個高度可擴展的多平台社群媒體資料收集系統。

---

## 核心設計模式

### 1. 策略模式 (Strategy Pattern)

不同平台的收集邏輯封裝在各自的收集器類別中，但都實作相同的介面。

```python
# 抽象策略
class BaseSocialMediaCollector(ABC):
    @abstractmethod
    def fetch_user_profile(self) -> PlatformUser: pass
    @abstractmethod
    def fetch_posts(self, limit: int) -> List[SocialPost]: pass
    # ...

# 具體策略
class InstagramCollector(BaseSocialMediaCollector):
    def fetch_user_profile(self):
        # Instagram 特定實作
        pass

class TwitterCollector(BaseSocialMediaCollector):
    def fetch_user_profile(self):
        # Twitter 特定實作
        pass
```

**優點:**
- 各平台邏輯互不干擾
- 易於測試和維護
- 符合開放封閉原則 (OCP)

### 2. 工廠模式 (Factory Pattern)

透過 `CollectorFactory` 自動建立對應平台的收集器。

```python
class CollectorFactory:
    _collectors = {}  # 註冊的收集器
    
    @classmethod
    def create_collector(cls, platform: str, username: str, api_token: str):
        platform_enum = PlatformType(platform)
        collector_class = cls._collectors[platform_enum]
        return collector_class(username, api_token)
```

**優點:**
- 客戶端不需要知道具體類別
- 集中管理物件建立邏輯
- 易於新增新平台

### 3. 模板方法模式 (Template Method Pattern)

基類定義了通用的收集流程，子類別實作具體步驟。

```python
class BaseSocialMediaCollector:
    def collect_all(self, post_limit, story_limit, include_stories):
        # 定義固定流程
        user = self.fetch_user_profile()  # 抽象方法
        posts = self.fetch_posts(post_limit)  # 抽象方法
        stories = self.fetch_stories(story_limit) if include_stories else []
        return CollectionResult(user=user, posts=posts, stories=stories)
```

**優點:**
- 統一的執行流程
- 避免重複程式碼
- 保證一致性

---

## 資料模型設計

### 通用資料類別

使用 `dataclass` 定義跨平台統一的資料結構：

```python
@dataclass
class PlatformUser:
    """通用使用者模型"""
    platform: PlatformType
    user_id: str
    username: str
    display_name: Optional[str]
    is_verified: bool
    follower_count: int
    # ... 所有平台共通的欄位

@dataclass
class SocialPost:
    """通用貼文模型"""
    platform: PlatformType
    post_id: str
    content_type: ContentType
    text: Optional[str]
    like_count: int
    media_items: List[MediaItem]
    # ... 所有平台共通的欄位
```

**設計原則:**
- 涵蓋所有平台的共通欄位
- 不存在的欄位使用 `Optional` 並設為 `None`

### 列舉類型

```python
class PlatformType(Enum):
    """平台類型"""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"

class ContentType(Enum):
    """內容類型"""
    POST = "post"
    TWEET = "tweet"
    REEL = "reel"
    THREAD = "thread"
    STORY = "story"
```

**優點:**
- 型別安全
- 易於擴展
- IDE 自動完成

---

## 模組劃分

### Core 核心模組

```
core/
├── base_collector.py       # 抽象基類
├── data_models.py          # 通用資料模型
├── factory.py              # 工廠管理器
└── database_manager.py     # 資料庫管理器
```

**職責:**
- 定義系統的核心介面和資料結構
- 提供通用功能（資料庫、工廠等）
- 與具體平台無關

### Platforms 平台模組

```
platforms/
├── instagram_collector.py
├── facebook_collector.py
├── twitter_collector.py
└── threads_collector.py
```

**職責:**
- 實作各平台的具體收集邏輯
- 繼承自 `BaseSocialMediaCollector`
- 將平台特定資料轉換為通用格式

### Lib 工具模組

```
lib/
├── media_downloader.py      # 媒體下載
├── get_sql_connection.py    # 資料庫連接
└── discord_notify.py        # 通知功能
```

**職責:**
- 提供可重用的工具函式
- 與業務邏輯解耦

---

## 資料庫設計

### 統一資料表結構

所有平台共用相同的資料表，透過 `platform` 欄位區分：

```sql
-- 使用者表
CREATE TABLE social_users (
    id INT PRIMARY KEY,
    platform VARCHAR(20),  -- 區分平台
    user_id VARCHAR(100),
    username VARCHAR(100),
    -- ... 通用欄位
    UNIQUE KEY (platform, user_id)
);

-- 貼文表
CREATE TABLE social_posts (
    id INT PRIMARY KEY,
    platform VARCHAR(20),  -- 區分平台
    post_id VARCHAR(100),
    board_id INT,  -- 關聯到 social_users.id
    -- ... 通用欄位
    UNIQUE KEY (platform, post_id)
);
```

**設計優點:**
- 統一查詢介面
- 易於跨平台分析
- 減少資料表數量

**查詢範例:**
```sql
-- 查詢所有平台的熱門貼文
SELECT platform, username, text, like_count
FROM social_posts p
JOIN social_users u ON p.board_id = u.id
WHERE like_count > 10000
ORDER BY like_count DESC;

-- 查詢特定平台
SELECT * FROM social_posts 
WHERE platform = 'instagram';
```

---

## 擴展機制

### 新增平台的步驟

#### Step 1: 建立收集器類別

```python
# platforms/tiktok_collector.py
class TikTokCollector(ApifyBasedCollector):
    def __init__(self, username: str, api_token: str):
        super().__init__(username, api_token, PlatformType.TIKTOK)
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        # 呼叫 Apify Actor
        items = self.call_apify_actor(ACTOR_ID, run_input)
        # 解析為通用格式
        return PlatformUser(...)
    
    def fetch_posts(self, limit: int) -> List[SocialPost]:
        # 實作貼文抓取
        pass
    
    def fetch_stories(self, limit: Optional[int]) -> List[SocialPost]:
        # 實作限時動態抓取
        pass
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        # 實作媒體下載
        pass
```

#### Step 2: 註冊到工廠

```python
# core/factory.py
from platforms.tiktok_collector import TikTokCollector

def register_all_collectors():
    CollectorFactory.register_collector(PlatformType.TIKTOK, TikTokCollector)
```

#### Step 3: 更新設定

```python
# config/platform_config.py
PLATFORM_SETTINGS = {
    'tiktok': {
        'enabled': True,
        'post_limit': 50,
        'download_media': True,
    }
}
```

**完成！** 新平台可以直接使用：

```python
collector = CollectorFactory.create_collector('tiktok', 'user', token)
result = collector.collect_all()
```

---

## 錯誤處理機制

### 1. 收集結果封裝

```python
@dataclass
class CollectionResult:
    platform: PlatformType
    success: bool
    user: Optional[PlatformUser]
    posts: List[SocialPost]
    stories: List[SocialPost]
    error_message: Optional[str]
```

**優點:**
- 統一的錯誤回報格式
- 可以部分成功（例如使用者資料成功，貼文失敗）
- 易於記錄和通知

### 2. 異常捕獲層級

```python
# 層級 1: 方法層級
def fetch_posts(self):
    try:
        # 抓取邏輯
    except Exception as e:
        print(f"抓取失敗: {e}")
        return []  # 返回空列表

# 層級 2: 收集流程層級
def collect_all(self):
    try:
        # 完整流程
    except Exception as e:
        return CollectionResult(success=False, error_message=str(e))

# 層級 3: 主程式層級
def batch_collect(self):
    for username in users:
        try:
            self.collect_user(username)
        except Exception as e:
            notify(f"錯誤: {e}")
            continue  # 繼續處理下一個
```

---

## 效能優化

### 1. 批次處理

```python
# 批次延遲避免被限制
for i, user in enumerate(users):
    if i % BATCH_SIZE == 0 and i != 0:
        time.sleep(random.randint(100, 300))
    
    collect_user(user)
    time.sleep(random.randint(5, 13))
```

### 2. 資料庫優化

```sql
-- 建立索引加速查詢
CREATE INDEX idx_platform ON social_users(platform);
CREATE INDEX idx_created ON social_posts(created_at);
CREATE INDEX idx_like_count ON social_posts(like_count);

-- 分區表（大量資料時）
CREATE TABLE social_posts (
    -- ...
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025)
);
```

### 3. 媒體下載優化

```python
class MediaDownloader:
    def download(self, url, file_path, overwrite=False):
        # 檢查檔案是否已存在
        if os.path.exists(file_path) and not overwrite:
            return False
        
        # 重試機制
        for attempt in range(self.retry_count):
            try:
                response = requests.get(url, timeout=self.timeout)
                # 儲存檔案
                return True
            except Exception as e:
                if attempt < self.retry_count - 1:
                    time.sleep(random.uniform(2, 5))
        return False
```

---

## 測試策略

### 1. 單元測試

```python
def test_instagram_collector():
    collector = InstagramCollector('instagram', APIFY_TOKEN)
    
    # 測試使用者資料抓取
    user = collector.fetch_user_profile()
    assert user is not None
    assert user.platform == PlatformType.INSTAGRAM
    assert user.username == 'instagram'
    
    # 測試貼文抓取
    posts = collector.fetch_posts(limit=5)
    assert len(posts) > 0
    assert all(p.platform == PlatformType.INSTAGRAM for p in posts)
```

### 2. 整合測試

```python
def test_full_workflow():
    # 建立收集器
    collector = CollectorFactory.create_collector('instagram', 'user', token)
    
    # 執行收集
    result = collector.collect_all(post_limit=5)
    
    # 驗證結果
    assert result.success
    assert result.user is not None
    assert len(result.posts) > 0
    
    # 儲存到資料庫
    with DatabaseManager(...) as db:
        db.save_collection_result(result)
    
    # 驗證資料庫
    # ...
```

---

## 安全性考量

### 1. API Token 保護

```python
# 不要硬編碼在程式碼中
APIFY_TOKEN = os.getenv('APIFY_TOKEN')

# 或從設定檔讀取
with open('config.txt') as f:
    APIFY_TOKEN = f.read().strip()
```

### 2. SQL 注入防護

```python
# 使用參數化查詢
cursor.execute(
    "SELECT * FROM users WHERE platform = %s AND username = %s",
    (platform, username)
)

# 使用 SQLAlchemy
df.to_sql('table_name', engine, if_exists='append')
```

### 3. 檔案路徑驗證

```python
def download_media(self, url, file_path):
    # 驗證檔案路徑
    if '..' in file_path:
        raise ValueError("Invalid file path")
    
    # 限制儲存目錄
    if not file_path.startswith(MEDIA_FOLDER_PATH):
        raise ValueError("Path outside allowed directory")
```

---

## 總結

### 核心優勢

✅ **高度可擴展**: 新增平台只需實作 4 個方法  
✅ **統一介面**: 所有平台使用相同的 API  
✅ **資料標準化**: 通用資料模型便於分析  
✅ **易於維護**: 模組化設計，職責分明  
✅ **錯誤容忍**: 完善的異常處理機制

### 設計原則遵循

- **SOLID 原則**: 單一職責、開放封閉、依賴反轉
- **DRY 原則**: 避免重複程式碼
- **關注點分離**: 核心、平台、工具完全分離
- **介面隔離**: 最小化介面依賴

### 未來擴展方向

🚀 新增更多平台（TikTok, YouTube, LinkedIn）  
🚀 非同步收集（asyncio）提升效能  
🚀 機器學習整合（情感分析、標籤推薦）  
🚀 Web 管理介面（Flask/Django）  
🚀 RESTful API 服務

---

**這個架構設計讓系統具備了長期維護和擴展的基礎！**

