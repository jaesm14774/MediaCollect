# Architecture Design Documentation

**This document explains how MediaCollect is built and how to extend it.**

MediaCollect uses a **Strategy Pattern + Factory Pattern + Abstract Base Class** design that makes it easy to add new social media platforms.

---

## Table of Contents

- [System Overview](#system-overview)
- [Design Patterns](#design-patterns)
- [Data Models](#data-models)
- [Module Structure](#module-structure)
- [Database Design](#database-design)
- [How to Add a New Platform](#how-to-add-a-new-platform)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Testing Strategy](#testing-strategy)
- [Security Considerations](#security-considerations)

---

## System Overview

### What Problems Does This Architecture Solve?

**Problem:** Each social media platform has different APIs and data formats.

**Solution:** MediaCollect provides a unified interface that works across all platforms:

```python
# Same code works for any platform
collector = CollectorFactory.create_collector('instagram', 'nasa', api_token)
result = collector.collect_all()

collector = CollectorFactory.create_collector('twitter', 'elonmusk', api_token)
result = collector.collect_all()  # Same method, different platform
```

**Key benefits:**
- **Write once, use everywhere**: Client code doesn't need platform-specific logic
- **Easy to add platforms**: Implement 4 methods and register
- **Standardized data**: All platforms use the same data models
- **Maintainable**: Each platform's code is isolated

---

## Design Patterns

### Pattern 1: Strategy Pattern

**Strategy pattern encapsulates platform-specific collection logic.**

Each platform implements the same interface but with different behavior:

```python
# Abstract strategy (the interface)
class BaseSocialMediaCollector(ABC):
    @abstractmethod
    def fetch_user_profile(self) -> PlatformUser:
        """Every platform must implement this"""
        pass

    @abstractmethod
    def fetch_posts(self, limit: int) -> List[SocialPost]:
        """Every platform must implement this"""
        pass

# Concrete strategy for Instagram
class InstagramCollector(BaseSocialMediaCollector):
    def fetch_user_profile(self):
        # Instagram-specific implementation
        return PlatformUser(...)

    def fetch_posts(self, limit: int):
        # Instagram-specific implementation
        return [SocialPost(...), ...]

# Concrete strategy for Twitter
class TwitterCollector(BaseSocialMediaCollector):
    def fetch_user_profile(self):
        # Twitter-specific implementation
        return PlatformUser(...)

    def fetch_posts(self, limit: int):
        # Twitter-specific implementation
        return [SocialPost(...), ...]
```

**Why this is good:**
- **Separation of concerns**: Instagram logic doesn't mix with Twitter logic
- **Easy testing**: Test each platform independently
- **Open/Closed Principle**: Add platforms without changing existing code

### Pattern 2: Factory Pattern

**Factory pattern automatically creates the right collector for each platform.**

Users don't need to know which collector class to use:

```python
class CollectorFactory:
    _collectors = {}  # Registry of available collectors

    @classmethod
    def create_collector(cls, platform: str, username: str, api_token: str):
        """Factory method that creates the right collector"""
        platform_enum = PlatformType(platform)
        collector_class = cls._collectors[platform_enum]
        return collector_class(username, api_token)

    @classmethod
    def register_collector(cls, platform: PlatformType, collector_class):
        """Register a new platform collector"""
        cls._collectors[platform] = collector_class
```

**Usage:**

```python
# User doesn't need to know about InstagramCollector class
collector = CollectorFactory.create_collector('instagram', 'nasa', token)
```

**Why this is good:**
- **Centralized creation logic**: One place manages all collectors
- **Client code is simple**: No need to import specific collector classes
- **Easy registration**: Adding a platform is just one line

### Pattern 3: Template Method Pattern

**Template method defines a standard collection workflow.**

The base class defines the steps, subclasses fill in the details:

```python
class BaseSocialMediaCollector:
    def collect_all(self, post_limit, story_limit, include_stories):
        """Template method: defines the standard workflow"""

        # Step 1: Fetch user profile (subclass implements)
        user = self.fetch_user_profile()

        # Step 2: Fetch posts (subclass implements)
        posts = self.fetch_posts(post_limit)

        # Step 3: Fetch stories if requested (subclass implements)
        stories = []
        if include_stories:
            stories = self.fetch_stories(story_limit)

        # Step 4: Package results
        return CollectionResult(
            platform=self.platform,
            user=user,
            posts=posts,
            stories=stories
        )
```

**Why this is good:**
- **Consistent workflow**: All platforms follow the same steps
- **No code duplication**: Common logic lives in base class
- **Guaranteed completeness**: Can't forget a step

---

## Data Models

### Unified Data Classes

**All platforms use the same data structures.**

This makes cross-platform analysis easy:

#### PlatformUser

Represents any user/account/page across platforms:

```python
@dataclass
class PlatformUser:
    """Universal user model for all platforms"""

    platform: PlatformType           # Which platform (instagram, facebook, etc.)
    user_id: str                     # Platform-specific ID
    username: str                    # Username/handle
    display_name: Optional[str]      # Display name
    is_verified: bool                # Verified account?
    follower_count: int              # Number of followers
    following_count: int             # Number following
    post_count: int                  # Number of posts
    bio: Optional[str]               # Profile bio/description
    profile_pic_url: Optional[str]   # Profile picture URL
    external_url: Optional[str]      # Website URL
    # ... more common fields
```

#### SocialPost

Represents any post/tweet/thread across platforms:

```python
@dataclass
class SocialPost:
    """Universal post model for all platforms"""

    platform: PlatformType           # Which platform
    post_id: str                     # Platform-specific post ID
    content_type: ContentType        # Type (post, tweet, reel, etc.)
    text: Optional[str]              # Text content
    like_count: int                  # Number of likes
    comment_count: int               # Number of comments
    share_count: int                 # Number of shares
    view_count: int                  # Number of views
    created_at: Optional[datetime]   # Post timestamp
    post_url: Optional[str]          # URL to post
    media_items: List[MediaItem]     # Attached media (images/videos)
    hashtags: List[str]              # Hashtags used
    mentions: List[str]              # Users mentioned
    # ... more common fields
```

#### MediaItem

Represents images and videos:

```python
@dataclass
class MediaItem:
    """Universal media model for all platforms"""

    media_type: str                  # "image" or "video"
    url: str                         # Media URL
    thumbnail_url: Optional[str]     # Thumbnail URL
    width: Optional[int]             # Width in pixels
    height: Optional[int]            # Height in pixels
    duration: Optional[float]        # Duration (for videos)
```

### Enum Types

**Enums provide type safety:**

```python
class PlatformType(Enum):
    """Supported platforms"""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"

class ContentType(Enum):
    """Content types"""
    POST = "post"
    TWEET = "tweet"
    REEL = "reel"
    THREAD = "thread"
    STORY = "story"
```

**Benefits:**
- **Type checking**: Catch typos at development time
- **IDE autocomplete**: Better developer experience
- **Clear values**: No magic strings

### Design Principle: Universal Fields

**The data models include all fields that ANY platform might have.**

If a platform doesn't support a field, it's set to `None` or a default value:

```python
# Instagram has stories, Facebook doesn't
instagram_user = PlatformUser(
    platform=PlatformType.INSTAGRAM,
    username="nasa",
    story_count=5,  # Instagram supports stories
    # ...
)

facebook_user = PlatformUser(
    platform=PlatformType.FACEBOOK,
    username="nasa",
    story_count=0,  # Facebook doesn't have stories, so it's 0
    # ...
)
```

---

## Module Structure

### Directory Organization

```
MediaCollect/
├── core/                       # Core system (platform-independent)
│   ├── base_collector.py      # Abstract base class for collectors
│   ├── data_models.py          # Universal data models
│   ├── factory.py              # Factory for creating collectors
│   └── database_manager.py     # Database operations
│
├── platforms/                  # Platform implementations
│   ├── instagram_collector.py # Instagram-specific code
│   ├── facebook_collector.py  # Facebook-specific code
│   ├── twitter_collector.py   # Twitter-specific code
│   └── threads_collector.py   # Threads-specific code
│
├── lib/                        # Utilities (reusable tools)
│   ├── logger.py              # Logging system
│   ├── media_downloader.py    # Media file downloads
│   ├── get_sql_connection.py  # Database connections
│   └── discord_notify.py      # Discord notifications
│
├── config/                     # Configuration
│   ├── platform_config.py     # Platform settings
│   └── accounts_loader.py     # Account list loader
│
└── main.py                     # Main entry point
```

### Core Module

**Contains platform-independent code.**

Purpose:
- Define the abstract interface all platforms must follow
- Provide universal data models
- Manage the factory registry
- Handle database operations

Key principle: **Core code never imports from platforms.**

### Platforms Module

**Contains platform-specific implementations.**

Each file is independent:
- `instagram_collector.py` only knows about Instagram
- `facebook_collector.py` only knows about Facebook
- They don't know about each other

Key principle: **Platforms inherit from core but don't modify it.**

### Lib Module

**Contains reusable utilities.**

These tools are used by multiple parts of the system:
- Logging (used by all collectors)
- Media download (used by all collectors)
- Database connections (used by database manager)

Key principle: **Utilities have no business logic.**

### Class Hierarchy

```
BaseSocialMediaCollector (Abstract)
    ↓
ApifyBasedCollector (Base for Apify-using platforms)
    ↓
    ├── InstagramCollector
    │   └── InstagramHashtagCollector (Specialized for hashtags)
    ├── FacebookCollector
    ├── TwitterCollector
    └── ThreadsCollector

CollectorFactory (Factory)
    └── Creates and manages all collectors

DatabaseManager (Database operations)
    └── Saves data from any collector
```

---

## Database Design

### Unified Schema for All Platforms

**All platforms share the same tables.**

The `platform` column differentiates data from different sources:

#### Design Decision: One Table for All Platforms

**Why not separate tables per platform?**

❌ **Separate tables** (e.g., `instagram_users`, `facebook_users`):
- Hard to query across platforms
- Duplicated schema
- More tables to maintain

✅ **Unified tables** with `platform` column:
- Easy cross-platform queries
- Single schema to maintain
- Natural joins work smoothly

#### social_users Table

```sql
CREATE TABLE social_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20),          -- Differentiates platforms
    user_id VARCHAR(100),
    username VARCHAR(100),
    display_name VARCHAR(200),
    is_verified BOOLEAN,
    follower_count INT,
    following_count INT,
    post_count INT,
    bio TEXT,
    profile_pic_url TEXT,
    external_url TEXT,
    -- ... more common fields

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY unique_platform_user (platform, user_id)
);
```

**Key design points:**
- **Composite unique key** `(platform, user_id)` ensures no duplicates per platform
- **Timestamps** track when data was first collected and last updated
- **TEXT fields** for variable-length content (bio, URLs)

#### social_posts Table

```sql
CREATE TABLE social_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20),          -- Differentiates platforms
    post_id VARCHAR(100),
    content_type VARCHAR(20),      -- post, tweet, reel, etc.
    board_id INT,                  -- Foreign key to social_users.id
    text TEXT,
    like_count INT,
    comment_count INT,
    share_count INT,
    view_count INT,
    created_at DATETIME,           -- Post creation time
    post_url TEXT,
    -- ... more fields

    UNIQUE KEY unique_platform_post (platform, post_id),
    FOREIGN KEY (board_id) REFERENCES social_users(id) ON DELETE CASCADE
);
```

**Key design points:**
- **Foreign key to users**: `board_id` links to who posted it
- **ON DELETE CASCADE**: If user is deleted, their posts are deleted
- **Nullable counts**: Some platforms don't provide all metrics

### Cross-Platform Queries

**Query all platforms together:**

```sql
-- Top posts across ALL platforms
SELECT
    u.platform,
    u.username,
    p.text,
    p.like_count
FROM social_posts p
JOIN social_users u ON p.board_id = u.id
WHERE p.like_count > 10000
ORDER BY p.like_count DESC;
```

**Query specific platform:**

```sql
-- Instagram posts only
SELECT * FROM social_posts
WHERE platform = 'instagram';
```

**Cross-platform user comparison:**

```sql
-- Compare follower count across platforms
SELECT
    platform,
    username,
    follower_count
FROM social_users
WHERE username IN ('nasa', 'natgeo')
ORDER BY username, platform;
```

### Indexes for Performance

**Create indexes on frequently queried columns:**

```sql
CREATE INDEX idx_platform ON social_users(platform);
CREATE INDEX idx_username ON social_users(username);
CREATE INDEX idx_created_at ON social_posts(created_at);
CREATE INDEX idx_like_count ON social_posts(like_count);
CREATE INDEX idx_board_id ON social_posts(board_id);
```

**When to add indexes:**
- Columns used in `WHERE` clauses
- Columns used in `ORDER BY`
- Foreign keys (for joins)

**Trade-off:** Indexes speed up reads but slow down writes. Balance based on your usage pattern.

---

## How to Add a New Platform

**Adding a platform requires implementing just 4 methods.**

Let's add TikTok as an example.

### Step 1: Create Collector Class

Create `platforms/tiktok_collector.py`:

```python
from core.base_collector import ApifyBasedCollector
from core.data_models import PlatformType, PlatformUser, SocialPost, MediaItem
from typing import Optional, List

class TikTokCollector(ApifyBasedCollector):
    """Collector for TikTok platform"""

    def __init__(self, username: str, api_token: str):
        super().__init__(username, api_token, PlatformType.TIKTOK)

    def fetch_user_profile(self) -> Optional[PlatformUser]:
        """Fetch TikTok user profile"""

        # Define Apify Actor input
        run_input = {
            "usernames": [self.username],
            "resultsLimit": 1
        }

        # Call Apify Actor
        items = self.call_apify_actor(
            actor_id="apify/tiktok-scraper",
            run_input=run_input
        )

        if not items:
            return None

        raw = items[0]

        # Map TikTok data to universal format
        return PlatformUser(
            platform=PlatformType.TIKTOK,
            user_id=raw.get('id', ''),
            username=raw.get('uniqueId', self.username),
            display_name=raw.get('nickname'),
            is_verified=raw.get('verified', False),
            follower_count=raw.get('fans', 0),
            following_count=raw.get('following', 0),
            post_count=raw.get('video', 0),
            bio=raw.get('signature'),
            profile_pic_url=raw.get('avatarLarger'),
            # ... map more fields
        )

    def fetch_posts(self, limit: int = 50) -> List[SocialPost]:
        """Fetch TikTok videos"""

        run_input = {
            "usernames": [self.username],
            "resultsLimit": limit
        }

        items = self.call_apify_actor(
            actor_id="apify/tiktok-scraper",
            run_input=run_input
        )

        posts = []
        for raw in items:
            # Parse video
            post = SocialPost(
                platform=PlatformType.TIKTOK,
                post_id=raw.get('id', ''),
                content_type=ContentType.POST,
                text=raw.get('text'),
                like_count=raw.get('diggCount', 0),
                comment_count=raw.get('commentCount', 0),
                share_count=raw.get('shareCount', 0),
                view_count=raw.get('playCount', 0),
                created_at=self._parse_timestamp(raw.get('createTime')),
                post_url=raw.get('webVideoUrl'),
                media_items=self._parse_media(raw),
                # ... map more fields
            )
            posts.append(post)

        return posts

    def fetch_stories(self, limit: Optional[int] = None) -> List[SocialPost]:
        """TikTok doesn't have stories feature"""
        return []

    def download_media(self, post: SocialPost, save_dir: str) -> bool:
        """Download TikTok video"""

        # Implementation here
        # Use self.media_downloader to download videos
        pass

    def _parse_media(self, raw: dict) -> List[MediaItem]:
        """Parse TikTok video into MediaItem"""
        video_url = raw.get('videoUrl')
        if not video_url:
            return []

        return [MediaItem(
            media_type="video",
            url=video_url,
            thumbnail_url=raw.get('covers', {}).get('default'),
            width=raw.get('width'),
            height=raw.get('height'),
            duration=raw.get('duration')
        )]
```

### Step 2: Register the Collector

Edit `core/factory.py`:

```python
from platforms.instagram_collector import InstagramCollector
from platforms.facebook_collector import FacebookCollector
from platforms.twitter_collector import TwitterCollector
from platforms.threads_collector import ThreadsCollector
from platforms.tiktok_collector import TikTokCollector  # Add this

def register_all_collectors():
    """Register all available collectors"""
    CollectorFactory.register_collector(PlatformType.INSTAGRAM, InstagramCollector)
    CollectorFactory.register_collector(PlatformType.FACEBOOK, FacebookCollector)
    CollectorFactory.register_collector(PlatformType.TWITTER, TwitterCollector)
    CollectorFactory.register_collector(PlatformType.THREADS, ThreadsCollector)
    CollectorFactory.register_collector(PlatformType.TIKTOK, TikTokCollector)  # Add this
```

### Step 3: Add to Enum

Edit `core/data_models.py`:

```python
class PlatformType(Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"
    TIKTOK = "tiktok"  # Add this
```

### Step 4: Add Platform Settings

Edit `config/platform_config.py`:

```python
PLATFORM_SETTINGS = {
    # ... existing platforms
    'tiktok': {
        'enabled': True,
        'post_limit': 50,
        'story_limit': None,
        'download_media': True,
    }
}
```

### Step 5: Use It!

```python
# Now TikTok works just like other platforms
collector = CollectorFactory.create_collector('tiktok', 'username', api_token)
result = collector.collect_all(post_limit=20)

# Save to database (same code)
with DatabaseManager(...) as db:
    db.save_collection_result(result)
```

**That's it!** The platform is fully integrated.

---

## Error Handling

### Multi-Level Error Handling Strategy

**Errors are caught at multiple levels for graceful degradation.**

#### Level 1: Method Level

Individual methods catch their own errors:

```python
def fetch_posts(self, limit: int) -> List[SocialPost]:
    """Fetch posts from platform"""
    try:
        items = self.call_apify_actor(actor_id, run_input)
        return self._parse_posts(items)
    except Exception as e:
        logger.error(f"Failed to fetch posts: {e}")
        return []  # Return empty list instead of crashing
```

**Benefit:** System continues even if one operation fails.

#### Level 2: Collection Workflow Level

The `collect_all` method packages results with status:

```python
def collect_all(self, post_limit, story_limit, include_stories):
    """Collect all data with error handling"""
    try:
        user = self.fetch_user_profile()
        posts = self.fetch_posts(post_limit)
        stories = self.fetch_stories(story_limit) if include_stories else []

        return CollectionResult(
            platform=self.platform,
            success=True,
            user=user,
            posts=posts,
            stories=stories,
            error_message=None
        )
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        return CollectionResult(
            platform=self.platform,
            success=False,
            error_message=str(e)
        )
```

**Benefit:** Caller knows if collection succeeded or failed.

#### Level 3: Batch Processing Level

When collecting multiple users, errors don't stop the batch:

```python
def batch_collect(self, usernames):
    """Collect from multiple users"""
    for username in usernames:
        try:
            result = self.collect_user(username)
            if result.success:
                logger.info(f"✓ Collected {username}")
            else:
                logger.warning(f"✗ Failed {username}: {result.error_message}")
        except Exception as e:
            logger.error(f"✗ Error {username}: {e}")
            notify_discord(f"Collection error for {username}")
            continue  # Keep processing other users
```

**Benefit:** One failure doesn't ruin the entire batch.

### CollectionResult Object

**Encapsulates success/failure status:**

```python
@dataclass
class CollectionResult:
    platform: PlatformType
    success: bool                    # Did collection succeed?
    user: Optional[PlatformUser]     # User data (if successful)
    posts: List[SocialPost]          # Posts collected
    stories: List[SocialPost]        # Stories collected
    error_message: Optional[str]     # Error (if failed)
    started_at: datetime
    finished_at: datetime
```

**Usage:**

```python
result = collector.collect_all()

if result.success:
    print(f"Collected {len(result.posts)} posts")
    save_to_database(result)
else:
    print(f"Failed: {result.error_message}")
    send_alert(result.error_message)
```

---

## Performance Optimization

### Strategy 1: Batch Processing with Delays

**Avoid rate limits by spacing out requests:**

```python
# Process in batches
BATCH_SIZE = 10
DELAY_MIN = 5
DELAY_MAX = 13
BATCH_DELAY = 120

for i, username in enumerate(usernames):
    # Collect data
    collect_user(username)

    # Small delay between users
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    # Longer delay after each batch
    if (i + 1) % BATCH_SIZE == 0:
        time.sleep(random.uniform(100, 300))
```

**Why random delays?** Looks more human, less likely to trigger anti-bot measures.

### Strategy 2: Multi-Process Parallelism

**Use multiple CPU cores for true parallelism:**

```python
from multiprocessing import Pool, cpu_count

def collect_user_wrapper(username):
    """Wrapper function for multiprocessing"""
    collector = CollectorFactory.create_collector(platform, username, token)
    return collector.collect_all()

# Process users in parallel
with Pool(processes=cpu_count()) as pool:
    results = pool.map(collect_user_wrapper, usernames)
```

**Best for:** Apify Actors that may block/wait for long periods.

### Strategy 3: Database Optimizations

**Create indexes on query columns:**

```sql
-- Indexes for common queries
CREATE INDEX idx_platform ON social_users(platform);
CREATE INDEX idx_created_at ON social_posts(created_at);
CREATE INDEX idx_like_count ON social_posts(like_count);
```

**Partition large tables:**

```sql
-- Partition by year for historical data
CREATE TABLE social_posts (
    -- ... columns
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

**Benefit:** Queries on specific time ranges only scan relevant partitions.

### Strategy 4: Media Download Optimization

**Skip already downloaded files:**

```python
def download(self, url, file_path, overwrite=False):
    """Download media file"""

    # Skip if already exists
    if os.path.exists(file_path) and not overwrite:
        return False

    # Retry mechanism
    for attempt in range(self.retry_count):
        try:
            response = requests.get(url, timeout=self.timeout)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            if attempt < self.retry_count - 1:
                time.sleep(random.uniform(2, 5))
            else:
                raise

    return False
```

---

## Testing Strategy

### Unit Testing

**Test individual collectors:**

```python
def test_instagram_collector():
    """Test Instagram collector"""
    collector = InstagramCollector('instagram', APIFY_TOKEN)

    # Test user profile
    user = collector.fetch_user_profile()
    assert user is not None
    assert user.platform == PlatformType.INSTAGRAM
    assert user.username == 'instagram'
    assert user.follower_count > 0

    # Test posts
    posts = collector.fetch_posts(limit=5)
    assert len(posts) > 0
    assert all(p.platform == PlatformType.INSTAGRAM for p in posts)
    assert all(p.post_id for p in posts)
```

### Integration Testing

**Test full workflow:**

```python
def test_full_collection_workflow():
    """Test end-to-end collection"""

    # Create collector
    collector = CollectorFactory.create_collector('instagram', 'nasa', token)

    # Collect data
    result = collector.collect_all(post_limit=5)

    # Verify results
    assert result.success
    assert result.user is not None
    assert len(result.posts) > 0

    # Save to database
    with DatabaseManager(config) as db:
        db.save_collection_result(result)

    # Verify database
    with DatabaseManager(config) as db:
        users = db.get_users(platform='instagram', username='nasa')
        assert len(users) == 1
```

### Mock Testing

**Test without calling real APIs:**

```python
from unittest.mock import Mock, patch

def test_collector_with_mock():
    """Test collector with mocked Apify"""

    # Mock Apify response
    mock_response = [{
        'id': '123',
        'username': 'test_user',
        'followersCount': 1000
    }]

    with patch.object(collector, 'call_apify_actor', return_value=mock_response):
        user = collector.fetch_user_profile()
        assert user.username == 'test_user'
        assert user.follower_count == 1000
```

---

## Security Considerations

### API Token Protection

**Never hard-code tokens:**

```python
# ❌ Bad - Hard-coded token
APIFY_TOKEN = "apify_api_1234567890abcdef"

# ✅ Good - Environment variable
APIFY_TOKEN = os.getenv('APIFY_TOKEN')

# ✅ Good - Config file
with open('.env') as f:
    APIFY_TOKEN = f.read().strip()
```

**Add sensitive files to .gitignore:**

```gitignore
.env
accounts.txt
config.txt
sql_config.txt
```

### SQL Injection Prevention

**Always use parameterized queries:**

```python
# ❌ Bad - String concatenation
query = f"SELECT * FROM users WHERE username = '{username}'"

# ✅ Good - Parameterized query
cursor.execute(
    "SELECT * FROM users WHERE platform = %s AND username = %s",
    (platform, username)
)

# ✅ Good - SQLAlchemy/Pandas
df.to_sql('table_name', engine, if_exists='append')
```

### File Path Validation

**Validate paths to prevent directory traversal:**

```python
def download_media(self, url, file_path):
    """Download media with path validation"""

    # Prevent directory traversal
    if '..' in file_path:
        raise ValueError("Invalid file path: contains '..'")

    # Ensure within allowed directory
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(os.path.abspath(MEDIA_FOLDER_PATH)):
        raise ValueError("Path outside allowed directory")

    # Now safe to download
    # ...
```

---

## Summary

### Architecture Strengths

✅ **Highly extensible**: Add platforms by implementing 4 methods
✅ **Unified interface**: Same API for all platforms
✅ **Data standardization**: Cross-platform analysis is easy
✅ **Maintainable**: Modular design, clear separation of concerns
✅ **Error tolerant**: Multi-level error handling

### Design Principles

**SOLID Principles:**
- **Single Responsibility**: Each class has one job
- **Open/Closed**: Open for extension (new platforms), closed for modification
- **Liskov Substitution**: Any collector can substitute for BaseSocialMediaCollector
- **Interface Segregation**: Minimal interface (just 4 methods)
- **Dependency Inversion**: Depend on abstractions (BaseSocialMediaCollector) not concrete classes

**Other Principles:**
- **DRY** (Don't Repeat Yourself): Common code in base classes
- **Separation of Concerns**: Core, platforms, lib are independent
- **Convention over Configuration**: Sensible defaults, customize when needed

### Future Extension Opportunities

🚀 **More platforms**: TikTok, YouTube, LinkedIn, Reddit
🚀 **Async collection**: Use asyncio for faster I/O
🚀 **ML integration**: Sentiment analysis, content classification
🚀 **Web interface**: Flask/Django dashboard
🚀 **RESTful API**: HTTP API for remote collection
🚀 **Real-time collection**: WebSocket streaming
🚀 **Advanced analytics**: Trend detection, influencer identification

---

**This architecture provides a solid foundation for long-term growth and maintenance!**
