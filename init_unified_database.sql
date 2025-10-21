-- ============================================================================
-- 通用社群媒體資料收集系統 - 資料庫初始化腳本
-- 支援多平台: Instagram, Facebook, Twitter(X), Threads 等
-- ============================================================================

USE crawler;

-- ============================================================================
-- 1. 使用者管理表 (social_users)
-- 統一管理所有平台的使用者資料
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL COMMENT '平台類型 (instagram, facebook, twitter, threads)',
    user_id VARCHAR(100) NOT NULL COMMENT '平台使用者 ID',
    username VARCHAR(100) NOT NULL COMMENT '使用者名稱',
    display_name VARCHAR(200) COMMENT '顯示名稱/全名',
    
    -- 帳號屬性
    is_verified BOOLEAN DEFAULT FALSE COMMENT '是否認證',
    is_private BOOLEAN DEFAULT FALSE COMMENT '是否私人帳號',
    is_business BOOLEAN DEFAULT FALSE COMMENT '是否商業帳號',
    
    -- 個人資訊
    description TEXT COMMENT '個人簡介',
    profile_image_url TEXT COMMENT '頭像 URL',
    banner_image_url TEXT COMMENT '封面圖 URL',
    category VARCHAR(100) COMMENT '分類/類別',
    
    -- 統計數據
    follower_count INT DEFAULT 0 COMMENT '追蹤者數',
    following_count INT DEFAULT 0 COMMENT '追蹤中數',
    post_count INT DEFAULT 0 COMMENT '貼文數',
    
    -- 聯絡資訊
    external_url TEXT COMMENT '外部連結',
    email VARCHAR(100) COMMENT '電子郵件',
    phone VARCHAR(50) COMMENT '電話',
    
    -- 位置資訊
    location VARCHAR(200) COMMENT '地點',
    latitude DECIMAL(10, 8) COMMENT '緯度',
    longitude DECIMAL(11, 8) COMMENT '經度',
    
    -- 原始資料
    raw_data LONGTEXT COMMENT '完整原始 JSON 資料（字串格式），保留所有從 Apify Actor 取得的資料',
    
    -- 狀態與時間
    status TINYINT DEFAULT 1 COMMENT '狀態 (1=啟用, 0=停用)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬蟲收集此資料的時間',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    
    -- 索引 (移除 unique key,允許同一使用者有多筆歷史記錄)
    INDEX idx_platform_user (platform, user_id),
    INDEX idx_platform (platform),
    INDEX idx_username (username),
    INDEX idx_status (status),
    INDEX idx_is_verified (is_verified),
    INDEX idx_create_time (create_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通用社群媒體使用者歷史表 (每次收集都會新增記錄)';

-- ============================================================================
-- 2. 貼文資料表 (social_posts)
-- 統一儲存所有平台的貼文/推文/串文
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_posts (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL COMMENT '平台類型',
    post_id VARCHAR(100) NOT NULL COMMENT '貼文 ID',
    content_type VARCHAR(20) COMMENT '內容類型 (post, tweet, reel, thread)',
    
    -- 作者資訊
    author_id VARCHAR(100) COMMENT '作者 ID',
    author_username VARCHAR(100) COMMENT '作者名稱',
    author_display_name VARCHAR(200) COMMENT '作者顯示名稱',
    
    -- 內容資訊
    text TEXT COMMENT '文字內容',
    title TEXT COMMENT '標題',
    language VARCHAR(10) COMMENT '語言',
    
    -- 媒體資訊
    media_count INT DEFAULT 0 COMMENT '媒體數量',
    primary_media_type VARCHAR(20) COMMENT '主要媒體類型 (image, video)',
    primary_media_url TEXT COMMENT '主要媒體 URL',
    sub_image_url TEXT COMMENT '子圖片 URL 列表 (用逗號分隔)',
    sub_video_url TEXT COMMENT '子影片 URL 列表 (用逗號分隔)',
    sub_thumbnail_url TEXT COMMENT '子縮圖 URL 列表 (用逗號分隔)',
    
    -- 互動數據
    like_count INT DEFAULT 0 COMMENT '按讚數',
    comment_count INT DEFAULT 0 COMMENT '留言數',
    share_count INT DEFAULT 0 COMMENT '分享數',
    view_count INT DEFAULT 0 COMMENT '觀看數',
    bookmark_count INT DEFAULT 0 COMMENT '收藏數',
    
    -- 貼文屬性
    is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否置頂',
    is_promoted BOOLEAN DEFAULT FALSE COMMENT '是否為廣告',
    comments_disabled BOOLEAN DEFAULT FALSE COMMENT '是否禁止留言',
    
    -- 位置資訊
    location_name VARCHAR(200) COMMENT '地點名稱',
    location_id VARCHAR(100) COMMENT '地點 ID',
    latitude DECIMAL(10, 8) COMMENT '緯度',
    longitude DECIMAL(11, 8) COMMENT '經度',
    
    -- 標籤與提及
    hashtags TEXT COMMENT '標籤列表 (用逗號分隔)',
    mentions TEXT COMMENT '提及的使用者列表 (用逗號分隔)',
    
    -- 時間資訊
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬蟲收集此資料的時間',
    created_at DATETIME COMMENT '貼文發布時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    expires_at DATETIME COMMENT '過期時間（限時動態）',
    
    -- 連結
    post_url TEXT COMMENT '貼文連結',
    
    -- 原始資料
    raw_data LONGTEXT COMMENT '完整原始 JSON 資料（字串格式），保留所有從 Apify Actor 取得的資料',
    
    -- 索引
    UNIQUE KEY unique_platform_post (platform, post_id),
    INDEX idx_platform (platform),
    INDEX idx_author (author_id),
    INDEX idx_content_type (content_type),
    INDEX idx_create_time (create_time),
    INDEX idx_created (created_at),
    INDEX idx_like_count (like_count),
    INDEX idx_view_count (view_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通用社群媒體貼文表';

-- ============================================================================
-- 3. 貼文差異暫存表 (social_posts_diff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_posts_diff (
    platform VARCHAR(20),
    post_id VARCHAR(100),
    INDEX idx_post (platform, post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='貼文差異暫存表';

-- ============================================================================
-- 4. 限時動態資料表 (social_stories)
-- 統一儲存所有平台的限時動態 (如果支援)
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_stories (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL COMMENT '平台類型',
    post_id VARCHAR(100) NOT NULL COMMENT 'Story ID',
    
    -- 作者資訊
    author_id VARCHAR(100) COMMENT '作者 ID',
    author_username VARCHAR(100) COMMENT '作者名稱',
    author_display_name VARCHAR(200) COMMENT '作者顯示名稱',
    
    -- 媒體資訊
    media_type VARCHAR(20) COMMENT '媒體類型 (image, video)',
    video_url TEXT COMMENT '影片 URL',
    image_url TEXT COMMENT '圖片 URL',
    thumbnail_url TEXT COMMENT '縮圖 URL',
    
    -- 時間資訊
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬蟲收集此資料的時間',
    created_at DATETIME COMMENT '限時動態發布時間',
    expires_at DATETIME COMMENT '過期時間（24小時後）',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    
    -- 原始資料
    raw_data LONGTEXT COMMENT '完整原始 JSON 資料（字串格式），保留所有從 Apify Actor 取得的資料',
    
    -- 索引
    UNIQUE KEY unique_platform_story (platform, post_id),
    INDEX idx_platform (platform),
    INDEX idx_author (author_id),
    INDEX idx_create_time (create_time),
    INDEX idx_created (created_at),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通用社群媒體限時動態表';

-- ============================================================================
-- 5. 限時動態差異暫存表 (social_stories_diff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_stories_diff (
    platform VARCHAR(20),
    post_id VARCHAR(100),
    INDEX idx_story (platform, post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限時動態差異暫存表';

-- ============================================================================
-- 6. 平台設定表 (platform_config)
-- 儲存各平台的設定參數
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL UNIQUE COMMENT '平台類型',
    api_token VARCHAR(200) COMMENT 'API Token',
    actor_id_profile VARCHAR(100) COMMENT 'Profile Scraper Actor ID',
    actor_id_post VARCHAR(100) COMMENT 'Post Scraper Actor ID',
    actor_id_story VARCHAR(100) COMMENT 'Story Scraper Actor ID',
    is_enabled BOOLEAN DEFAULT TRUE COMMENT '是否啟用',
    post_limit INT DEFAULT 50 COMMENT '預設貼文抓取數量',
    story_limit INT DEFAULT NULL COMMENT '預設限時動態抓取數量',
    download_media BOOLEAN DEFAULT TRUE COMMENT '是否下載媒體',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台設定表';

-- 插入預設平台設定
INSERT INTO platform_config (platform, is_enabled) VALUES
('instagram', TRUE),
('facebook', TRUE),
('twitter', TRUE),
('threads', TRUE)
ON DUPLICATE KEY UPDATE platform=platform;

-- ============================================================================
-- 7. 收集歷史記錄表 (collection_history)
-- 記錄每次收集任務的執行狀況
-- ============================================================================
CREATE TABLE IF NOT EXISTS collection_history (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL COMMENT '平台類型',
    username VARCHAR(100) NOT NULL COMMENT '使用者名稱',
    success BOOLEAN DEFAULT FALSE COMMENT '是否成功',
    post_count INT DEFAULT 0 COMMENT '收集的貼文數',
    story_count INT DEFAULT 0 COMMENT '收集的限時動態數',
    error_message TEXT COMMENT '錯誤訊息',
    started_at DATETIME COMMENT '開始時間',
    finished_at DATETIME COMMENT '完成時間',
    duration_seconds INT COMMENT '執行時長（秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
    
    INDEX idx_platform (platform),
    INDEX idx_username (username),
    INDEX idx_success (success),
    INDEX idx_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收集歷史記錄表';

-- ============================================================================
-- 8. Hashtag 貼文資料表 (social_hashtag_posts)
-- 儲存透過 hashtag 收集的貼文資料
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_hashtag_posts (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主鍵',
    platform VARCHAR(20) NOT NULL COMMENT '平台類型',
    hashtag VARCHAR(200) NOT NULL COMMENT '收集的 hashtag（不含 # 符號）',
    post_id VARCHAR(100) NOT NULL COMMENT '貼文 ID',
    content_type VARCHAR(20) COMMENT '內容類型 (post, tweet, reel, thread)',
    
    -- 作者資訊
    author_id VARCHAR(100) COMMENT '作者 ID',
    author_username VARCHAR(100) COMMENT '作者名稱',
    author_display_name VARCHAR(200) COMMENT '作者顯示名稱',
    
    -- 內容資訊
    text TEXT COMMENT '文字內容',
    title TEXT COMMENT '標題',
    language VARCHAR(10) COMMENT '語言',
    
    -- 媒體資訊
    media_count INT DEFAULT 0 COMMENT '媒體數量',
    primary_media_type VARCHAR(20) COMMENT '主要媒體類型 (image, video)',
    primary_media_url TEXT COMMENT '主要媒體 URL',
    sub_image_url TEXT COMMENT '子圖片 URL 列表 (用逗號分隔)',
    sub_video_url TEXT COMMENT '子影片 URL 列表 (用逗號分隔)',
    sub_thumbnail_url TEXT COMMENT '子縮圖 URL 列表 (用逗號分隔)',
    
    -- 互動數據
    like_count INT DEFAULT 0 COMMENT '按讚數',
    comment_count INT DEFAULT 0 COMMENT '留言數',
    share_count INT DEFAULT 0 COMMENT '分享數',
    view_count INT DEFAULT 0 COMMENT '觀看數',
    bookmark_count INT DEFAULT 0 COMMENT '收藏數',
    
    -- 貼文屬性
    is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否置頂',
    is_promoted BOOLEAN DEFAULT FALSE COMMENT '是否為廣告',
    comments_disabled BOOLEAN DEFAULT FALSE COMMENT '是否禁止留言',
    
    -- 位置資訊
    location_name VARCHAR(200) COMMENT '地點名稱',
    location_id VARCHAR(100) COMMENT '地點 ID',
    latitude DECIMAL(10, 8) COMMENT '緯度',
    longitude DECIMAL(11, 8) COMMENT '經度',
    
    -- 標籤與提及
    hashtags TEXT COMMENT '標籤列表 (用逗號分隔)',
    mentions TEXT COMMENT '提及的使用者列表 (用逗號分隔)',
    
    -- 時間資訊
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬蟲收集此資料的時間',
    created_at DATETIME COMMENT '貼文發布時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    expires_at DATETIME COMMENT '過期時間（限時動態）',
    
    -- 連結
    post_url TEXT COMMENT '貼文連結',
    
    -- 原始資料
    raw_data LONGTEXT COMMENT '完整原始 JSON 資料（字串格式），保留所有從 Apify Actor 取得的資料',
    
    -- 索引
    UNIQUE KEY unique_hashtag_post (platform, hashtag, post_id),
    INDEX idx_platform (platform),
    INDEX idx_hashtag (hashtag),
    INDEX idx_author (author_id),
    INDEX idx_content_type (content_type),
    INDEX idx_create_time (create_time),
    INDEX idx_created (created_at),
    INDEX idx_like_count (like_count),
    INDEX idx_view_count (view_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hashtag 貼文資料表';

-- ============================================================================
-- 9. Hashtag 貼文差異暫存表 (social_hashtag_posts_diff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS social_hashtag_posts_diff (
    platform VARCHAR(20),
    hashtag VARCHAR(200),
    post_id VARCHAR(100),
    INDEX idx_hashtag_post (platform, hashtag, post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hashtag 貼文差異暫存表';

-- ============================================================================
-- 初始化完成
-- ============================================================================
SELECT '通用社群媒體資料收集系統 - 資料表初始化完成！' AS message;
SELECT CONCAT('支援平台: ', GROUP_CONCAT(platform SEPARATOR ', ')) AS supported_platforms 
FROM platform_config WHERE is_enabled = TRUE;

