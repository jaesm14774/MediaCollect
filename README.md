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

### 🏗️ 架構特色

- 🔧 **抽象基類設計**: 所有平台共用統一介面
- 🔧 **工廠模式**: 自動選擇對應平台的收集器
- 🔧 **通用資料模型**: 跨平台統一的資料結構
- 🔧 **易於擴展**: 新增平台只需實作 4 個核心方法
- 🔧 **模組化設計**: 核心、平台、工具完全分離

---

## 🌍 支援平台

| 平台 | 狀態 | 支援功能 | Apify Actor |
|------|------|----------|-------------|
| **Instagram** | ✅ 完整支援 | 使用者資訊、貼文、限時動態、輪播 | apify/instagram-profile-scraper<br>apify/instagram-post-scraper<br>igview-owner/instagram-story-viewer |
| **Facebook** | ✅ 支援 | 粉絲專頁資訊、貼文 | apify/facebook-pages-scraper<br>apify/facebook-posts-scraper |
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
│   ├── media_downloader.py       # 媒體下載工具
│   ├── get_sql_connection.py     # 資料庫連接
│   └── discord_notify.py         # Discord 通知
│
├── config/                        # 設定檔
│   ├── config.py                 # 通用設定
│   └── platform_config.py        # 各平台設定
│
├── main.py                        # 主程式入口
├── example_unified.py             # 使用範例
├── init_unified_database.sql     # 資料庫初始化腳本
└── requirements.txt               # 依賴套件
```

### 核心類別關係圖

```
BaseSocialMediaCollector (抽象基類)
    ↓
ApifyBasedCollector (Apify 基類)
    ↓
    ├── InstagramCollector
    ├── FacebookCollector
    ├── TwitterCollector
    └── ThreadsCollector

CollectorFactory (工廠)
    └── 自動建立對應平台的收集器

DatabaseManager (資料庫管理)
    └── 統一儲存所有平台資料
```

---

## 🚀 快速開始

### 0. 每日排程收集（推薦）

這是最簡單的使用方式，適合定期排程執行：

```bash
# 1. 複製帳號配置檔範本
cp accounts.example.txt accounts.txt

# 2. 編輯 accounts.txt，填入要收集的帳號
# [instagram]
# nasa
# natgeo
# 
# [twitter]
# twitter
# elonmusk

# 3. 直接執行每日收集
python main.py --mode daily
```

**這樣就完成了！** 系統會自動收集 `accounts.txt` 中設定的所有帳號。

### 1. 基本使用範例

```python
from core.factory import CollectorFactory, register_all_collectors
from config.platform_config import APIFY_TOKEN

# 註冊所有平台收集器
register_all_collectors()

# 建立 Instagram 收集器
collector = CollectorFactory.create_collector(
    platform='instagram',
    username='instagram',
    api_token=APIFY_TOKEN
)

# 收集資料
result = collector.collect_all(post_limit=10)
print(result)
```

### 2. 多平台收集

```python
# 支援的平台
platforms = ['instagram', 'facebook', 'twitter', 'threads']

for platform in platforms:
    collector = CollectorFactory.create_collector(
        platform=platform,
        username='example_user',
        api_token=APIFY_TOKEN
    )
    result = collector.collect_all(post_limit=5)
    print(f"{platform}: {result.success}")
```

### 3. 互動式測試

```bash
python main.py --mode interactive
```

### 4. 批次收集

```bash
# 每日收集（從 accounts.txt 讀取帳號） - 推薦用於排程
python main.py --mode daily

# 使用自訂帳號檔
python main.py --mode daily --accounts-file my_accounts.txt

# 從資料庫讀取使用者列表並批次收集
python main.py --mode batch --platform instagram

# 收集所有平台（從資料庫讀取）
python main.py --mode all
```

---

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
    # ... 其他平台
}
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
```

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

# 批次處理（從資料庫讀取）
python main.py --mode batch --platform twitter

# 所有平台批次處理（從資料庫讀取）
python main.py --mode all
```

### 方式 3: 使用範例程式

```bash
python example_unified.py
```

會顯示互動式選單，讓你選擇不同的範例。

### 方式 4: 在程式碼中使用

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
   - 起始於: `C:\Users\jaesm14774\Desktop\self_project\MediaCollect`

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

## 📧 聯絡方式

如有問題或建議，歡迎透過 Issue 系統聯繫。

---

**⭐ 如果這個專案對你有幫助，請給個星星！**


