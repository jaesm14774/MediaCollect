# 🌐 通用社群媒體資料收集系統

基於 Apify API 的**多平台社群媒體資料收集系統**，支援 Instagram、Facebook、Twitter(X)、Threads 等平台，可自動抓取使用者資訊、貼文、限時動態，並下載媒體檔案到本地，同時將資料儲存至 MySQL 資料庫。

---

## 📋 目錄

- [功能特色](#-功能特色)
- [支援平台](#-支援平台)
- [系統架構](#-系統架構)
- [快速開始](#-快速開始)
- [安裝步驟](#-安裝步驟)
- [設定說明](#-設定說明)
- [使用方式](#-使用方式)
- [資料表結構](#-資料表結構)
- [擴展新平台](#-擴展新平台)
- [欄位轉換功能](#-欄位轉換功能)
- [API 說明](#-api-說明)
- [常見問題](#-常見問題)
- [Instagram Hashtag 收集器使用指南](#-instagram-hashtag-收集器使用指南)
- [Facebook 收集器完整使用手冊](#-facebook-收集器完整使用手冊)

---

## ✨ 功能特色

### 🎯 核心功能

- ✅ **多平台支援**: 統一介面支援 Instagram、Facebook、Twitter、Threads 等
- ✅ **使用者資訊收集**: 抓取帳號基本資訊、追蹤數、貼文數等
- ✅ **貼文資料收集**: 抓取圖片/影片貼文、輪播貼文、推文、串文等
- ✅ **限時動態收集**: 抓取 24 小時內的 Stories（如果平台支援）
- ✅ **媒體檔案下載**: 自動下載高清圖片和影片
- ✅ **資料庫整合**: 自動儲存至 MySQL 資料庫（統一資料結構）
- ✅ **增量更新**: 智能比對，只更新變更的資料
- ✅ **欄位值轉換**: 自訂義轉換規則，將難以理解的代碼轉為易讀格式
- ✅ **日誌記錄**: 完整的日誌系統，按日期自動分檔
- ✅ **收集歷史追蹤**: 記錄每次收集的執行狀況、成功率、執行時長等
- ✅ **多進程平行處理**: 真正的多核心並行處理，適合處理 Apify Actor 阻塞情況
- ✅ **異步並發**: 支援多使用者同時收集（協程並發）

### 🏗️ 架構特色

- 🔧 **抽象基類設計**: 所有平台共用統一介面
- 🔧 **工廠模式**: 自動選擇對應平台的收集器
- 🔧 **通用資料模型**: 跨平台統一的資料結構
- 🔧 **易於擴展**: 新增平台只需實作 4 個核心方法
- 🔧 **模組化設計**: 核心、平台、工具完全分離
- 🔧 **完整監控**: 日誌記錄 + 歷史追蹤，方便除錯與效能分析

---

## 🌍 支援平台

| 平台 | 狀態 | 支援功能 | Apify Actor |
|------|------|----------|-------------|
| **Instagram** | ✅ 完整支援 | 使用者資訊、貼文、限時動態、輪播、Hashtag 主題追蹤 | apify/instagram-profile-scraper<br>apify/instagram-post-scraper<br>igview-owner/instagram-story-viewer<br>apify/instagram-hashtag-scraper |
| **Facebook** | ✅ 完整支援 | 粉絲專頁資訊、貼文、照片 (含OCR) | apify/facebook-pages-scraper<br>apify/facebook-posts-scraper<br>apify/facebook-photos-scraper |
| **Twitter(X)** | ✅ 支援 | 使用者資訊、推文、轉推 | apify/twitter-scraper |
| **Threads** | ✅ 支援 | 使用者資訊、串文 | apify/threads-scraper |
| **TikTok** | 🚧 規劃中 | - | - |
| **YouTube** | 🚧 規劃中 | - | - |

---

## 🏗️ 系統架構

```
social_media_crawler/
│
├── core/                          # 核心模組
│   ├── base_collector.py         # 抽象基類
│   ├── data_models.py             # 通用資料模型
│   ├── factory.py                 # 收集器工廠
│   └── database_manager.py        # 資料庫管理器
│
├── platforms/                     # 平台實作
│   ├── instagram_collector.py    # Instagram 收集器
│   ├── facebook_collector.py     # Facebook 收集器
│   ├── twitter_collector.py      # Twitter(X) 收集器
│   └── threads_collector.py      # Threads 收集器
│
├── lib/                           # 工具模組
│   ├── logger.py                 # 日誌管理模組（新增）
│   ├── media_downloader.py       # 媒體下載工具
│   ├── get_sql_connection.py     # 資料庫連接
│   └── discord_notify.py         # Discord 通知
│
├── config/                        # 設定檔
│   ├── config.py                 # 通用設定
│   └── platform_config.py        # 各平台設定
│
├── main.py                        # 主程式入口
├── query_collection_history.py   # 收集歷史查詢工具（新增）
├── example_unified.py             # 使用範例
├── init_unified_database.sql     # 資料庫初始化腳本
├── LOG_FEATURE.md                # 日誌功能說明文件（新增）
└── requirements.txt               # 依賴套件
```

### 核心類別關係圖

```
BaseSocialMediaCollector (抽象基類)
    ↓
ApifyBasedCollector (Apify 基類)
    ↓
    ├── InstagramCollector
    │   └── InstagramHashtagCollector (主題標籤收集器)
    ├── FacebookCollector
    ├── TwitterCollector
    └── ThreadsCollector

CollectorFactory (工廠)
    └── 自動建立對應平台的收集器

DatabaseManager (資料庫管理)
    └── 統一儲存所有平台資料
```


## 📦 安裝步驟

### 1. 環境需求

- Python 3.8+
- MySQL 5.7+ / MariaDB 10.3+
- Apify 帳號（需要 API Token）

### 2. 安裝依賴套件

```bash
pip install -r requirements.txt
```

**requirements.txt 內容:**
```txt
pandas>=1.5.0
numpy>=1.23.0
requests>=2.28.0
apify-client>=1.3.0
pymysql>=1.0.2
sqlalchemy>=1.4.0
python-dotenv>=0.21.0
```

### 3. 資料庫初始化

執行 SQL 腳本建立資料表：

```bash
mysql -u your_user -p crawler < init_unified_database.sql
```

或在 MySQL 客戶端中執行：

```sql
source init_unified_database.sql;
```

---

## ⚙️ 設定說明

### 1. 環境變數設定（推薦）

**第一步：複製環境變數範本**

```bash
cp .env.example .env
```

**第二步：編輯 .env 檔案**

```env
# Apify API Token（可設定多個，系統會隨機選擇）
APIFY_TOKEN_1=apify_api_your_token_1
APIFY_TOKEN_2=apify_api_your_token_2
APIFY_TOKEN_3=apify_api_your_token_3

# 媒體儲存路徑
MEDIA_FOLDER_PATH=E:/your_path/SocialMedia/

# 資料庫設定
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=crawler

# Discord 通知（選用）
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

> 📘 **詳細設定指南**：請參閱 [SETUP.md](SETUP.md) 取得完整的環境設定說明。

### 2. 帳號列表設定

如果要使用每日收集功能，需要設定帳號列表：

```bash
# 複製範本
cp accounts.example.txt accounts.txt

# 編輯檔案，填入要收集的帳號
```

`accounts.txt` 格式：
```ini
[instagram]
nasa
natgeo

[twitter]
twitter
elonmusk
```

### 3. 平台啟用設定（選用）

在 `config/platform_config.py` 中可以調整各平台的參數：

```python
PLATFORM_SETTINGS = {
    'instagram': {
        'enabled': True,      # 是否啟用
        'post_limit': 50,     # 每次抓取貼文數
        'story_limit': None,  # 限時動態數量
        'download_media': True,
    },
    'facebook': {
        'enabled': False,
        'post_limit': 10,
        'photo_limit': 10,
        'story_limit': None,
        'download_media': True,
        # 時間範圍設定（只適用於 Facebook）
        'posts_newer_than': None,  # 只抓取此日期之後的貼文
        'posts_older_than': None,  # 只抓取此日期之前的貼文
        'caption_text': False,     # 是否提取影片字幕
    },
    # ... 其他平台
}
```

#### Facebook 時間範圍設定說明

Facebook 收集器支援時間範圍過濾，可以精確控制要抓取的貼文時間範圍：

**支援的時間格式：**
- **絕對日期**：`"2024-01-01"` (YYYY-MM-DD)
- **完整時間戳**：`"2025-09-23T10:02:01"` (ISO 8601 格式)
- **相對時間**：`"1 day"`, `"2 months"`, `"3 years"`, `"1 hour"`, `"30 minutes"`

**使用範例：**
```python
# 只抓取最近 7 天的貼文
'posts_newer_than': "7 days",

# 抓取特定時間範圍的貼文
'posts_newer_than': "2024-01-01",
'posts_older_than': "2024-12-31",

# 抓取最近一個月且提取影片字幕
'posts_newer_than': "1 month",
'caption_text': True,
```

### 4. 舊版設定檔（向下相容）

如果您不想使用 `.env` 檔案，仍可使用舊版設定檔：

**資料庫設定檔 `sql_config.txt`：**
```csv
name,value
ip,127.0.0.1
port,3306
user,your_username
password,your_password
```

**Discord 通知設定檔 `Discord.txt`：**
```csv
name,token
程式bug權杖,your_discord_webhook_url
```

> ⚠️ 舊版設定檔雖然仍可使用，但建議遷移到 `.env` 以提高安全性。

---

## 📖 使用方式

### 方式 1: 每日排程收集（推薦）

**最簡單的使用方式，適合定期排程執行！**

```bash
# 每日收集（從 accounts.txt 讀取帳號）
python main.py --mode daily

# 使用自訂配置檔
python main.py --mode daily --accounts-file my_accounts.txt

# 🚀 多進程平行處理（推薦！真正的平行處理）
python main.py --mode daily --multiprocess --num-processes 4

# 異步並發模式（協程並發）
python main.py --mode daily --async --concurrent-limit 3
```

> 💡 **效能提升**：
> 
> **多進程模式（`--multiprocess`）**：
> - 真正的多核心平行處理，每個使用者在獨立進程中執行
> - **最適合處理 Apify Actor 阻塞等待的情況**（如時間篩選導致重啟）
> - 即使單個任務被阻塞，其他進程仍繼續執行
> - 可以充分利用多核心 CPU
> 
> **異步模式（`--async`）**：
> - 協程並發，共用單一進程
> - 適合 I/O 密集但不會長時間阻塞的任務
> - 如果 Apify Actor 會阻塞等待，效果有限

**配置檔格式 (`accounts.txt`):**

```ini
# Instagram 帳號清單
[instagram]
nasa
natgeo
instagram

# Facebook 粉絲專頁
[facebook]
facebook
microsoft

# Twitter 帳號
[twitter]
twitter
elonmusk

# Threads 帳號
[threads]
zuck
instagram
```

### 方式 2: 使用主程式（進階）

```bash
# 互動式模式
python main.py --mode interactive

# 單一使用者
python main.py --mode single --platform instagram --username nasa --post-limit 10

# 單一使用者（加上時間篩選參數，適用於 Facebook）
python main.py --mode single --platform facebook --username nasa --posts-newer-than "2024-01-01" --posts-older-than "2024-12-31"
python main.py --mode single --platform facebook --username nasa --posts-newer-than "1 month" --caption-text

# 批次處理（從資料庫讀取）
python main.py --mode batch --platform twitter

# 批次處理（多進程模式，推薦）
python main.py --mode batch --platform instagram --multiprocess --num-processes 4

# 批次處理（異步並發模式）
python main.py --mode batch --platform instagram --async --concurrent-limit 5

# 所有平台批次處理（從資料庫讀取）
python main.py --mode all
```

### 方式 3: 使用範例程式

```bash
python example_unified.py
```

會顯示互動式選單，讓你選擇不同的範例。

### 方式 4: 在程式碼中使用

#### 基本使用範例

```python
from core.factory import CollectorFactory, register_all_collectors
from core.database_manager import create_database_manager_from_config
from config.platform_config import APIFY_TOKEN, SQL_CONFIGURE_PATH

# 註冊收集器
register_all_collectors()

# 建立收集器
collector = CollectorFactory.create_collector(
    platform='instagram',
    username='nasa',
    api_token=APIFY_TOKEN
)

# 收集資料
result = collector.collect_all(
    post_limit=20,
    story_limit=10,
    include_stories=True
)

# 儲存到資料庫
if result.success:
    with create_database_manager_from_config(SQL_CONFIGURE_PATH) as db:
        db.save_collection_result(result)
    
    # 下載媒體
    for post in result.posts:
        collector.download_media(post, 'E:/media/')
```

#### Instagram Hashtag 主題追蹤範例

```python
from platforms.instagram_collector import InstagramHashtagCollector
from config.platform_config import APIFY_TOKEN

# 建立 Instagram Hashtag 收集器
hashtag_collector = InstagramHashtagCollector(
    hashtag="travel",  # 要追蹤的主題標籤
    api_token=APIFY_TOKEN,
    results_type="posts",  # "posts" 或 "reels"
    results_limit=50
)

# 收集 hashtag 貼文
result = hashtag_collector.collect_hashtag()

print(f"成功: {result.success}")
print(f"Hashtag: #{result.hashtag}")
print(f"貼文數: {len(result.posts)}")

# 查看貼文資訊
for post in result.posts[:5]:
    print(f"\n作者: @{post.author_username}")
    print(f"內容: {post.text[:100]}...")
    print(f"互動: ❤️ {post.like_count} 💬 {post.comment_count}")
```

#### Facebook 時間範圍過濾範例

```python
from core.factory import CollectorFactory, register_all_collectors
from config.platform_config import APIFY_TOKEN

# 註冊收集器
register_all_collectors()

# 建立 Facebook 收集器
collector = CollectorFactory.create_collector(
    platform='facebook',
    username='microsoft',  # Facebook 粉絲專頁名稱
    api_token=APIFY_TOKEN
)

# 範例 1: 只抓取最近 7 天的貼文
result = collector.collect_all(
    post_limit=50,
    posts_newer_than="7 days",
    caption_text=True  # 提取影片字幕
)

# 範例 2: 抓取特定時間範圍的貼文
result = collector.collect_all(
    post_limit=100,
    posts_newer_than="2024-01-01",
    posts_older_than="2024-12-31"
)

# 範例 3: 抓取最近一個月的貼文
result = collector.collect_all(
    post_limit=50,
    posts_newer_than="1 month"
)

# 範例 4: 使用完整時間戳
result = collector.collect_all(
    post_limit=30,
    posts_newer_than="2025-10-01T00:00:00",
    posts_older_than="2025-10-20T23:59:59"
)
```

#### 使用 main.py 指定時間範圍

```python
from main import SocialMediaCrawler
from config.platform_config import APIFY_TOKEN

crawler = SocialMediaCrawler()

# 收集 Facebook 粉絲專頁最近 7 天的貼文
result = crawler.collect_user(
    platform='facebook',
    username='microsoft',
    post_limit=50,
    posts_newer_than="7 days",
    caption_text=True
)

print(f"成功: {result.success}")
print(f"貼文數: {len(result.posts)}")
```

---

## 🗄️ 資料表結構

### 統一資料表設計

所有平台共用以下資料表，透過 `platform` 欄位區分：

#### 1. social_users - 使用者表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INT | 自增主鍵 |
| platform | VARCHAR(20) | 平台類型 (instagram, facebook, twitter, threads) |
| user_id | VARCHAR(100) | 平台使用者 ID |
| username | VARCHAR(100) | 使用者名稱 |
| display_name | VARCHAR(200) | 顯示名稱 |
| is_verified | BOOLEAN | 是否認證 |
| follower_count | INT | 追蹤者數 |
| following_count | INT | 追蹤中數 |
| post_count | INT | 貼文數 |
| ... | ... | ... |

**唯一鍵**: (platform, user_id)

#### 2. social_posts - 貼文表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INT | 自增主鍵 |
| platform | VARCHAR(20) | 平台類型 |
| post_id | VARCHAR(100) | 貼文 ID |
| content_type | VARCHAR(20) | 內容類型 (post, tweet, reel, thread) |
| board_id | INT | 關聯到 social_users.id |
| text | TEXT | 文字內容 |
| like_count | INT | 按讚數 |
| comment_count | INT | 留言數 |
| share_count | INT | 分享數 |
| view_count | INT | 觀看數 |
| ... | ... | ... |

**唯一鍵**: (platform, post_id)

#### 3. social_stories - 限時動態表

類似 social_posts，但專門用於限時動態。

#### 4. platform_config - 平台設定表

儲存各平台的 API Token、Actor ID 等設定。

#### 5. collection_history - 收集歷史表

記錄每次收集任務的執行狀況和結果。

---

## 🔧 擴展新平台

要新增一個新平台（例如 TikTok），只需 3 個步驟：

### Step 1: 建立收集器類別

在 `platforms/` 目錄下建立 `tiktok_collector.py`：

```python
from core.base_collector import ApifyBasedCollector
from core.data_models import PlatformType, PlatformUser, SocialPost

class TikTokCollector(ApifyBasedCollector):
    def __init__(self, username: str, api_token: str):
        super().__init__(username, api_token, PlatformType.TIKTOK)
    
    def fetch_user_profile(self) -> Optional[PlatformUser]:
        # 實作使用者資料抓取
        pass
    
    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        # 實作貼文抓取
        pass
    
    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        # 實作限時動態抓取
        pass
    
    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        # 實作媒體下載
        pass
```

### Step 2: 註冊收集器

在 `core/factory.py` 的 `register_all_collectors()` 函式中添加：

```python
from platforms.tiktok_collector import TikTokCollector
CollectorFactory.register_collector(PlatformType.TIKTOK, TikTokCollector)
```

### Step 3: 更新設定

在 `config/platform_config.py` 的 `PLATFORM_SETTINGS` 中添加：

```python
'tiktok': {
    'enabled': True,
    'post_limit': 50,
    'story_limit': None,
    'download_media': True,
}
```

完成！現在就可以使用：

```python
collector = CollectorFactory.create_collector('tiktok', 'username', api_token)
```

---

## 🔄 欄位轉換功能

### 功能介紹

欄位轉換器允許你在資料儲存到資料庫前，對特定欄位的值進行自動轉換。這對於處理難以理解的代碼（如 Instagram 的 media type：1 代表圖片、2 代表影片）非常有用。

### 使用場景

- **數字代碼轉文字**：將 `1` 轉換為 `"IMAGE"`，`2` 轉換為 `"VIDEO"`
- **布林值本地化**：將 `True/False` 轉換為 `"是"/"否"`
- **數字格式化**：將 `1234567` 轉換為 `"1.2M"`
- **資料清理**：標準化不符合規範的值

### 如何使用

#### 步驟 1：定義轉換函式

在 `config/platform_config.py` 中定義你的轉換函式：

```python
def transform_media_type(value):
    """將媒體類型數字轉換為易讀字串"""
    media_type_mapping = {
        1: "IMAGE",
        2: "VIDEO",
        8: "CAROUSEL",
    }
    if value is None:
        return None
    return media_type_mapping.get(value, f"UNKNOWN_{value}")
```

#### 步驟 2：註冊到 FIELD_TRANSFORMERS

```python
FIELD_TRANSFORMERS = {
    'primary_media_type': transform_media_type,
    'is_verified': transform_boolean_to_text,
    # 可自行新增更多欄位
}
```

#### 步驟 3：自動套用

轉換會在資料儲存時自動執行，無需額外程式碼！

### 內建轉換器

1. **transform_media_type**：媒體類型數字 → 易讀字串
   - `1` → `"IMAGE"`
   - `2` → `"VIDEO"`
   - `8` → `"CAROUSEL"`

2. **transform_boolean_to_text**：布林值 → 中文
   - `True` → `"是"`
   - `False` → `"否"`

3. **transform_count_to_display**：大數字 → 易讀格式
   - `1234` → `"1.2K"`
   - `1234567` → `"1.2M"`

### 自訂義轉換範例

```python
def transform_clean_url(value):
    """移除 URL 追蹤參數"""
    if value is None:
        return value
    import re
    return re.sub(r'\?utm_.*', '', value)

# 註冊
FIELD_TRANSFORMERS = {
    'external_url': transform_clean_url,
}
```

詳細說明請參考：`config/FIELD_TRANSFORMERS_README.md`

### 測試轉換功能

執行測試腳本驗證轉換器是否正常運作：

```bash
python test_field_transformers.py
```

---

## 📚 API 說明

### CollectorFactory

```python
# 建立收集器
collector = CollectorFactory.create_collector(
    platform='instagram',
    username='example_user',
    api_token='your_token'
)

# 取得支援的平台列表
platforms = CollectorFactory.get_supported_platforms()

# 檢查平台是否支援
is_supported = CollectorFactory.is_platform_supported('instagram')
```

### BaseSocialMediaCollector

```python
# 收集所有資料
result = collector.collect_all(
    post_limit=50,
    story_limit=10,
    include_stories=True
)

# 單獨抓取
user = collector.fetch_user_profile()
posts = collector.fetch_posts(limit=20)
stories = collector.fetch_stories(limit=10)

# 下載媒體
collector.download_media(post, save_dir='/path/to/save/')
```

### DatabaseManager

```python
with create_database_manager_from_config(config_path) as db:
    # 儲存收集結果
    db.save_collection_result(result)
    
    # 取得啟用的使用者
    users = db.get_active_users(platform='instagram')
    
    # 取得使用者貼文
    posts = db.get_user_posts(platform='instagram', username='nasa', limit=50)
```

---

## ❓ 常見問題

### Q1: 如何取得 Apify API Token？

1. 前往 [Apify](https://apify.com/) 註冊帳號
2. 登入後進入 Settings > Integrations
3. 複製 API Token

### Q2: 各平台會被封鎖嗎？

本系統使用 Apify 官方 Actor，遵循各平台的使用條款。建議：
- 設定合理的延遲時間
- 避免短時間內大量抓取
- 不要抓取私人帳號

### Q3: 如何新增要監控的使用者？

方法 1: 直接在資料庫的 `social_users` 表中新增記錄
方法 2: 使用程式自動新增：

```python
collector = CollectorFactory.create_collector('instagram', 'new_user', api_token)
result = collector.collect_all()
# 會自動新增到資料庫
```

### Q4: 如何定時執行收集？

#### 步驟 1: 設定帳號配置檔

```bash
# 複製範本
cp accounts.example.txt accounts.txt

# 編輯 accounts.txt，填入要收集的帳號
```

#### 步驟 2: 設定排程

**Windows (工作排程器):**

1. 開啟「工作排程器」(Task Scheduler)
2. 建立基本工作
3. 設定觸發程序（例如：每天早上 6 點）
4. 動作設定：
   - 程式: `python.exe` 或完整路徑 `C:\Python39\python.exe`
   - 引數: `main.py --mode daily`
   - 起始於: `C:\Users\<user>\Desktop\MediaCollect`

或使用命令列建立：
```powershell
# 每天早上 6 點執行
schtasks /create /tn "MediaCollect_Daily" /tr "python C:\path\to\main.py --mode daily" /sc daily /st 06:00
```

**Linux/Mac (Crontab):**

```bash
# 編輯 crontab
crontab -e

# 每天早上 6 點執行
0 6 * * * cd /path/to/MediaCollect && python main.py --mode daily

# 每 6 小時執行一次
0 */6 * * * cd /path/to/MediaCollect && python main.py --mode daily

# 每天早上 6 點和晚上 6 點執行
0 6,18 * * * cd /path/to/MediaCollect && python main.py --mode daily
```

**Docker 定時任務:**

```dockerfile
# 在容器中安裝 cron
RUN apt-get update && apt-get install -y cron

# 添加 crontab
RUN echo "0 6 * * * cd /app && python main.py --mode daily" | crontab -

# 啟動 cron
CMD cron && tail -f /dev/null
```

### Q5: 多個平台的資料如何區分？

所有資料表都有 `platform` 欄位，可以輕鬆查詢：

```sql
-- 只查詢 Instagram 的貼文
SELECT * FROM social_posts WHERE platform = 'instagram';

-- 查詢所有平台的某個使用者
SELECT * FROM social_users WHERE username = 'example';
```

---

## ⚠️ 注意事項

### 法律與道德

- ⚠️ **遵守法律**: 確保你有權限抓取目標使用者的資料
- ⚠️ **尊重隱私**: 不要抓取私人帳號
- ⚠️ **商業用途**: 商業使用前請確認各平台的服務條款
- ⚠️ **資料保護**: 妥善保管抓取的資料，避免洩漏

### 技術限制

- 📌 Apify 有 API 使用額度限制（依方案而定）
- 📌 各平台可能更改 API 結構，導致爬蟲失效
- 📌 私人帳號無法抓取
- 📌 限時動態僅保留 24 小時

### 效能建議

- 💡 單次抓取建議不超過 100 筆貼文
- 💡 批次處理時設定適當延遲（5-15 秒）
- 💡 定期清理舊的媒體檔案
- 💡 為常用欄位建立資料庫索引

---

## 📊 專案統計

- **支援平台**: 4 個（Instagram, Facebook, Twitter, Threads）
- **程式碼行數**: ~3000 行
- **核心類別**: 10+ 個
- **資料表**: 7 個
- **範例程式**: 6 個

---

## 📝 更新紀錄

### v2.3.0 (2025-10) - 多進程與異步並發功能 🚀

- ✅ 新增多進程平行處理模式（`--multiprocess`）
- ✅ 真正的多核心並行，適合處理 Apify Actor 阻塞情況
- ✅ `--num-processes` 參數控制進程數量（預設使用 CPU 核心數）
- ✅ 新增異步並發收集模式（`--async`）
- ✅ `--concurrent-limit` 參數控制並發數量
- ✅ 支援 `daily` 和 `batch` 模式
- ✅ 使用 Python `multiprocessing` 實現真正平行處理

### v2.2.0 (2024-10) - 帳號配置檔功能

- ✅ 新增帳號配置檔支援 (`accounts.txt`)
- ✅ 新增每日收集模式 (`--mode daily`)
- ✅ 可直接從配置檔讀取帳號清單，無需手動指定
- ✅ 完美支援定期排程執行
- ✅ 新增 `config/accounts_loader.py` 模組
- ✅ 提供 `accounts.example.txt` 範本檔案
- ✅ 更新 README 增加排程設定詳細說明

### v2.1.0 (2024-10) - 欄位轉換功能

- ✅ 新增欄位值轉換機制
- ✅ 可在 config 中自訂義轉換規則
- ✅ 內建 3 種常用轉換器（媒體類型、布林值、數字格式化）
- ✅ 自動在資料儲存前套用轉換
- ✅ 轉換失敗時自動降級保留原值

### v2.0.0 (2024-10) - 通用架構重構

- ✅ 重新設計為通用多平台架構
- ✅ 新增 Facebook、Twitter、Threads 支援
- ✅ 統一資料模型和資料庫結構
- ✅ 工廠模式自動選擇收集器
- ✅ 易於擴展新平台

### v1.2.0 (2024-10) - Instagram 專用版本

- ✅ Instagram 專用收集器
- ✅ 支援貼文、限時動態、輪播
- ✅ 媒體檔案下載

---

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

---

## 📄 授權

本專案僅供學習和研究使用。使用前請確保遵守各社群平台和 Apify 的服務條款。

---

## 📊 日誌與監控

### 日誌系統

本專案內建完整的日誌記錄功能，所有執行過程都會自動記錄到檔案和 console。

**日誌檔案位置**: `logs/MediaCollect_YYYYMMDD.log`

**查看即時日誌**:
```bash
tail -f logs/MediaCollect_20251019.log
```

**搜尋錯誤記錄**:
```bash
grep "ERROR" logs/MediaCollect_20251019.log
```

### 收集歷史記錄

每次收集任務都會記錄到 `collection_history` 資料表，包含：
- 平台與使用者名稱
- 成功或失敗狀態
- 收集的貼文數與限時動態數
- 執行時長（秒）
- 錯誤訊息（如果失敗）

**使用查詢工具**:
```bash
python query_collection_history.py
```

提供以下查詢功能：
1. 最近收集記錄
2. 失敗記錄
3. 平台成功率統計
4. 效能統計
5. 特定使用者歷史
6. 今日收集摘要

**SQL 查詢範例**:

```sql
-- 查看今日收集記錄
SELECT * FROM collection_history 
WHERE DATE(started_at) = CURDATE()
ORDER BY started_at DESC;

-- 統計平台成功率
SELECT 
    platform,
    COUNT(*) as total,
    SUM(success) as success_count,
    ROUND(SUM(success) / COUNT(*) * 100, 2) as success_rate
FROM collection_history 
GROUP BY platform;

-- 查看平均執行時長
SELECT 
    platform,
    AVG(duration_seconds) as avg_duration,
    AVG(post_count) as avg_posts
FROM collection_history 
WHERE success = 1
GROUP BY platform;
```

詳細說明請參閱 [LOG_FEATURE.md](LOG_FEATURE.md)

---

## 📷 Instagram Hashtag 收集器使用指南

> 🎯 追蹤主題標籤，發掘熱門話題 | 📅 最後更新: 2025-10-21

### 🌟 功能說明

Instagram Hashtag 收集器現已支援**單個或多個 hashtag** 的收集功能。Apify 的 Instagram Hashtag Scraper 本身就支援複數 hashtag，因此您可以在一次請求中收集多個 hashtag 的貼文。

`InstagramHashtagCollector` 是專門用於收集特定 hashtag 貼文的收集器，與 `InstagramCollector` 的主要區別：

| 收集器 | 用途 | 追蹤對象 | 使用場景 |
|--------|------|----------|----------|
| **InstagramCollector** | 使用者追蹤 | 特定使用者的貼文 | 追蹤品牌、KOL、競爭對手 |
| **InstagramHashtagCollector** | 主題追蹤 | 特定標籤的貼文 | 追蹤話題、趨勢、活動、產品關鍵字 |

### 🚀 使用方式

#### 1. 命令行模式

##### 單個 Hashtag
```bash
python main.py --mode hashtag --platform instagram --hashtag timelessbruno
```

##### 多個 Hashtag（用逗號分隔）
```bash
# 基本用法
python main.py --mode hashtag --platform instagram --hashtag "timelessbruno,travel,food"

# 指定結果類型和數量
python main.py --mode hashtag --platform instagram --hashtag "timelessbruno,travel,food" --results-type reels --results-limit 100
```

**注意事項：**
- 多個 hashtag 用逗號分隔
- 建議用引號包圍整個 hashtag 字串（避免命令行解析問題）
- 可以包含或不包含 # 符號，程式會自動處理
- `--results-limit` 是指**每個 hashtag** 的結果數量限制

#### 2. 互動式模式

```bash
python main.py --mode interactive
```

然後選擇：
1. 選擇模式 `2` (Hashtag 收集模式)
2. 選擇平台（例如 Instagram）
3. 輸入 hashtag（支援單個或多個，用逗號分隔）
   - 單個範例：`timelessbruno`
   - 多個範例：`timelessbruno,travel,food`
4. 選擇結果類型（Posts 或 Reels）
5. 輸入結果數量限制

#### 3. Python 程式碼調用

##### 單個 Hashtag
```python
from platforms.instagram_collector import InstagramHashtagCollector
from config.platform_config import APIFY_TOKEN

# 初始化收集器
collector = InstagramHashtagCollector(
    hashtag="timelessbruno",
    api_token=APIFY_TOKEN,
    results_type="posts",    # "posts" 或 "reels"
    results_limit=50
)

# 收集貼文
result = collector.collect_hashtag()

# 查看結果
print(f"✓ 成功收集 #{result.hashtag} 的 {len(result.posts)} 則貼文")
```

##### 多個 Hashtag（逗號分隔字串）
```python
from main import SocialMediaCrawler

crawler = SocialMediaCrawler()
result = crawler.collect_hashtag(
    platform="instagram",
    hashtag="timelessbruno,travel,food",
    results_type="posts",
    results_limit=50
)
```

##### 多個 Hashtag（列表）
```python
result = crawler.collect_hashtag(
    platform="instagram",
    hashtag=["timelessbruno", "travel", "food"],
    results_type="posts",
    results_limit=50
)
```

#### 4. 儲存到資料庫

```python
from core.database_manager import create_database_manager_from_config
from config.platform_config import SQL_CONFIGURE_PATH

# 收集資料
collector = InstagramHashtagCollector(
    hashtag="python",
    api_token=APIFY_TOKEN
)
result = collector.collect_hashtag()

# 儲存到資料庫
if result.success:
    with create_database_manager_from_config(SQL_CONFIGURE_PATH) as db:
        db.save_hashtag_collection_result(result)
    print(f"✓ 已儲存 {len(result.posts)} 則貼文到資料庫")
```

### 🔧 技術細節

#### 支援的輸入格式

程式會自動識別並處理以下三種格式：

1. **單個 hashtag（字串）**
   ```python
   hashtag = "timelessbruno"
   ```

2. **多個 hashtag（逗號分隔字串）**
   ```python
   hashtag = "timelessbruno,travel,food"
   ```

3. **多個 hashtag（列表）**
   ```python
   hashtag = ["timelessbruno", "travel", "food"]
   ```

#### 自動處理

程式會自動處理：
- 移除 # 符號（如果有）
- 去除空白字元
- 統一轉換為列表格式傳給 Apify Actor

#### Apify Actor 參數

最終傳給 Apify Instagram Hashtag Scraper 的參數格式：
```json
{
  "hashtags": ["timelessbruno", "travel", "food"],
  "resultsType": "posts",
  "resultsLimit": 50
}
```

### 📊 資料結構

#### HashtagPost 物件欄位

```python
{
    'platform': 'instagram',
    'post_id': 'CX1234567',
    'content_type': 'post',  # 或 'reel'
    'author_id': '123456789',
    'author_username': 'user123',
    'author_display_name': 'User Name',
    'text': '貼文內容...',
    'hashtag': 'travel',  # 收集時使用的 hashtag
    'hashtags': ['travel', 'photography', 'nature'],  # 貼文中的所有標籤
    'mentions': ['user1', 'user2'],  # 提及的使用者
    'like_count': 1234,
    'comment_count': 56,
    'view_count': 5678,
    'share_count': 12,
    'comments_disabled': False,
    'is_promoted': False,  # 是否為廣告貼文
    'location_name': 'Tokyo, Japan',
    'created_at': datetime(2025, 10, 21, 12, 0, 0),
    'post_url': 'https://www.instagram.com/p/CX1234567/',
    'media_items': [...]  # MediaItem 物件列表
}
```

### 📝 範例

#### 收集旅遊相關的多個 hashtag
```bash
python main.py --mode hashtag --platform instagram --hashtag "travel,travelgram,wanderlust,vacation" --results-limit 100
```

#### 收集美食相關的 Reels
```bash
python main.py --mode hashtag --platform instagram --hashtag "food,foodie,foodporn,instafood" --results-type reels --results-limit 50
```

### 🎯 使用場景範例

#### 場景 1: 品牌監控

```python
# 追蹤品牌相關話題
brand_hashtags = ['nike', 'justdoit', 'nikeshoes']

for tag in brand_hashtags:
    collector = InstagramHashtagCollector(tag, APIFY_TOKEN, results_limit=100)
    result = collector.collect_hashtag()
    
    print(f"\n#{tag}: {len(result.posts)} 則貼文")
    
    # 找出互動最高的貼文
    top_posts = sorted(result.posts, key=lambda p: p.like_count, reverse=True)[:5]
    for post in top_posts:
        print(f"  - @{post.author_username}: ❤️ {post.like_count:,}")
```

#### 場景 2: 趨勢分析

```python
# 收集熱門話題
trending_tag = "ai"
collector = InstagramHashtagCollector(
    hashtag=trending_tag,
    api_token=APIFY_TOKEN,
    results_limit=200
)
result = collector.collect_hashtag()

# 分析發文時間分布
from collections import Counter
import datetime

hour_counts = Counter()
for post in result.posts:
    if post.created_at:
        hour_counts[post.created_at.hour] += 1

print("發文時間分布:")
for hour in sorted(hour_counts.keys()):
    print(f"{hour:02d}:00 - {hour_counts[hour]} 則貼文 {'█' * hour_counts[hour]}")
```

#### 場景 3: KOL 發掘

```python
# 找出特定主題的活躍創作者
collector = InstagramHashtagCollector("foodphotography", APIFY_TOKEN, results_limit=100)
result = collector.collect_hashtag()

# 統計創作者
from collections import defaultdict
creators = defaultdict(list)

for post in result.posts:
    creators[post.author_username].append(post)

# 找出發文最多的創作者
top_creators = sorted(creators.items(), key=lambda x: len(x[1]), reverse=True)[:10]

print("\n最活躍創作者:")
for username, posts in top_creators:
    avg_likes = sum(p.like_count for p in posts) / len(posts)
    print(f"@{username}: {len(posts)} 則貼文 | 平均互動: {avg_likes:,.0f}")
```

### ⚙️ 參數說明

#### 初始化參數

| 參數 | 類型 | 說明 | 預設值 |
|------|------|------|--------|
| `hashtag` | str/list | 要追蹤的 hashtag（可含或不含 #，支援單個或多個） | 必填 |
| `api_token` | str | Apify API Token | 必填 |
| `results_type` | str | 結果類型：`"posts"` 或 `"reels"` | `"posts"` |
| `results_limit` | int | 抓取數量限制 | `50` |

#### collect_hashtag() 方法參數

```python
result = collector.collect_hashtag(
    hashtag=None,         # 可覆蓋初始化的 hashtag
    results_type=None,    # 可覆蓋初始化的 results_type
    results_limit=None    # 可覆蓋初始化的 results_limit
)
```

### ❓ 常見問題

#### Q1: InstagramHashtagCollector 和 InstagramCollector 有什麼區別？

**A:** 
- `InstagramCollector`: 追蹤**特定使用者**的所有貼文
- `InstagramHashtagCollector`: 追蹤**特定主題標籤**的所有貼文（來自不同使用者）

#### Q2: 每個 hashtag 會收集多少貼文？

**A:** `--results-limit` 參數指定的是 Apify Actor 的結果總數限制，實際上會在所有 hashtag 之間分配。具體分配方式由 Apify 決定。

#### Q3: 可以混合使用帶 # 和不帶 # 的 hashtag 嗎？

**A:** 可以，程式會自動處理。例如 `#travel,food,#photo` 會被處理為 `travel,food,photo`。

#### Q4: 有數量限制嗎？

**A:** 理論上沒有限制，但建議一次不要超過 10 個 hashtag，以確保 Apify Actor 的穩定性和效能。

#### Q5: results_type 選 "posts" 還是 "reels"？

**A:**
- `"posts"`: 一般貼文（圖片、影片、輪播）
- `"reels"`: 只收集 Reels 短影片

如果不確定，建議使用 `"posts"`（包含所有類型）。

#### Q6: 收集的貼文會重複嗎？

**A:** 資料庫使用 `(platform, post_id)` 作為唯一鍵，重複的貼文會自動更新而不會重複儲存。

#### Q7: 可以過濾時間範圍嗎？

**A:** Apify 的 hashtag scraper 目前不支援時間過濾。建議收集後再用程式碼過濾：

```python
result = collector.collect_hashtag()

# 只保留最近 7 天的貼文
from datetime import datetime, timedelta
seven_days_ago = datetime.now() - timedelta(days=7)

recent_posts = [
    post for post in result.posts 
    if post.created_at and post.created_at >= seven_days_ago
]
```

#### Q8: 如何儲存到資料庫？

**A:** hashtag 貼文會儲存到 `social_hashtag_posts` 資料表：

```python
with create_database_manager_from_config(SQL_CONFIGURE_PATH) as db:
    db.save_hashtag_collection_result(result)
```

#### Q9: 消耗多少 Apify 配額？

**A:** 
- 50 則貼文：約 30-60 秒
- 100 則貼文：約 60-120 秒

Free tier 用戶建議設定 `results_limit=50`。

#### Q10: 支援其他平台嗎？

**A:** 目前只有 Instagram 支援 hashtag 收集功能。其他平台的支援取決於對應的 Apify Actor 是否提供相關功能。

### 💾 資料庫儲存

收集到的貼文會儲存到 `social_hashtag_posts` 資料表中，其中 `hashtag` 欄位會以逗號分隔的形式儲存所有查詢的 hashtag：

```
hashtag: "timelessbruno,travel,food"
```

這樣可以清楚知道該筆貼文是透過哪些 hashtag 查詢得到的。

### 💡 最佳實踐

#### 1. 批次收集多個 hashtag

```python
hashtags = ['travel', 'photography', 'nature', 'adventure']

for tag in hashtags:
    print(f"\n收集 #{tag}...")
    collector = InstagramHashtagCollector(tag, APIFY_TOKEN, results_limit=50)
    result = collector.collect_hashtag()
    
    if result.success:
        # 儲存到資料庫
        with create_database_manager_from_config(SQL_CONFIGURE_PATH) as db:
            db.save_hashtag_collection_result(result)
```

#### 2. 定期排程收集

將以下內容加入 crontab（每天早上 6 點執行）：

```bash
0 6 * * * cd /path/to/MediaCollect && python scripts/collect_hashtags.py
```

`scripts/collect_hashtags.py`:
```python
from platforms.instagram_collector import InstagramHashtagCollector
from config.platform_config import APIFY_TOKEN

# 定義要追蹤的 hashtag
HASHTAGS_TO_TRACK = ['ai', 'machinelearning', 'python', 'programming']

for tag in HASHTAGS_TO_TRACK:
    collector = InstagramHashtagCollector(tag, APIFY_TOKEN, results_limit=50)
    result = collector.collect_hashtag()
    
    if result.success:
        print(f"✓ #{tag}: {len(result.posts)} 則貼文")
```

#### 3. 分析競爭對手的 hashtag 策略

```python
# 先用 InstagramCollector 收集競爭對手的貼文
from platforms.instagram_collector import InstagramCollector

competitor_collector = InstagramCollector("competitor_username", APIFY_TOKEN)
competitor_posts = competitor_collector.fetch_posts(limit=50)

# 提取他們常用的 hashtag
from collections import Counter
hashtag_counter = Counter()

for post in competitor_posts:
    hashtag_counter.update(post.hashtags)

# 追蹤前 10 個熱門 hashtag
top_hashtags = [tag for tag, count in hashtag_counter.most_common(10)]

for tag in top_hashtags:
    collector = InstagramHashtagCollector(tag, APIFY_TOKEN, results_limit=30)
    result = collector.collect_hashtag()
    print(f"#{tag}: {len(result.posts)} 則貼文")
```

### 📈 版本更新

**v1.1 (2025-10-21) - 多 Hashtag 支援**

新增功能：
- ✅ 支援一次收集多個 hashtag（逗號分隔或列表）
- ✅ 自動處理 # 符號和空白字元
- ✅ 命令行模式支援多 hashtag
- ✅ 互動式模式支援多 hashtag
- ✅ 資料庫儲存時記錄所有查詢的 hashtag

**v1.0 (2025-10-21) - 正式發布**

功能特色：
- ✅ 獨立的 Hashtag 收集器類別
- ✅ 繼承 InstagramCollector，重用媒體解析邏輯
- ✅ 支援 posts 和 reels 兩種類型
- ✅ 完整的貼文資料（作者、互動數、標籤、提及等）
- ✅ 支援儲存到資料庫
- ✅ 詳細的錯誤處理和日誌記錄

設計理念：
- 🎯 **職責分離**: 使用者追蹤 vs 主題追蹤
- 🎯 **繼承複用**: 重用父類別的媒體解析、標籤提取等功能
- 🎯 **獨立功能**: hashtag 相關函數不污染 InstagramCollector

---

## 📘 Facebook 收集器完整使用手冊

> 🎯 適合 Free User 使用 | 📅 最後更新: 2025-10-20

### 🚀 快速開始

#### 1. 基本設定

確保您的 `.env` 檔案包含 Apify Token：
```env
APIFY_TOKEN_1=your_apify_token_here
```

#### 2. 啟用 Facebook 收集

編輯 `config/platform_config.py`：
```python
PLATFORM_SETTINGS = {
    'facebook': {
        'enabled': True,  # 改為 True
        'post_limit': 10,
        'photo_limit': 10,
        'download_media': True,
    }
}
```

#### 3. 基本使用範例
```python
from platforms.facebook_collector import FacebookCollector
from config.platform_config import APIFY_TOKEN

# 初始化
collector = FacebookCollector(
    username="nasa",
    api_token=APIFY_TOKEN
)

# 抓取專頁資料
user = collector.fetch_user_profile()
print(f"專頁: {user.display_name} (粉絲: {user.follower_count:,})")

# 抓取貼文
posts = collector.fetch_posts(limit=5)
print(f"抓取了 {len(posts)} 則貼文")

# 抓取照片
photos = collector.fetch_photos(limit=5)
print(f"抓取了 {len(photos)} 張照片")
```

#### 4. 執行測試
```bash
python examples/test_facebook_collector.py
```

### 📦 三個 Apify Actors

| Actor | 功能 | Free User | 特色 |
|-------|------|-----------|------|
| `facebook-pages-scraper` | 專頁基本資料 | ✅ | 完整專頁資訊、聯絡方式 |
| `facebook-posts-scraper` | 貼文內容 | ✅ | 文字、圖片、影片、互動數據 |
| `facebook-photos-scraper` | 照片專輯 | ✅ | 高畫質照片 + OCR 文字識別 |

### ✨ 功能特色

#### 專頁資料收集
- ✅ 完整專頁資訊（名稱、描述、分類）
- ✅ 粉絲數、追蹤中數量
- ✅ 聯絡資訊（Email、電話、地址、網站）
- ✅ 認證狀態智慧判斷
- ✅ 頭像、封面圖 URL

#### 貼文收集
- ✅ 文字內容
- ✅ 圖片、影片、縮圖
- ✅ 互動數據（讚、留言、分享）
- ✅ 發布時間（支援 3 種格式）
- ✅ 貼文連結

#### 照片收集
- ✅ 高解析度圖片
- ✅ OCR 文字識別
- ✅ 照片專輯完整抓取

### 🔧 技術改進

#### 1. 多欄位 Fallback
```python
# 自動處理不同 API 回傳格式
user_id = raw.get('pageId') or raw.get('facebookId', '')
post_url = raw.get('url') or raw.get('topLevelUrl')
```

#### 2. 智慧認證判斷
```python
def _check_verified(self, raw):
    # 檢查多個可能的認證欄位
    if raw.get('verified'):
        return True
    if raw.get('CONFIRMED_OWNER_LABEL'):
        return True
    return False
```

#### 3. 多格式時間解析
支援三種時間格式：
- Unix timestamp (毫秒)
- Facebook 格式: "Thursday, 6 April 2023 at 07:10"
- ISO 8601: "2023-04-06T07:10:00Z"

#### 4. 媒體去重處理
```python
# 避免重複加入相同 URL 的媒體
if link_url and link_url not in [m.url for m in media_items]:
    media_items.append(MediaItem(...))
```

### 📊 API 輸入格式

#### 專頁資料
```python
run_input = {
    "startUrls": [{"url": "https://www.facebook.com/nasa"}]
}
```

#### 貼文收集
```python
run_input = {
    "startUrls": [{"url": "https://www.facebook.com/nasa"}],
    "resultsLimit": 10,
    "proxy": {
        "apifyProxyGroups": ["RESIDENTIAL"]
    },
    "maxRequestRetries": 10
}
```

#### 照片收集
```python
run_input = {
    "startUrls": [{"url": "https://www.facebook.com/nasa"}],
    "resultsLimit": 10,
    "proxy": {
        "apifyProxyGroups": ["RESIDENTIAL"]
    },
    "maxRequestRetries": 10
}
```

### 📝 輸出資料結構

#### 專頁資料
```python
{
    'platform': 'facebook',
    'user_id': '100064975200317',
    'username': 'nasa',
    'display_name': 'NASA',
    'is_verified': True,
    'follower_count': 10505363,
    'following_count': 26,
    'category': 'Science Website',
    'description': 'Explore and learn more...',
    'external_url': 'https://science.nasa.gov/earth/',
    'email': 'contact@nasa.gov',
    'phone': '+1-xxx-xxx-xxxx',
    'location': 'Washington, DC'
}
```

#### 貼文資料
```python
{
    'post_id': '10153102379324999',
    'text': 'Vice President Kamala Harris...',
    'like_count': 9,
    'comment_count': 17,
    'share_count': 5,
    'created_at': datetime(2023, 4, 6, 7, 10),
    'post_url': 'https://www.facebook.com/...',
    'media_items': [...]
}
```

### ❓ 常見問題

#### Q1: Free User 可以使用嗎？
**A:** 可以！建議設定：
- `post_limit`: 5-10
- `photo_limit`: 5-10

#### Q2: 為什麼需要三個 Actors？
**A:** 不同 Actor 專門處理不同類型的資料，資料更完整準確。

#### Q3: 會消耗多少配額？
**A:** 
- 專頁資料: ~10-20 秒
- 貼文 (10則): ~30-60 秒
- 照片 (10張): ~30-60 秒

Free tier 用戶建議每天不超過 20-30 次執行。

#### Q4: 可以抓取私人專頁嗎？
**A:** 不行，僅支援公開粉絲專頁。

#### Q5: 可以抓取限時動態嗎？
**A:** 目前不支援，Facebook 限時動態需要登入權限。

#### Q6: 照片資料為什麼沒有互動數？
**A:** `facebook-photos-scraper` 專注於照片本身。如需互動數據，請使用 `fetch_posts()`。

#### Q7: 可以批次抓取多個專頁嗎？
**A:** 可以！在 `accounts.txt` 中新增：
```
facebook,nasa
facebook,nytimes
facebook,natgeo
```
然後執行 `python main.py`

#### Q8: 資料存在哪裡？
**A:** 
- **資料庫**: unified 資料庫（若已設定）
- **媒體**: `media/facebook/專頁名稱/`
- **日誌**: `logs/Collector_YYYYMMDD.log`

#### Q9: 抓取失敗怎麼辦？
**A:** 依序檢查：
1. 確認專頁名稱正確
2. 確認專頁為公開專頁
3. 檢查 Apify 配額
4. 查看日誌檔案
5. 查看 Apify Dashboard

#### Q10: 沒有返回資料
**A:** 可能原因：
- 專頁沒有足夠的貼文/照片
- 遇到速率限制，等待後重試
- 減少 `limit` 數量重試

### 🎯 推薦測試專頁

| 專頁名稱 | Username | 類型 | 特色 |
|----------|----------|------|------|
| NASA | `nasa` | 科技 | 高品質圖片和影片 |
| The New York Times | `nytimes` | 新聞 | 大量文字貼文 |
| National Geographic | `natgeo` | 攝影 | 精美照片 |
| NASA Earth | `nasaearth` | 科學 | 地球科學圖片 |
| Humans of New York | `humansofnewyork` | 人文 | 故事性貼文 |

### 📈 版本更新

**v2.0 (2025-10-20) - 重大更新**

新增功能：
- ✅ 照片收集功能 (`facebook-photos-scraper`)
- ✅ OCR 文字識別
- ✅ 聯絡資訊欄位 (Email, Phone, Location)
- ✅ 智慧認證判斷
- ✅ 多格式時間解析
- ✅ 媒體去重處理
- ✅ 重試機制 (10次)
- ✅ RESIDENTIAL 代理支援

資料完整度提升：
- 專頁資料: 8 個欄位 → 15 個欄位 (+87.5%)
- 貼文資料: 新增作者名稱、多 URL fallback
- 媒體解析: 支援縮圖、連結圖片 + 去重

### 📚 相關文件

- `platforms/facebook_collector.py` - 收集器實作
- `examples/test_facebook_collector.py` - 測試範例
- `config/platform_config.py` - 設定檔

---

## 📧 聯絡方式

如有問題或建議，歡迎透過 Issue 系統聯繫。

---

**⭐ 如果這個專案對你有幫助，請給個星星！**


