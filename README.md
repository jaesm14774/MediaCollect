# MediaCollect: Multi-Platform Social Media Data Collection System

**A unified system for collecting social media data from Instagram, Facebook, Twitter(X), and Threads using the Apify API.**

This system automatically fetches user profiles, posts, stories, and media files, then stores everything in a MySQL database with a standardized schema across all platforms.

---

## Table of Contents

- [What This System Does](#what-this-system-does)
- [Quick Start Guide](#quick-start-guide)
- [Installation](#installation)
- [Configuration](#configuration)
- [How to Use](#how-to-use)
- [Supported Platforms](#supported-platforms)
- [Key Features](#key-features)
- [Database Schema](#database-schema)
- [Adding New Platforms](#adding-new-platforms)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)
- [Advanced Features](#advanced-features)
- [Important Notes](#important-notes)

---

## What This System Does

**MediaCollect collects social media data and saves it to your database.**

The system can:
- **Fetch user profiles**: username, follower count, verified status, bio, profile picture, etc.
- **Collect posts**: text, images, videos, likes, comments, shares, timestamps
- **Download media files**: high-resolution images and videos saved locally
- **Track stories**: 24-hour stories (on platforms that support them)
- **Store everything in MySQL**: unified database schema for all platforms
- **Run on schedule**: automated daily collection from account lists
- **Process in parallel**: multi-core processing for faster data collection

---

## Quick Start Guide

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set up your environment variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your Apify API token:

```env
APIFY_TOKEN_1=apify_api_your_token_here
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=crawler
MEDIA_FOLDER_PATH=E:/your_path/SocialMedia/
```

**How to get an Apify token:**
1. Sign up at [apify.com](https://apify.com/)
2. Go to Settings → Integrations
3. Copy your API token

### Step 3: Initialize the database

```bash
mysql -u your_user -p crawler < init_unified_database.sql
```

### Step 4: Create an account list

Create `accounts.txt` with the accounts you want to monitor:

```ini
[instagram]
nasa
natgeo

[twitter]
elonmusk
```

### Step 5: Run your first collection

```bash
python main.py --mode daily
```

**That's it!** The system will collect data from all accounts in your list.

---

## Installation

### System Requirements

- **Python 3.8 or higher**
- **MySQL 5.7+ or MariaDB 10.3+**
- **Apify account** (free tier works fine)

### Install Python packages

```bash
pip install -r requirements.txt
```

Required packages:
```
pandas>=1.5.0
numpy>=1.23.0
requests>=2.28.0
apify-client>=1.3.0
pymysql>=1.0.2
sqlalchemy>=1.4.0
python-dotenv>=0.21.0
```

### Set up the database

Run the SQL initialization script:

```bash
# Using command line
mysql -u your_user -p crawler < init_unified_database.sql

# Or in MySQL client
source init_unified_database.sql;
```

This creates these tables:
- `social_users` - User profiles
- `social_posts` - Posts and tweets
- `social_stories` - Stories (24-hour content)
- `social_hashtag_posts` - Posts from hashtag searches
- `collection_history` - Tracking collection runs
- `platform_config` - Platform settings

---

## Configuration

### Environment Variables (.env file)

**The .env file stores your sensitive configuration.**

Create it from the example:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Apify API Tokens (you can add multiple, system will randomly select one)
APIFY_TOKEN_1=apify_api_your_token_1
APIFY_TOKEN_2=apify_api_your_token_2
APIFY_TOKEN_3=apify_api_your_token_3

# Where to save downloaded media files
MEDIA_FOLDER_PATH=E:/your_path/SocialMedia/

# Database connection
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=crawler

# Discord notifications (optional)
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

### Account List (accounts.txt)

**The accounts.txt file tells the system which accounts to collect.**

Format:
```ini
# Instagram accounts
[instagram]
nasa
natgeo
instagram

# Facebook pages
[facebook]
facebook
microsoft

# Twitter accounts
[twitter]
twitter
elonmusk

# Threads accounts
[threads]
zuck
instagram
```

Rules:
- Use `[platform_name]` to mark sections
- One account per line (no @ symbol needed)
- Lines starting with `#` are comments
- Empty lines are ignored
- Platform names are case-insensitive

**How to organize accounts:**

Use comments to categorize:
```ini
[instagram]
# Official accounts
instagram
facebook

# Science
nasa
natgeo
sciencechannel

# Tech companies
apple
google
microsoft
```

**How to disable accounts temporarily:**

Add `#` in front:
```ini
[instagram]
nasa
# natgeo  # Temporarily disabled
instagram
```

### Platform Settings (config/platform_config.py)

**Platform settings control how much data to collect from each platform.**

Edit `config/platform_config.py`:

```python
PLATFORM_SETTINGS = {
    'instagram': {
        'enabled': True,           # Enable/disable this platform
        'post_limit': 50,          # How many posts to collect
        'story_limit': None,       # How many stories (None = all)
        'download_media': True,    # Download images/videos?
    },
    'facebook': {
        'enabled': True,
        'post_limit': 10,
        'photo_limit': 10,
        'download_media': True,
        # Time filtering (Facebook only)
        'posts_newer_than': None,  # e.g., "7 days" or "2024-01-01"
        'posts_older_than': None,  # e.g., "2024-12-31"
        'caption_text': False,     # Extract video captions?
    },
    'twitter': {
        'enabled': True,
        'post_limit': 50,
        'download_media': True,
    },
    'threads': {
        'enabled': True,
        'post_limit': 50,
        'download_media': True,
    },
}
```

**Facebook time filtering examples:**

```python
# Collect only last 7 days
'posts_newer_than': "7 days"

# Collect specific date range
'posts_newer_than': "2024-01-01"
'posts_older_than': "2024-12-31"

# Collect last month with video captions
'posts_newer_than': "1 month"
'caption_text': True
```

Supported time formats:
- **Relative**: `"1 day"`, `"2 months"`, `"3 years"`, `"1 hour"`, `"30 minutes"`
- **Absolute date**: `"2024-01-01"` (YYYY-MM-DD)
- **Full timestamp**: `"2025-09-23T10:02:01"` (ISO 8601)

---

## How to Use

### Method 1: Daily Scheduled Collection (Recommended)

**This is the simplest way to use the system.**

Collect from all accounts in `accounts.txt`:

```bash
python main.py --mode daily
```

Use a custom account file:

```bash
python main.py --mode daily --accounts-file my_accounts.txt
```

**Enable parallel processing** (recommended for faster collection):

```bash
# Multi-process mode (true parallel processing, best for Apify actors)
python main.py --mode daily --multiprocess --num-processes 4

# Async mode (concurrent I/O, good for non-blocking tasks)
python main.py --mode daily --async --concurrent-limit 3
```

**Multi-process vs Async:**
- **`--multiprocess`**: True parallel processing using multiple CPU cores. Best for handling Apify Actor blocking/waiting situations. Each user runs in a separate process.
- **`--async`**: Concurrent I/O using coroutines. Good for I/O-heavy tasks that don't block. Shares a single process.

**Set up automated scheduling:**

Windows (Task Scheduler):
```powershell
# Run daily at 6 AM
schtasks /create /tn "MediaCollect_Daily" /tr "python C:\path\to\main.py --mode daily" /sc daily /st 06:00

# Or use the daily.bat script (recommended)
# Make sure daily.bat uses "start /wait" to prevent duplicate execution
```

**重要：防止重複執行**
- 系統已內建文件鎖機制，自動防止 `daily`、`batch`、`all` 模式的重複執行
- 如果檢測到另一個實例正在運行，會自動退出並顯示錯誤訊息
- 鎖文件位置：`media_collect.lock`（在腳本目錄）
- 使用 `daily.bat` 時，請確保使用 `start /wait` 而不是 `start /min`，以避免工作排程器重複觸發

Linux/Mac (Crontab):
```bash
# Edit crontab
crontab -e

# Run daily at 6 AM
0 6 * * * cd /path/to/MediaCollect && python main.py --mode daily

# Run every 6 hours
0 */6 * * * cd /path/to/MediaCollect && python main.py --mode daily
```

**注意：** `daily`、`batch`、`all` 模式會自動使用文件鎖防止重複執行。如果任務仍在運行中，新的執行會自動退出。

### Method 2: Interactive Mode

**Use this when you want to manually choose what to collect.**

```bash
python main.py --mode interactive
```

The system will show you a menu:
1. Single user collection
2. Hashtag collection
3. Batch collection
4. All platforms

### Method 3: Command-Line Collection

**Collect a specific user:**

```bash
# Basic usage
python main.py --mode single --platform instagram --username nasa --post-limit 10

# With time filtering (Facebook only)
python main.py --mode single --platform facebook --username nasa --posts-newer-than "2024-01-01" --posts-older-than "2024-12-31"
```

**Batch collection from database:**

```bash
# Single platform
python main.py --mode batch --platform twitter

# With parallel processing
python main.py --mode batch --platform instagram --multiprocess --num-processes 4

# All platforms
python main.py --mode all
```

**Hashtag collection (Instagram only):**

```bash
# Single hashtag
python main.py --mode hashtag --platform instagram --hashtag travel

# Multiple hashtags
python main.py --mode hashtag --platform instagram --hashtag "travel,food,photography" --results-limit 100
```

### Method 4: Use in Python Code

**Basic example:**

```python
from core.factory import CollectorFactory, register_all_collectors
from core.database_manager import create_database_manager_from_config
from config.platform_config import APIFY_TOKEN, SQL_CONFIGURE_PATH

# Register all collectors
register_all_collectors()

# Create a collector
collector = CollectorFactory.create_collector(
    platform='instagram',
    username='nasa',
    api_token=APIFY_TOKEN
)

# Collect data
result = collector.collect_all(
    post_limit=20,
    story_limit=10,
    include_stories=True
)

# Save to database
if result.success:
    with create_database_manager_from_config(SQL_CONFIGURE_PATH) as db:
        db.save_collection_result(result)

    # Download media files
    for post in result.posts:
        collector.download_media(post, 'E:/media/')
```

**Instagram hashtag tracking:**

```python
from platforms.instagram_collector import InstagramHashtagCollector
from config.platform_config import APIFY_TOKEN

# Create hashtag collector
collector = InstagramHashtagCollector(
    hashtag="travel",
    api_token=APIFY_TOKEN,
    results_type="posts",  # "posts" or "reels"
    results_limit=50
)

# Collect posts with this hashtag
result = collector.collect_hashtag()

print(f"Collected {len(result.posts)} posts for #{result.hashtag}")

# View post details
for post in result.posts[:5]:
    print(f"\nAuthor: @{post.author_username}")
    print(f"Text: {post.text[:100]}...")
    print(f"Engagement: ❤️ {post.like_count} 💬 {post.comment_count}")
```

**Facebook with time filtering:**

```python
from core.factory import CollectorFactory, register_all_collectors
from config.platform_config import APIFY_TOKEN

register_all_collectors()

collector = CollectorFactory.create_collector(
    platform='facebook',
    username='microsoft',
    api_token=APIFY_TOKEN
)

# Collect last 7 days only
result = collector.collect_all(
    post_limit=50,
    posts_newer_than="7 days",
    caption_text=True
)

# Collect specific date range
result = collector.collect_all(
    post_limit=100,
    posts_newer_than="2024-01-01",
    posts_older_than="2024-12-31"
)
```

---

## Supported Platforms

| Platform | Status | What You Can Collect | Apify Actors Used |
|----------|--------|---------------------|-------------------|
| **Instagram** | ✅ Fully supported | User profiles, posts, stories, carousels, reels, hashtag tracking | `apify/instagram-profile-scraper`<br>`apify/instagram-post-scraper`<br>`igview-owner/instagram-story-viewer`<br>`apify/instagram-hashtag-scraper` |
| **Facebook** | ✅ Fully supported | Page info, posts, photos (with OCR) | `apify/facebook-pages-scraper`<br>`apify/facebook-posts-scraper`<br>`apify/facebook-photos-scraper` |
| **Twitter(X)** | ✅ Supported | User profiles, tweets, retweets, hashtags with time filtering | `apify/twitter-scraper` |
| **Threads** | ✅ Supported | User profiles, threads | `apify/threads-scraper` |
| **TikTok** | 🚧 Planned | - | - |
| **YouTube** | 🚧 Planned | - | - |

### Platform-Specific Features

**Instagram:**
- ✅ Profile info, posts, stories, reels
- ✅ Carousel posts (multiple images/videos)
- ✅ Hashtag tracking (find posts by topic)
- ✅ Story viewer (24-hour content)

**Facebook:**
- ✅ Page info with contact details (email, phone, address)
- ✅ Posts with engagement metrics
- ✅ Photo albums with OCR text extraction
- ✅ Time-range filtering
- ✅ Video caption extraction

**Twitter:**
- ✅ User profiles, tweets, retweets
- ✅ Native time filtering (since/until parameters)
- ✅ Hashtag search with precise time ranges
- ⭐ **Best for historical data** (2020-2024 range works perfectly)

**Threads:**
- ✅ User profiles, thread posts
- ✅ Thread-specific engagement metrics

---

## Key Features

### Core Capabilities

**Multi-platform support with unified interface**
- Single API works across Instagram, Facebook, Twitter, Threads
- Same code structure for all platforms
- Easy to add new platforms (implement 4 methods)

**Comprehensive data collection**
- User profiles: username, follower count, verified status, bio
- Posts: text, media URLs, engagement metrics, timestamps
- Stories: 24-hour temporary content (where supported)
- Media files: automatic download of images and videos

**Database integration**
- Automatic MySQL storage with standardized schema
- Incremental updates (only new/changed data)
- De-duplication by unique keys
- Collection history tracking

**Advanced features**
- Field value transformers (convert codes to readable text)
- Logging system with daily log files
- Collection history tracking in database
- Multi-process parallel collection
- Async concurrent collection
- Discord notifications

### Architecture Highlights

**Factory pattern for platform selection**
```python
# Automatically creates the right collector
collector = CollectorFactory.create_collector('instagram', 'nasa', api_token)
```

**Abstract base class design**
- All platforms inherit from `BaseSocialMediaCollector`
- Guaranteed consistent interface
- Easy to extend

**Unified data models**
- `PlatformUser` - standardized user data
- `SocialPost` - standardized post data
- `MediaItem` - standardized media data
- Works across all platforms

**Modular structure**
```
core/          # Base classes, factory, data models
platforms/     # Platform-specific implementations
lib/           # Utilities (media download, logging, notifications)
config/        # Settings and configuration
```

---

## Database Schema

### Unified Tables for All Platforms

**All platforms share the same tables**, differentiated by the `platform` column.

#### social_users

Stores user/page profiles:

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-increment primary key |
| platform | VARCHAR(20) | Platform name (instagram, facebook, twitter, threads) |
| user_id | VARCHAR(100) | Platform-specific user ID |
| username | VARCHAR(100) | Username/handle |
| display_name | VARCHAR(200) | Display name |
| is_verified | BOOLEAN | Verified account? |
| follower_count | INT | Number of followers |
| following_count | INT | Number following |
| post_count | INT | Number of posts |
| bio | TEXT | Profile bio/description |
| profile_pic_url | TEXT | Profile picture URL |
| external_url | TEXT | Website URL |
| ... | ... | ... |

**Unique key:** `(platform, user_id)`

#### social_posts

Stores posts, tweets, threads:

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-increment primary key |
| platform | VARCHAR(20) | Platform name |
| post_id | VARCHAR(100) | Platform-specific post ID |
| content_type | VARCHAR(20) | Type (post, tweet, reel, thread, story) |
| board_id | INT | Foreign key to social_users.id |
| text | TEXT | Text content |
| like_count | INT | Number of likes |
| comment_count | INT | Number of comments |
| share_count | INT | Number of shares |
| view_count | INT | Number of views |
| created_at | DATETIME | Post timestamp |
| post_url | TEXT | URL to post |
| ... | ... | ... |

**Unique key:** `(platform, post_id)`

#### social_stories

Stories (24-hour content), same structure as social_posts.

#### social_hashtag_posts

Posts from hashtag searches, includes `hashtag` column.

#### collection_history

Tracks every collection run:

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-increment primary key |
| platform | VARCHAR(20) | Platform collected |
| username | VARCHAR(100) | Username collected |
| success | BOOLEAN | Success or failure |
| post_count | INT | Posts collected |
| story_count | INT | Stories collected |
| duration_seconds | FLOAT | Execution time |
| error_message | TEXT | Error (if failed) |
| started_at | DATETIME | Start time |
| finished_at | DATETIME | End time |

**Query examples:**

```sql
-- View today's collections
SELECT * FROM collection_history
WHERE DATE(started_at) = CURDATE()
ORDER BY started_at DESC;

-- Platform success rates
SELECT
    platform,
    COUNT(*) as total,
    SUM(success) as success_count,
    ROUND(SUM(success) / COUNT(*) * 100, 2) as success_rate
FROM collection_history
GROUP BY platform;

-- Average execution time by platform
SELECT
    platform,
    AVG(duration_seconds) as avg_duration,
    AVG(post_count) as avg_posts
FROM collection_history
WHERE success = 1
GROUP BY platform;
```

### Querying Multi-Platform Data

**All posts across platforms:**
```sql
SELECT platform, username, text, like_count
FROM social_posts p
JOIN social_users u ON p.board_id = u.id
WHERE like_count > 10000
ORDER BY like_count DESC;
```

**Instagram posts only:**
```sql
SELECT * FROM social_posts
WHERE platform = 'instagram';
```

**Find user across all platforms:**
```sql
SELECT * FROM social_users
WHERE username = 'nasa';
```

---

## Adding New Platforms

**You can add new platforms by implementing just 4 methods.**

### Step 1: Create Collector Class

Create `platforms/tiktok_collector.py`:

```python
from core.base_collector import ApifyBasedCollector
from core.data_models import PlatformType, PlatformUser, SocialPost
from typing import Optional, List

class TikTokCollector(ApifyBasedCollector):
    def __init__(self, username: str, api_token: str):
        super().__init__(username, api_token, PlatformType.TIKTOK)

    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """Fetch TikTok user profile"""
        # Call Apify Actor
        items = self.call_apify_actor(ACTOR_ID, run_input)

        # Parse to unified format
        return PlatformUser(
            platform=PlatformType.TIKTOK,
            user_id=...,
            username=...,
            # ... map fields
        )

    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """Fetch TikTok videos"""
        # Implementation here
        pass

    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """Fetch stories (if supported)"""
        # Implementation here
        pass

    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """Download video files"""
        # Implementation here
        pass
```

### Step 2: Register in Factory

Edit `core/factory.py`:

```python
from platforms.tiktok_collector import TikTokCollector

def register_all_collectors():
    # ... existing registrations
    CollectorFactory.register_collector(PlatformType.TIKTOK, TikTokCollector)
```

### Step 3: Add Platform Settings

Edit `config/platform_config.py`:

```python
PLATFORM_SETTINGS = {
    # ... existing platforms
    'tiktok': {
        'enabled': True,
        'post_limit': 50,
        'download_media': True,
    }
}
```

**Done!** Now you can use it:

```python
collector = CollectorFactory.create_collector('tiktok', 'username', api_token)
result = collector.collect_all()
```

---

## Performance Tips

### Parallel Processing

**Use multi-process mode for best performance:**

```bash
# Let system decide core count
python main.py --mode daily --multiprocess

# Specify core count
python main.py --mode daily --multiprocess --num-processes 4
```

Multi-process mode is best when:
- Apify Actors may block/wait for long periods
- You have multiple CPU cores
- Processing independent users

### Batch Settings

**Adjust delays to avoid rate limits:**

Edit `config/platform_config.py`:

```python
# Delay between individual collections (seconds)
MIN_DELAY = 5
MAX_DELAY = 13

# Batch processing
BATCH_SIZE = 10              # Process this many before long delay
BATCH_DELAY_MIN = 100        # Minimum delay after batch (seconds)
BATCH_DELAY_MAX = 300        # Maximum delay after batch (seconds)
```

### Database Optimization

**Create indexes for faster queries:**

```sql
CREATE INDEX idx_platform ON social_users(platform);
CREATE INDEX idx_created ON social_posts(created_at);
CREATE INDEX idx_like_count ON social_posts(like_count);
CREATE INDEX idx_username ON social_users(username);
```

**For large datasets, use partitioning:**

```sql
CREATE TABLE social_posts (
    -- ... columns
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

### Media Download Settings

**Skip already downloaded files:**

The system automatically skips existing files unless you set `overwrite=True`.

**Limit post count to save quota:**

For free Apify accounts:
```python
PLATFORM_SETTINGS = {
    'instagram': {
        'post_limit': 10,  # Lower limit for free tier
    }
}
```

---

## Troubleshooting

### Common Issues

**"No Apify token found"**

Solution: Check your `.env` file contains:
```env
APIFY_TOKEN_1=apify_api_your_actual_token
```

**"Connection refused" database error**

Solutions:
1. Check MySQL is running: `mysql -u root -p`
2. Verify credentials in `.env` file
3. Test connection: `mysql -u your_user -p -h 127.0.0.1`

**"Actor run failed" or timeout**

Solutions:
1. Check Apify quota at [apify.com/account](https://apify.com/account)
2. Reduce `post_limit` and `photo_limit`
3. Check if account/page is public
4. Wait and retry (temporary rate limit)

**No data returned**

Possible causes:
- Account is private or doesn't exist
- Platform temporarily blocked Apify
- Reached Apify free tier limit
- Account has no posts

Solutions:
1. Verify account name is correct
2. Check account is public
3. Check Apify quota
4. Try with a different account

**Media files not downloading**

Solutions:
1. Check `MEDIA_FOLDER_PATH` in `.env` exists
2. Ensure folder is writable
3. Check `download_media: True` in settings
4. Check disk space

### Checking Logs

**Console output shows real-time progress.**

**Log files are in** `logs/MediaCollect_YYYYMMDD.log`

View today's log:
```bash
# Linux/Mac
tail -f logs/MediaCollect_20251025.log

# Windows
Get-Content logs/MediaCollect_20251025.log -Wait
```

Search for errors:
```bash
grep "ERROR" logs/MediaCollect_20251025.log
```

**Query collection history:**

```bash
python query_collection_history.py
```

Options:
1. Recent collections
2. Failed collections
3. Platform success rates
4. Performance stats
5. User-specific history
6. Today's summary

### Getting Help

**Check these resources:**
1. Review error messages in console or log files
2. Check `collection_history` table in database
3. Verify Apify Actor run at [apify.com/console](https://apify.com/console)
4. Review platform settings in `config/platform_config.py`
5. Test with example scripts in `examples/` folder

---

## Advanced Features

### Batch Time Collector

**Collect historical data by splitting time ranges into smaller intervals.**

This is especially useful for free Apify users who have quota limits.

```bash
# Twitter (best - native time filtering support)
python batch_time_collector.py \
  --platform twitter \
  --hashtag cat \
  --start-time 2020 \
  --end-time 2024 \
  --split-strategy years \
  --interval-size 1 \
  --results-limit 200 \
  --delay-min 15 \
  --delay-max 45
```

**Why Twitter is better for historical data:**
- Twitter Apify Actor supports native `since` and `until` parameters
- API-level time filtering (doesn't waste quota)
- No duplicate results
- Perfect for 2020-2024 multi-year collection

```bash
# Instagram (post-filtering)
python batch_time_collector.py \
  --platform instagram \
  --hashtag travel \
  --start-time 2024-01-01 \
  --end-time 2024-12-31 \
  --split-strategy months \
  --interval-size 2
```

**Feature comparison:**

| Feature | Twitter | Instagram |
|---------|---------|-----------|
| Time filtering | ✅ API native | ⚠️ Post-processing |
| Accuracy | 🎯 Perfect | 📊 Depends on collection time |
| Duplicates | ❌ None | ⚠️ Possible |
| Best for | Long-term historical data | Recent data |

### Field Value Transformers

**Transform database field values for better readability.**

Example: Convert media type codes to readable text.

Define transformer in `config/platform_config.py`:

```python
def transform_media_type(value):
    """Convert media type number to readable string"""
    media_type_mapping = {
        1: "IMAGE",
        2: "VIDEO",
        8: "CAROUSEL",
    }
    if value is None:
        return None
    return media_type_mapping.get(value, f"UNKNOWN_{value}")

# Register transformers
FIELD_TRANSFORMERS = {
    'primary_media_type': transform_media_type,
    'is_verified': transform_boolean_to_text,
}
```

**Transformers apply automatically when saving to database.**

Built-in transformers:
1. `transform_media_type`: 1 → "IMAGE", 2 → "VIDEO", 8 → "CAROUSEL"
2. `transform_boolean_to_text`: True → "是", False → "否"
3. `transform_count_to_display`: 1234567 → "1.2M"

Test transformers:
```bash
python test_field_transformers.py
```

### Instagram Hashtag Tracking

**Track posts by hashtag instead of by user.**

Single hashtag:
```bash
python main.py --mode hashtag --platform instagram --hashtag travel
```

Multiple hashtags:
```bash
python main.py --mode hashtag --platform instagram --hashtag "travel,food,photography" --results-limit 100
```

In Python:
```python
from platforms.instagram_collector import InstagramHashtagCollector

collector = InstagramHashtagCollector(
    hashtag="travel",
    api_token=APIFY_TOKEN,
    results_type="posts",  # or "reels"
    results_limit=50
)

result = collector.collect_hashtag()
```

**Use cases:**
- Brand monitoring (track brand-related hashtags)
- Trend analysis (discover trending topics)
- KOL discovery (find active creators in a niche)
- Competitor research (track competitor hashtags)

### Logging and Monitoring

**Every collection run is logged.**

Log files: `logs/MediaCollect_YYYYMMDD.log`

Collection history is saved to `collection_history` table with:
- Platform and username
- Success/failure status
- Post/story counts
- Execution time
- Error messages (if failed)

Query tool:
```bash
python query_collection_history.py
```

Available queries:
1. Recent collections
2. Failed collections only
3. Success rate by platform
4. Performance statistics
5. History for specific user
6. Today's summary

---

## Important Notes

### Legal and Ethical Use

⚠️ **Comply with laws and platform terms:**
- Ensure you have permission to collect data
- Don't scrape private accounts
- Review platform terms of service before commercial use
- Protect collected data appropriately

### Technical Limitations

📌 **Apify quota limits:**
- Free tier: limited compute units per month
- Each actor run consumes units
- Monitor usage at [apify.com/account](https://apify.com/account)

📌 **Platform restrictions:**
- Private accounts cannot be scraped
- Platforms may change APIs (breaking scrapers)
- Stories only available for 24 hours
- Rate limits may apply

### Performance Recommendations

💡 **Collection limits:**
- Single collection: max 100 posts recommended
- Batch processing: add delays (5-15 seconds between users)
- Free tier: 10-20 posts per account recommended

💡 **Storage:**
- Clean old media files periodically
- Create database indexes on frequently queried columns
- Consider partitioning tables for large datasets

### Security

🔒 **Protect your API tokens:**
- Never commit `.env` to version control
- Add `accounts.txt` to `.gitignore`
- Use environment variables in production

🔒 **Database security:**
- Use strong passwords
- Don't expose MySQL to public internet
- Regular backups

---

## Project Statistics

- **Supported platforms**: 4 (Instagram, Facebook, Twitter, Threads)
- **Code base**: ~3,000 lines
- **Core classes**: 10+
- **Database tables**: 7
- **Example scripts**: 6+

---

## Version History

### v2.3.0 (2025-10) - Multi-Process & Async Concurrency

- ✅ Multi-process parallel processing (`--multiprocess`)
- ✅ True multi-core parallelism for Apify Actor blocking
- ✅ `--num-processes` parameter (defaults to CPU count)
- ✅ Async concurrent collection (`--async`)
- ✅ `--concurrent-limit` parameter
- ✅ Supported in `daily` and `batch` modes

### v2.2.0 (2024-10) - Account Configuration File

- ✅ Account list file support (`accounts.txt`)
- ✅ Daily collection mode (`--mode daily`)
- ✅ Automated scheduled collection
- ✅ `config/accounts_loader.py` module
- ✅ `accounts.example.txt` template

### v2.1.0 (2024-10) - Field Transformers

- ✅ Field value transformation mechanism
- ✅ Custom transformation rules in config
- ✅ 3 built-in transformers
- ✅ Automatic application on database save
- ✅ Graceful fallback on transformation errors

### v2.0.0 (2024-10) - Universal Architecture Redesign

- ✅ Redesigned for multi-platform architecture
- ✅ Added Facebook, Twitter, Threads support
- ✅ Unified data models and database schema
- ✅ Factory pattern for collector selection
- ✅ Easy platform extension

---

## Contributing

Issues and pull requests welcome!

---

## License

For educational and research purposes only. Ensure compliance with platform terms of service and Apify policies.

---

**⭐ If this project helps you, please give it a star!**
