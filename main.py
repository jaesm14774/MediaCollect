"""
通用社群媒體資料收集系統 - 主程式
支援多平台: Instagram, Facebook, Twitter(X), Threads 等
"""
import sys
import os
import time
import random
import pandas as pd
import asyncio
from typing import List, Optional
from multiprocessing import Pool, cpu_count
from functools import partial

# 導入核心模組
from core.factory import CollectorFactory, register_all_collectors
from core.database_manager import create_database_manager_from_config
from core.data_models import CollectionResult, HashtagCollectionResult

# 導入設定
from config.platform_config import (
    APIFY_TOKEN, MEDIA_FOLDER_PATH, SQL_CONFIGURE_PATH, DISCORD_PATH,
    PLATFORM_SETTINGS, MIN_DELAY, MAX_DELAY, BATCH_SIZE, 
    BATCH_DELAY_MIN, BATCH_DELAY_MAX, get_platform_setting
)
from config.accounts_loader import (
    load_accounts_from_file, get_accounts_for_platform, 
    get_all_enabled_accounts, validate_accounts_file
)

# 導入通知模組
from lib.discord_notify import notify

# 導入日誌模組
from lib.logger import get_logger

# 建立全域 logger
logger = get_logger('MediaCollect')


# =========================================================================
# 多進程輔助函數（必須在類別外部，才能被 pickle 序列化）
# =========================================================================

def _multiprocess_collect_single_user(args):
    """
    在獨立進程中收集單一使用者的資料
    
    這個函數必須在類別外部定義，才能被 multiprocessing.Pool 序列化
    
    參數:
        args: (platform, username) 元組
    
    返回:
        包含收集結果的字典
    """
    platform, username = args
    
    try:
        # 在子進程中重新註冊收集器
        register_all_collectors()
        
        # 建立新的 crawler 實例
        crawler = SocialMediaCrawler()
        
        try:
            # 執行收集
            result = crawler.collect_user(platform, username)
            
            return {
                'username': username,
                'success': result.success,
                'error': result.error_message,
                'post_count': len(result.posts) if result.success else 0,
                'story_count': len(result.stories) if result.success else 0
            }
        finally:
            # 確保關閉資源
            crawler.close()
    
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"[多進程] 處理 {username} 時發生錯誤: {error_detail}")
        
        return {
            'username': username,
            'success': False,
            'error': error_detail,
            'post_count': 0,
            'story_count': 0
        }


class SocialMediaCrawler:
    """
    通用社群媒體資料收集器
    
    功能:
    - 自動選擇平台收集器
    - 批次處理多個使用者
    - 資料庫儲存
    - 錯誤通知
    """
    
    def __init__(self):
        """初始化收集器"""
        # 註冊所有平台收集器
        register_all_collectors()
        
        # 建立資料庫管理器
        self.db = create_database_manager_from_config(SQL_CONFIGURE_PATH)
        
        # 載入 Discord 通知設定
        # 優先使用環境變數
        import os
        self.discord_token = os.getenv('DISCORD_WEBHOOK_URL')
        
        # 如果環境變數沒有，嘗試從檔案讀取（向下相容）
        if not self.discord_token:
            try:
                if os.path.exists(DISCORD_PATH):
                    notify_config = pd.read_csv(DISCORD_PATH, encoding='utf_8_sig', index_col='name')
                    self.discord_token = notify_config.loc['程式bug權杖', 'token']
            except:
                self.discord_token = None
                print("[警告] 無法載入 Discord 通知設定")
    
    def collect_hashtag(
        self,
        platform: str,
        hashtag,
        results_type: str = "posts",
        results_limit: int = 50
    ) -> HashtagCollectionResult:
        """
        收集指定 hashtag 的資料
        
        參數:
            platform: 平台名稱 (instagram, ...)
            hashtag: hashtag（可含或不含 # 符號）
                    - 單個 hashtag: str，例如 "elonmusk"
                    - 多個 hashtag: List[str]，例如 ["elonmusk", "travel"]
                    - 逗號分隔字串: str，例如 "elonmusk,travel,food"
            results_type: 結果類型 ("posts" 或 "reels")
            results_limit: 結果數量限制
        
        返回:
            HashtagCollectionResult 物件
        """
        try:
            # 建立 hashtag 收集器
            logger.info(f"{'='*60}")
            # 處理 hashtag 顯示
            if isinstance(hashtag, str):
                if ',' in hashtag:
                    hashtag_display = ', '.join(['#' + h.strip().lstrip('#') for h in hashtag.split(',') if h.strip()])
                else:
                    hashtag_display = '#' + hashtag.lstrip('#')
            elif isinstance(hashtag, list):
                hashtag_display = ', '.join(['#' + str(h).lstrip('#') for h in hashtag])
            else:
                hashtag_display = '#' + str(hashtag).lstrip('#')
            
            logger.info(f"[{platform.upper()}] 開始收集 hashtag: {hashtag_display}")
            logger.info(f"{'='*60}")
            
            collector = CollectorFactory.create_hashtag_collector(
                platform=platform,
                hashtag=hashtag,
                api_token=APIFY_TOKEN,
                results_type=results_type,
                results_limit=results_limit
            )
            
            if not collector:
                error_msg = f"無法建立 {platform} Hashtag 收集器"
                logger.error(error_msg)
                from core.data_models import PlatformType, HashtagCollectionResult
                return HashtagCollectionResult(
                    platform=PlatformType(platform.lower()),
                    hashtag=hashtag.lstrip('#'),
                    success=False,
                    error_message=error_msg
                )
            
            # 執行收集
            result = collector.collect_hashtag()
            
            # 下載媒體檔案
            if result.success and result.posts:
                logger.info(f"[{platform.upper()}] 開始下載 {len(result.posts)} 個貼文的媒體檔案...")
                for post in result.posts:
                    collector.download_media(post, MEDIA_FOLDER_PATH)
                logger.info(f"[{platform.upper()}] 媒體下載完成")
            
            # 儲存到資料庫
            if result.success:
                self.db.save_hashtag_collection_result(result)
            
            # 儲存收集歷史記錄
            self.db.save_collection_history(
                platform=platform,
                username=f"hashtag_{result.hashtag}",  # 使用 hashtag 作為 username
                success=result.success,
                post_count=len(result.posts),
                story_count=0,  # hashtag 收集沒有限時動態
                error_message=result.error_message,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration_seconds=result.duration_seconds
            )
            
            logger.info(f"\n{result}")
            return result
        
        except Exception as e:
            import traceback
            error_msg = f"Hashtag 收集失敗: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[錯誤] {error_msg}")
            
            # 發送錯誤通知
            if self.discord_token:
                notify(self.discord_token, f"[{platform.upper()}] Hashtag 收集失敗 - #{hashtag}:\n{str(e)}")
            
            # 處理 hashtag 字串以保存歷史記錄
            if isinstance(hashtag, str):
                if ',' in hashtag:
                    hashtag_str = ','.join([h.strip().lstrip('#') for h in hashtag.split(',') if h.strip()])
                else:
                    hashtag_str = hashtag.lstrip('#')
            elif isinstance(hashtag, list):
                hashtag_str = ','.join([str(h).lstrip('#') for h in hashtag])
            else:
                hashtag_str = str(hashtag).lstrip('#')
            
            # 儲存失敗的收集歷史記錄
            try:
                self.db.save_collection_history(
                    platform=platform,
                    username=f"hashtag_{hashtag_str}",
                    success=False,
                    post_count=0,
                    story_count=0,
                    error_message=error_msg,
                    started_at=None,
                    finished_at=None,
                    duration_seconds=None
                )
            except:
                logger.error("無法儲存收集歷史記錄")
            
            from core.data_models import PlatformType, HashtagCollectionResult
            return HashtagCollectionResult(
                platform=PlatformType(platform.lower()),
                hashtag=hashtag_str,
                success=False,
                error_message=error_msg
            )
    
    def collect_user(
        self, 
        platform: str, 
        username: str,
        post_limit: Optional[int] = None,
        story_limit: Optional[int] = None,
        photo_limit: Optional[int] = None,
        download_media: Optional[bool] = None,
        posts_newer_than: Optional[str] = None,
        posts_older_than: Optional[str] = None,
        caption_text: Optional[bool] = None
    ) -> CollectionResult:
        """
        收集指定使用者的資料
        
        參數:
            platform: 平台名稱 (instagram, facebook, twitter, threads)
            username: 使用者名稱
            post_limit: 貼文數量限制 (None 使用設定檔的值)
            story_limit: 限時動態數量限制
            photo_limit: 照片數量限制 (僅適用於 Facebook)
            download_media: 是否下載媒體
            posts_newer_than: 只抓取此日期之後的貼文 (僅適用於 Facebook)
            posts_older_than: 只抓取此日期之前的貼文 (僅適用於 Facebook)
            caption_text: 是否提取影片字幕 (僅適用於 Facebook)
        
        返回:
            CollectionResult 物件
        """
        try:
            # 取得平台設定
            if post_limit is None:
                post_limit = get_platform_setting(platform, 'post_limit', 50)
            if story_limit is None:
                story_limit = get_platform_setting(platform, 'story_limit')
            if photo_limit is None:
                photo_limit = get_platform_setting(platform, 'photo_limit')
            if download_media is None:
                download_media = get_platform_setting(platform, 'download_media', True)
            if posts_newer_than is None:
                posts_newer_than = get_platform_setting(platform, 'posts_newer_than')
            if posts_older_than is None:
                posts_older_than = get_platform_setting(platform, 'posts_older_than')
            if caption_text is None:
                caption_text = get_platform_setting(platform, 'caption_text', False)
            
            # 建立收集器
            logger.info(f"{'='*60}")
            logger.info(f"[{platform.upper()}] 開始處理使用者: {username}")
            logger.info(f"{'='*60}")
            
            collector = CollectorFactory.create_collector(
                platform=platform,
                username=username,
                api_token=APIFY_TOKEN
            )
            
            if not collector:
                error_msg = f"無法建立 {platform} 收集器"
                logger.error(error_msg)
                return CollectionResult(
                    platform=platform,
                    success=False,
                    error_message=error_msg
                )
            
            # 執行收集
            result = collector.collect_all(
                post_limit=post_limit,
                story_limit=story_limit,
                include_stories=(story_limit is not None or story_limit != 0),
                photo_limit=photo_limit,
                include_photos=(photo_limit is not None and photo_limit > 0),
                posts_newer_than=posts_newer_than,
                posts_older_than=posts_older_than,
                caption_text=caption_text
            )
            
            # 儲存到資料庫
            if result.success:
                self.db.save_collection_result(result)
                
                # 下載媒體
                if download_media:
                    self._download_media_for_result(result, collector)
            
            # 儲存收集歷史記錄
            self.db.save_collection_history(
                platform=platform,
                username=username,
                success=result.success,
                post_count=len(result.posts),
                story_count=len(result.stories),
                error_message=result.error_message,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration_seconds=result.duration_seconds
            )
            
            logger.info(f"\n{result}")
            return result
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[錯誤] {error_msg}")
            
            # 發送錯誤通知
            if self.discord_token:
                notify(self.discord_token, f"[{platform.upper()}] 收集失敗 - {username}:\n{str(e)}")
            
            # 儲存失敗記錄到歷史
            try:
                self.db.save_collection_history(
                    platform=platform,
                    username=username,
                    success=False,
                    post_count=0,
                    story_count=0,
                    error_message=error_msg,
                    started_at=None,
                    finished_at=None,
                    duration_seconds=None
                )
            except:
                logger.error("無法儲存收集歷史記錄")
            
            return CollectionResult(
                platform=platform,
                success=False,
                error_message=error_msg
            )
    
    def _download_media_for_result(self, result: CollectionResult, collector):
        """下載收集結果中的媒體檔案"""
        try:
            logger.info(f"[{result.platform.value}] 開始下載媒體檔案...")
            
            # 下載貼文媒體
            for post in result.posts:
                collector.download_media(post, MEDIA_FOLDER_PATH)
            
            # 下載限時動態媒體
            for story in result.stories:
                collector.download_media(story, MEDIA_FOLDER_PATH)
            
            logger.info(f"[{result.platform.value}] 媒體下載完成")
        
        except Exception as e:
            logger.error(f"[{result.platform.value}] 下載媒體失敗: {e}")
    
    def batch_collect(
        self, 
        platform: str, 
        username_list: Optional[List[str]] = None
    ):
        """
        批次收集多個使用者
        
        參數:
            platform: 平台名稱
            username_list: 使用者名稱列表 (None 表示從資料庫讀取)
        """
        # 如果沒有提供使用者列表，從資料庫讀取
        if username_list is None:
            users_df = self.db.get_active_users(platform=platform)
            username_list = users_df['username'].tolist()
        
        if not username_list:
            logger.warning(f"[{platform}] 沒有要處理的使用者")
            return
        
        # 隨機打亂順序（避免規律性）
        import numpy as np
        username_list = np.random.choice(
            username_list, 
            size=len(username_list), 
            replace=False
        ).tolist()
        
        logger.info(f"{'='*60}")
        logger.info(f"[{platform.upper()}] 批次收集模式")
        logger.info(f"使用者數量: {len(username_list)}")
        logger.info(f"{'='*60}")
        
        # 批次處理
        for i, username in enumerate(username_list):
            # 批次延遲
            if i % BATCH_SIZE == 0 and i != 0:
                delay = random.randint(BATCH_DELAY_MIN, BATCH_DELAY_MAX)
                logger.info(f"[批次延遲] 等待 {delay} 秒...")
                time.sleep(delay)
            
            # 收集資料
            try:
                result = self.collect_user(platform, username)
                
                # 使用者間延遲
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                logger.info(f"[延遲] 等待 {delay} 秒...")
                time.sleep(delay)
            
            except Exception as e:
                logger.error(f"處理 {username} 時發生錯誤: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 錯誤 - {username}: {e}")
                continue
        
        logger.info(f"{'='*60}")
        logger.info(f"[{platform.upper()}] 批次收集完成")
        logger.info(f"{'='*60}")
    
    async def async_collect_user(
        self, 
        platform: str, 
        username: str,
        post_limit: Optional[int] = None,
        story_limit: Optional[int] = None,
        download_media: Optional[bool] = None
    ) -> CollectionResult:
        """
        異步收集指定使用者的資料
        
        參數:
            platform: 平台名稱 (instagram, facebook, twitter, threads)
            username: 使用者名稱
            post_limit: 貼文數量限制 (None 使用設定檔的值)
            story_limit: 限時動態數量限制
            download_media: 是否下載媒體
        
        返回:
            CollectionResult 物件
        """
        try:
            # 取得平台設定
            if post_limit is None:
                post_limit = get_platform_setting(platform, 'post_limit', 50)
            if story_limit is None:
                story_limit = get_platform_setting(platform, 'story_limit')
            if download_media is None:
                download_media = get_platform_setting(platform, 'download_media', True)
            
            # 建立收集器
            logger.info(f"{'='*60}")
            logger.info(f"[{platform.upper()}] 開始處理使用者: {username}")
            logger.info(f"{'='*60}")
            
            collector = CollectorFactory.create_collector(
                platform=platform,
                username=username,
                api_token=APIFY_TOKEN
            )
            
            if not collector:
                error_msg = f"無法建立 {platform} 收集器"
                logger.error(error_msg)
                return CollectionResult(
                    platform=platform,
                    success=False,
                    error_message=error_msg
                )
            
            # 執行異步收集
            result = await collector.collect_all_async(
                post_limit=post_limit,
                story_limit=story_limit,
                include_stories=(story_limit is not None or story_limit != 0)
            )
            
            # 儲存到資料庫
            if result.success:
                self.db.save_collection_result(result)
                
                # 下載媒體
                if download_media:
                    self._download_media_for_result(result, collector)
            
            # 儲存收集歷史記錄
            self.db.save_collection_history(
                platform=platform,
                username=username,
                success=result.success,
                post_count=len(result.posts),
                story_count=len(result.stories),
                error_message=result.error_message,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration_seconds=result.duration_seconds
            )
            
            logger.info(f"\n{result}")
            return result
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[錯誤] {error_msg}")
            
            # 發送錯誤通知
            if self.discord_token:
                notify(self.discord_token, f"[{platform.upper()}] 收集失敗 - {username}:\n{str(e)}")
            
            # 儲存失敗記錄到歷史
            try:
                self.db.save_collection_history(
                    platform=platform,
                    username=username,
                    success=False,
                    post_count=0,
                    story_count=0,
                    error_message=error_msg,
                    started_at=None,
                    finished_at=None,
                    duration_seconds=None
                )
            except:
                logger.error("無法儲存收集歷史記錄")
            
            return CollectionResult(
                platform=platform,
                success=False,
                error_message=error_msg
            )
    
    async def async_batch_collect(
        self, 
        platform: str, 
        username_list: Optional[List[str]] = None,
        concurrent_limit: int = 3
    ):
        """
        異步批次收集多個使用者（並發執行）
        
        參數:
            platform: 平台名稱
            username_list: 使用者名稱列表 (None 表示從資料庫讀取)
            concurrent_limit: 同時並發的任務數量（預設3個）
        """
        # 如果沒有提供使用者列表，從資料庫讀取
        if username_list is None:
            users_df = self.db.get_active_users(platform=platform)
            username_list = users_df['username'].tolist()
        
        if not username_list:
            logger.warning(f"[{platform}] 沒有要處理的使用者")
            return
        
        # 隨機打亂順序（避免規律性）
        import numpy as np
        username_list = np.random.choice(
            username_list, 
            size=len(username_list), 
            replace=False
        ).tolist()
        
        logger.info(f"{'='*60}")
        logger.info(f"[{platform.upper()}] 異步批次收集模式")
        logger.info(f"使用者數量: {len(username_list)}")
        logger.info(f"並發限制: {concurrent_limit} 個同時任務")
        logger.info(f"{'='*60}")
        
        # 使用 Semaphore 限制並發數量
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def collect_with_semaphore(username: str):
            """使用信號量控制並發的收集任務"""
            async with semaphore:
                try:
                    # 加入隨機延遲，避免同時發送請求
                    delay = random.uniform(1, 3)
                    await asyncio.sleep(delay)
                    
                    result = await self.async_collect_user(platform, username)
                    
                    # 使用者間延遲
                    delay = random.randint(MIN_DELAY, MAX_DELAY)
                    logger.info(f"[延遲] 等待 {delay} 秒...")
                    await asyncio.sleep(delay)
                    
                    return result
                except Exception as e:
                    logger.error(f"處理 {username} 時發生錯誤: {e}")
                    if self.discord_token:
                        notify(self.discord_token, f"[{platform}] 錯誤 - {username}: {e}")
                    return None
        
        # 建立所有任務
        tasks = [collect_with_semaphore(username) for username in username_list]
        
        # 並發執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 統計結果
        success_count = sum(1 for r in results if r and isinstance(r, CollectionResult) and r.success)
        fail_count = len(results) - success_count
        
        logger.info(f"{'='*60}")
        logger.info(f"[{platform.upper()}] 異步批次收集完成")
        logger.info(f"成功: {success_count}, 失敗: {fail_count}")
        logger.info(f"{'='*60}")
    
    def multiprocess_batch_collect(
        self, 
        platform: str, 
        username_list: Optional[List[str]] = None,
        num_processes: Optional[int] = None
    ):
        """
        多進程批次收集多個使用者（真正的平行處理）
        
        適合處理 Apify Actor 阻塞等待的情況（如時間篩選導致重啟）
        
        參數:
            platform: 平台名稱
            username_list: 使用者名稱列表 (None 表示從資料庫讀取)
            num_processes: 進程數量（None 使用 CPU 核心數）
        """
        # 如果沒有提供使用者列表，從資料庫讀取
        if username_list is None:
            users_df = self.db.get_active_users(platform=platform)
            username_list = users_df['username'].tolist()
        
        if not username_list:
            logger.warning(f"[{platform}] 沒有要處理的使用者")
            return
        
        # 隨機打亂順序（避免規律性）
        import numpy as np
        username_list = np.random.choice(
            username_list, 
            size=len(username_list), 
            replace=False
        ).tolist()
        
        # 決定進程數量
        if num_processes is None:
            num_processes = min(cpu_count(), len(username_list))
        
        logger.info(f"{'='*60}")
        logger.info(f"[{platform.upper()}] 多進程批次收集模式")
        logger.info(f"使用者數量: {len(username_list)}")
        logger.info(f"進程數量: {num_processes} (CPU 核心數: {cpu_count()})")
        logger.info(f"{'='*60}")
        
        # 記錄開始時間
        start_time = time.time()
        
        # 準備參數列表（每個元素是 (platform, username) 元組）
        task_args = [(platform, username) for username in username_list]
        
        # 使用多進程池處理
        try:
            with Pool(processes=num_processes) as pool:
                # 使用全域函數 _multiprocess_collect_single_user
                results = pool.map(_multiprocess_collect_single_user, task_args)
            
            # 統計結果
            success_count = sum(1 for r in results if r['success'])
            fail_count = len(results) - success_count
            total_posts = sum(r.get('post_count', 0) for r in results)
            total_stories = sum(r.get('story_count', 0) for r in results)
            
            # 計算執行時間
            elapsed_time = time.time() - start_time
            
            logger.info(f"{'='*60}")
            logger.info(f"[{platform.upper()}] 多進程批次收集完成")
            logger.info(f"成功: {success_count}, 失敗: {fail_count}")
            logger.info(f"總貼文數: {total_posts}, 總限時動態數: {total_stories}")
            logger.info(f"總執行時間: {elapsed_time:.2f} 秒")
            logger.info(f"平均每個使用者: {elapsed_time/len(username_list):.2f} 秒")
            logger.info(f"{'='*60}")
            
            # 顯示失敗的使用者
            if fail_count > 0:
                logger.warning("失敗的使用者:")
                for r in results:
                    if not r['success']:
                        error_preview = r['error'][:200] if r['error'] else 'Unknown error'
                        logger.warning(f"  - {r['username']}: {error_preview}...")
        
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            logger.error(f"[多進程] 批次收集失敗: {error_detail}")
            if self.discord_token:
                notify(self.discord_token, f"[{platform}] 多進程批次收集失敗: {e}")
    
    def multiprocess_collect_from_accounts_file(
        self, 
        accounts_file: str = 'accounts.txt',
        num_processes: Optional[int] = None
    ):
        """
        從帳號配置檔多進程收集資料
        
        參數:
            accounts_file: 帳號配置檔路徑
            num_processes: 進程數量（None 使用 CPU 核心數）
        """
        # 驗證配置檔
        if not validate_accounts_file(accounts_file):
            logger.error(f"帳號配置檔無效或不存在: {accounts_file}")
            logger.info(f"請複製 accounts.example.txt 為 accounts.txt 並填入帳號")
            return
        
        # 載入所有帳號
        all_accounts = get_all_enabled_accounts(accounts_file)
        
        if not all_accounts:
            logger.warning("配置檔中沒有任何帳號")
            return
        
        logger.info("="*60)
        logger.info("每日收集模式（多進程）- 從配置檔載入帳號")
        logger.info("="*60)
        
        # 逐平台收集
        for platform, username_list in all_accounts.items():
            # 檢查平台是否啟用
            if not PLATFORM_SETTINGS.get(platform, {}).get('enabled', False):
                logger.info(f"[跳過] {platform.upper()} 平台未啟用")
                continue
            
            if not username_list:
                logger.info(f"[跳過] {platform.upper()} 沒有設定帳號")
                continue
            
            try:
                logger.info(f"{'='*60}")
                logger.info(f"[{platform.upper()}] 開始多進程批次收集")
                logger.info(f"帳號數量: {len(username_list)}")
                logger.info(f"{'='*60}")
                
                # 使用多進程批次收集
                self.multiprocess_batch_collect(platform, username_list, num_processes)
                
                logger.info(f"[{platform.upper()}] 完成收集")
            
            except Exception as e:
                logger.error(f"{platform} 平台收集失敗: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 平台收集失敗: {e}")
        
        logger.info("="*60)
        logger.info("每日收集完成（多進程）")
        logger.info("="*60)
    
    def collect_all_platforms(self):
        """收集所有啟用平台的資料（從資料庫讀取使用者）"""
        for platform, settings in PLATFORM_SETTINGS.items():
            if not settings.get('enabled', False):
                continue
            
            try:
                self.batch_collect(platform)
            except Exception as e:
                logger.error(f"{platform} 平台收集失敗: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 平台收集失敗: {e}")
    
    def collect_from_accounts_file(self, accounts_file: str = 'accounts.txt'):
        """
        從帳號配置檔收集資料
        
        參數:
            accounts_file: 帳號配置檔路徑
        """
        # 驗證配置檔
        if not validate_accounts_file(accounts_file):
            logger.error(f"帳號配置檔無效或不存在: {accounts_file}")
            logger.info(f"請複製 accounts.example.txt 為 accounts.txt 並填入帳號")
            return
        
        # 載入所有帳號
        all_accounts = get_all_enabled_accounts(accounts_file)
        
        if not all_accounts:
            logger.warning("配置檔中沒有任何帳號")
            return
        
        logger.info("="*60)
        logger.info("每日收集模式 - 從配置檔載入帳號")
        logger.info("="*60)
        
        # 逐平台收集
        for platform, username_list in all_accounts.items():
            # 檢查平台是否啟用
            if not PLATFORM_SETTINGS.get(platform, {}).get('enabled', False):
                logger.info(f"[跳過] {platform.upper()} 平台未啟用")
                continue
            
            if not username_list:
                logger.info(f"[跳過] {platform.upper()} 沒有設定帳號")
                continue
            
            try:
                logger.info(f"{'='*60}")
                logger.info(f"[{platform.upper()}] 開始批次收集")
                logger.info(f"帳號數量: {len(username_list)}")
                logger.info(f"{'='*60}")
                
                # 使用 batch_collect，但提供帳號列表
                self.batch_collect(platform, username_list)
                
                logger.info(f"[{platform.upper()}] 完成收集")
            
            except Exception as e:
                logger.error(f"{platform} 平台收集失敗: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 平台收集失敗: {e}")
        
        logger.info("="*60)
        logger.info("每日收集完成")
        logger.info("="*60)
    
    async def async_collect_from_accounts_file(
        self, 
        accounts_file: str = 'accounts.txt',
        concurrent_limit: int = 3
    ):
        """
        從帳號配置檔異步收集資料
        
        參數:
            accounts_file: 帳號配置檔路徑
            concurrent_limit: 同時並發的任務數量（預設3個）
        """
        # 驗證配置檔
        if not validate_accounts_file(accounts_file):
            logger.error(f"帳號配置檔無效或不存在: {accounts_file}")
            logger.info(f"請複製 accounts.example.txt 為 accounts.txt 並填入帳號")
            return
        
        # 載入所有帳號
        all_accounts = get_all_enabled_accounts(accounts_file)
        
        if not all_accounts:
            logger.warning("配置檔中沒有任何帳號")
            return
        
        logger.info("="*60)
        logger.info("每日收集模式（異步）- 從配置檔載入帳號")
        logger.info("="*60)
        
        # 逐平台收集
        for platform, username_list in all_accounts.items():
            # 檢查平台是否啟用
            if not PLATFORM_SETTINGS.get(platform, {}).get('enabled', False):
                logger.info(f"[跳過] {platform.upper()} 平台未啟用")
                continue
            
            if not username_list:
                logger.info(f"[跳過] {platform.upper()} 沒有設定帳號")
                continue
            
            try:
                logger.info(f"{'='*60}")
                logger.info(f"[{platform.upper()}] 開始異步批次收集")
                logger.info(f"帳號數量: {len(username_list)}")
                logger.info(f"{'='*60}")
                
                # 使用異步批次收集
                await self.async_batch_collect(platform, username_list, concurrent_limit)
                
                logger.info(f"[{platform.upper()}] 完成收集")
            
            except Exception as e:
                logger.error(f"{platform} 平台收集失敗: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 平台收集失敗: {e}")
        
        logger.info("="*60)
        logger.info("每日收集完成（異步）")
        logger.info("="*60)
    
    def close(self):
        """關閉資源"""
        self.db.close()
        logger.info("已關閉所有資源連接")


def interactive_mode():
    """互動式測試模式"""
    logger.info("="*60)
    logger.info("通用社群媒體資料收集系統 - 互動式測試")
    logger.info("="*60)
    
    # 選擇模式
    print("\n請選擇收集模式:")
    print("  1. 使用者收集")
    print("  2. Hashtag 收集")
    
    try:
        mode_choice = int(input(">>> "))
        if mode_choice not in [1, 2]:
            logger.error("無效的選擇")
            return
    except:
        logger.error("無效的輸入")
        return
    
    if mode_choice == 1:
        # 使用者收集模式
        # 顯示支援的平台
        supported_platforms = CollectorFactory.get_supported_platforms()
        logger.info("\n支援的平台:")
        for i, platform in enumerate(supported_platforms, 1):
            logger.info(f"  {i}. {platform.upper()}")
        
        # 選擇平台
        print("\n請選擇平台 (輸入數字):")
        try:
            choice = int(input(">>> "))
            if choice < 1 or choice > len(supported_platforms):
                logger.error("無效的選擇")
                return
            platform = supported_platforms[choice - 1]
        except:
            logger.error("無效的輸入")
            return
        
        # 輸入使用者名稱
        print(f"\n請輸入 {platform.upper()} 使用者名稱:")
        username = input(">>> ").strip()
        
        if not username:
            logger.error("使用者名稱不能為空")
            return
        
        # 執行收集
        crawler = SocialMediaCrawler()
        try:
            result = crawler.collect_user(platform, username)
            logger.info("="*60)
            logger.info("收集結果:")
            logger.info("="*60)
            logger.info(str(result))
            logger.info("="*60)
        finally:
            crawler.close()
    
    elif mode_choice == 2:
        # Hashtag 收集模式
        # 顯示支援 hashtag 收集的平台
        supported_hashtag_platforms = CollectorFactory.get_supported_hashtag_platforms()
        if not supported_hashtag_platforms:
            logger.error("目前沒有平台支援 hashtag 收集")
            return
        
        logger.info("\n支援 Hashtag 收集的平台:")
        for i, platform in enumerate(supported_hashtag_platforms, 1):
            logger.info(f"  {i}. {platform.upper()}")
        
        # 選擇平台
        print("\n請選擇平台 (輸入數字):")
        try:
            choice = int(input(">>> "))
            if choice < 1 or choice > len(supported_hashtag_platforms):
                logger.error("無效的選擇")
                return
            platform = supported_hashtag_platforms[choice - 1]
        except:
            logger.error("無效的輸入")
            return
        
        # 輸入 hashtag
        print(f"\n請輸入 {platform.upper()} hashtag（可含或不含 # 符號）:")
        print("  提示: 支援單個或多個 hashtag（用逗號分隔）")
        print("  範例: elonmusk 或 elonmusk,travel,food")
        hashtag = input(">>> ").strip()
        
        if not hashtag:
            logger.error("Hashtag 不能為空")
            return
        
        # 輸入結果類型（僅限 Instagram）
        results_type = "posts"
        if platform == "instagram":
            print("\n請選擇結果類型:")
            print("  1. Posts (貼文)")
            print("  2. Reels (短影片)")
            try:
                type_choice = int(input(">>> "))
                if type_choice == 2:
                    results_type = "reels"
            except:
                pass
        
        # 輸入結果數量限制
        print("\n請輸入結果數量限制 (預設: 50):")
        try:
            results_limit_input = input(">>> ").strip()
            results_limit = int(results_limit_input) if results_limit_input else 50
        except:
            results_limit = 50
        
        # 執行收集
        crawler = SocialMediaCrawler()
        try:
            result = crawler.collect_hashtag(
                platform=platform, 
                hashtag=hashtag,
                results_type=results_type,
                results_limit=results_limit
            )
            logger.info("="*60)
            logger.info("收集結果:")
            logger.info("="*60)
            logger.info(str(result))
            logger.info("="*60)
        finally:
            crawler.close()


def main():
    """主程式入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='通用社群媒體資料收集系統',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 每日排程收集（從 accounts.txt 讀取帳號）
  python main.py --mode daily
  python main.py --mode daily --accounts-file my_accounts.txt
  
  # 每日排程收集（多進程模式，推薦！真正平行處理）
  python main.py --mode daily --multiprocess --num-processes 4
  
  # 每日排程收集（異步並發模式）
  python main.py --mode daily --async --concurrent-limit 5
  
  # 互動式測試
  python main.py --mode interactive
  
  # 單一使用者收集
  python main.py --mode single --platform instagram --username nasa
  
  # 單一使用者收集（加上時間篩選）
  python main.py --mode single --platform facebook --username nasa --posts-newer-than "2024-01-01" --posts-older-than "2024-12-31"
  python main.py --mode single --platform facebook --username nasa --posts-newer-than "1 month"
  
  # Hashtag 收集（單個）
  python main.py --mode hashtag --platform instagram --hashtag elonmusk
  
  # Hashtag 收集（多個，用逗號分隔）
  python main.py --mode hashtag --platform instagram --hashtag "elonmusk,travel,food"
  python main.py --mode hashtag --platform instagram --hashtag "elonmusk,travel,food" --results-type reels --results-limit 100
  
  # 批次收集（從資料庫讀取使用者）
  python main.py --mode batch --platform twitter
  python main.py --mode batch --platform instagram --multiprocess --num-processes 4
  python main.py --mode all
        """
    )
    parser.add_argument('--mode', 
                       choices=['daily', 'batch', 'single', 'hashtag', 'interactive', 'all'], 
                       default='interactive', 
                       help='執行模式:\n'
                            '  daily - 每日收集模式（從 accounts.txt 讀取）\n'
                            '  batch - 批次模式（從資料庫讀取）\n'
                            '  single - 單一使用者\n'
                            '  hashtag - Hashtag 收集\n'
                            '  interactive - 互動式\n'
                            '  all - 所有平台（從資料庫讀取）')
    parser.add_argument('--platform', type=str, help='平台名稱')
    parser.add_argument('--username', type=str, help='使用者名稱')
    parser.add_argument('--hashtag', type=str, help='Hashtag（可含或不含 # 符號）。支援單個或多個（用逗號分隔），例如: "elonmusk" 或 "elonmusk,travel,food"')
    parser.add_argument('--results-type', type=str, default='posts', 
                       choices=['posts', 'reels'],
                       help='Hashtag 收集的結果類型（預設: posts）')
    parser.add_argument('--results-limit', type=int, default=50,
                       help='Hashtag 收集的結果數量限制（預設: 50）')
    parser.add_argument('--post-limit', type=int, help='貼文數量限制')
    parser.add_argument('--story-limit', type=int, help='限時動態數量限制')
    parser.add_argument('--photo-limit', type=int, help='照片數量限制（僅適用於 Facebook）')
    parser.add_argument('--posts-newer-than', type=str, help='只抓取此日期之後的貼文 (格式: YYYY-MM-DD 或 "1 day", "2 months")')
    parser.add_argument('--posts-older-than', type=str, help='只抓取此日期之前的貼文 (格式: YYYY-MM-DD 或 "1 day", "2 months")')
    parser.add_argument('--caption-text', action='store_true', help='是否提取影片字幕（僅適用於 Facebook）')
    parser.add_argument('--accounts-file', type=str, default='accounts.txt',
                       help='帳號配置檔路徑（預設: accounts.txt）')
    parser.add_argument('--async', dest='use_async', action='store_true',
                       help='使用異步並發模式（適用於 daily 和 batch 模式）')
    parser.add_argument('--concurrent-limit', type=int, default=3,
                       help='異步模式下同時並發的任務數量（預設: 3）')
    parser.add_argument('--multiprocess', dest='use_multiprocess', action='store_true',
                       help='使用多進程平行處理模式（適合 Apify Actor 阻塞情況，適用於 daily 和 batch 模式）')
    parser.add_argument('--num-processes', type=int, default=None,
                       help='多進程模式下的進程數量（預設: CPU 核心數）')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        # 互動式模式
        interactive_mode()
    
    elif args.mode == 'daily':
        # 每日收集模式（從配置檔讀取帳號）
        crawler = SocialMediaCrawler()
        try:
            if args.use_multiprocess:
                # 多進程模式（推薦：適合 Apify Actor 阻塞情況）
                crawler.multiprocess_collect_from_accounts_file(
                    args.accounts_file, 
                    args.num_processes
                )
            elif args.use_async:
                # 異步模式
                asyncio.run(crawler.async_collect_from_accounts_file(
                    args.accounts_file, 
                    args.concurrent_limit
                ))
            else:
                # 同步模式
                crawler.collect_from_accounts_file(args.accounts_file)
        finally:
            crawler.close()
    
    elif args.mode == 'single':
        # 單一使用者模式
        if not args.platform or not args.username:
            logger.error("單一使用者模式需要指定 --platform 和 --username")
            return
        
        crawler = SocialMediaCrawler()
        try:
            crawler.collect_user(
                platform=args.platform,
                username=args.username,
                post_limit=args.post_limit,
                story_limit=args.story_limit,
                photo_limit=args.photo_limit,
                posts_newer_than=args.posts_newer_than,
                posts_older_than=args.posts_older_than,
                caption_text=args.caption_text
            )
        finally:
            crawler.close()
    
    elif args.mode == 'hashtag':
        # Hashtag 收集模式
        if not args.platform or not args.hashtag:
            logger.error("Hashtag 收集模式需要指定 --platform 和 --hashtag")
            return
        
        crawler = SocialMediaCrawler()
        try:
            crawler.collect_hashtag(
                platform=args.platform,
                hashtag=args.hashtag,
                results_type=args.results_type,
                results_limit=args.results_limit
            )
        finally:
            crawler.close()
    
    elif args.mode == 'batch':
        # 批次模式（從資料庫讀取）
        if not args.platform:
            logger.error("批次模式需要指定 --platform")
            return
        
        crawler = SocialMediaCrawler()
        try:
            if args.use_multiprocess:
                # 多進程模式（推薦：適合 Apify Actor 阻塞情況）
                crawler.multiprocess_batch_collect(
                    args.platform, 
                    None, 
                    args.num_processes
                )
            elif args.use_async:
                # 異步模式
                asyncio.run(crawler.async_batch_collect(
                    args.platform, 
                    None, 
                    args.concurrent_limit
                ))
            else:
                # 同步模式
                crawler.batch_collect(args.platform)
        finally:
            crawler.close()
    
    elif args.mode == 'all':
        # 所有平台批次模式（從資料庫讀取）
        crawler = SocialMediaCrawler()
        try:
            crawler.collect_all_platforms()
        finally:
            crawler.close()


if __name__ == '__main__':
    main()

