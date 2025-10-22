"""
通用資料庫管理器
處理多平台社群媒體資料的儲存與更新
"""
import pandas as pd
import pymysql
from sqlalchemy import create_engine
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from .data_models import PlatformType, PlatformUser, SocialPost, CollectionResult
import datetime
import json
import sys
import os

# 載入欄位轉換器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.platform_config import apply_field_transformers

# 導入 logger
from lib.logger import get_logger
logger = get_logger('DatabaseManager')


class DatabaseManager:
    """
    資料庫管理器
    
    負責將收集到的社群媒體資料儲存到 MySQL 資料庫
    支援多平台統一管理
    """
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        初始化資料庫連接
        
        參數:
            host: 資料庫主機
            port: 資料庫埠口
            user: 使用者名稱
            password: 密碼
            database: 資料庫名稱
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        
        # 建立連接
        self.conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            db=database
        )
        self.cursor = self.conn.cursor()
        
        # 建立 SQLAlchemy engine
        self.engine = create_engine(
            f'mysql+mysqldb://{user}:{quote_plus(password)}@{host}:{port}/{database}?charset=utf8mb4'
        )
        
        logger.info(f"已連接到資料庫: {database}@{host}:{port}")
    
    def close(self):
        """關閉資料庫連接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("已關閉資料庫連接")
    
    # =========================================================================
    # 使用者管理
    # =========================================================================
    
    def save_user(self, user: PlatformUser):
        """
        儲存使用者記錄（每次都新增一筆歷史記錄）
        
        參數:
            user: PlatformUser 物件
        """
        user_data = user.to_dict()
        user_data['create_time'] = datetime.datetime.now()
        user_data['created_at'] = datetime.datetime.now()
        user_data['updated_at'] = datetime.datetime.now()
        user_data['status'] = 1  # 啟用狀態
        
        # 套用欄位轉換器
        user_data = apply_field_transformers(user_data)
        
        df = pd.DataFrame([user_data])
        df.to_sql('social_users', self.engine, if_exists='append', index=False)
        
        logger.info(f"已儲存使用者歷史記錄: {user.username}")
    
    
    # =========================================================================
    # 貼文管理
    # =========================================================================
    
    def save_posts(self, posts: List[SocialPost]):
        """
        儲存貼文列表
        
        參數:
            posts: SocialPost 物件列表
        """
        if not posts:
            logger.info("沒有貼文需要儲存")
            return
        
        # 轉換為 DataFrame
        posts_data = []
        for post in posts:
            post_dict = post.to_dict()
            post_dict['create_time'] = datetime.datetime.now()
            post_dict['updated_at'] = datetime.datetime.now()
            
            # 套用欄位轉換器
            post_dict = apply_field_transformers(post_dict)
            
            posts_data.append(post_dict)
        
        df = pd.DataFrame(posts_data)
        
        # 使用 update_table 方法儲存
        self._update_table(
            df=df,
            table_name='social_posts',
            diff_table_name='social_posts_diff',
            primary_keys=['platform', 'post_id']
        )
        
        logger.info(f"已儲存 {len(posts)} 筆貼文")
    
    def save_stories(self, stories: List[SocialPost]):
        """
        儲存限時動態列表
        
        參數:
            stories: SocialPost 物件列表
        """
        if not stories:
            logger.info("沒有限時動態需要儲存")
            return
        
        # 轉換為 DataFrame
        stories_data = []
        for story in stories:
            story_dict = story.to_dict()
            story_dict['create_time'] = datetime.datetime.now()
            story_dict['updated_at'] = datetime.datetime.now()
            
            # 套用欄位轉換器（在映射欄位之前）
            story_dict = apply_field_transformers(story_dict)
            
            # 將特定欄位映射到 social_stories 表的欄位結構
            story_record = {
                'platform': story_dict.get('platform'),
                'post_id': story_dict.get('post_id'),
                'author_id': story_dict.get('author_id'),
                'author_username': story_dict.get('author_username'),
                'author_display_name': story_dict.get('author_display_name'),
                'media_type': story_dict.get('primary_media_type'),
                'video_url': story_dict.get('sub_video_url').split(',')[0] if story_dict.get('sub_video_url') else None,
                'image_url': story_dict.get('sub_image_url').split(',')[0] if story_dict.get('sub_image_url') else None,
                'thumbnail_url': story_dict.get('sub_thumbnail_url').split(',')[0] if story_dict.get('sub_thumbnail_url') else None,
                'create_time': story_dict.get('create_time'),
                'created_at': story_dict.get('created_at'),
                'expires_at': story_dict.get('expires_at'),
                'updated_at': story_dict.get('updated_at'),
                'raw_data': story_dict.get('raw_data')
            }
            
            stories_data.append(story_record)
        
        df = pd.DataFrame(stories_data)
        
        # 使用 update_table 方法儲存
        self._update_table(
            df=df,
            table_name='social_stories',
            diff_table_name='social_stories_diff',
            primary_keys=['platform', 'post_id']
        )
        
        logger.info(f"已儲存 {len(stories)} 筆限時動態")
    
    def _update_table(
        self, 
        df: pd.DataFrame, 
        table_name: str, 
        diff_table_name: str, 
        primary_keys: List[str]
    ):
        """
        更新資料表（先刪後插策略）
        
        參數:
            df: 要更新的資料框
            table_name: 目標資料表名稱
            diff_table_name: 暫存差異表名稱
            primary_keys: 主鍵欄位列表
        """
        if len(df) == 0:
            return
        
        try:
            # Step 1: 清空暫存表並插入新資料的主鍵
            self.cursor.execute(f'TRUNCATE TABLE {diff_table_name}')
            self.conn.commit()
            
            df.loc[:, primary_keys].to_sql(
                diff_table_name, 
                self.engine, 
                if_exists='append', 
                index=False
            )
            
            # Step 2: 刪除已存在的資料
            primary_key_conditions = ' AND '.join(
                [f'tb.{pk} = tb2.{pk}' for pk in primary_keys]
            )
            delete_sql = f"""
                DELETE tb
                FROM {table_name} tb
                WHERE EXISTS (
                    SELECT 1
                    FROM {diff_table_name} tb2
                    WHERE {primary_key_conditions}
                )
            """
            self.cursor.execute(delete_sql)
            self.conn.commit()
            
            # Step 3: 插入新資料
            df.to_sql(table_name, self.engine, index=False, if_exists='append')
            
            logger.info(f"已更新 {table_name} 表，共 {len(df)} 筆資料")
        
        except Exception as e:
            logger.error(f"更新表格失敗: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # =========================================================================
    # 收集結果儲存
    # =========================================================================
    
    def save_collection_result(self, result: CollectionResult) -> bool:
        """
        儲存完整的收集結果
        
        參數:
            result: CollectionResult 物件
        
        返回:
            是否成功儲存
        """
        if not result.success:
            logger.warning(f"收集失敗，不儲存資料: {result.error_message}")
            return False
        
        try:
            # 1. 儲存使用者資料（每次收集都會新增一筆歷史記錄）
            if result.user:
                self.save_user(result.user)
            else:
                logger.warning("沒有使用者資料")
                return False
            
            # 2. 儲存貼文
            if result.posts:
                self.save_posts(result.posts)
            
            # 3. 儲存限時動態
            if result.stories:
                self.save_stories(result.stories)
            
            logger.info(f"成功儲存 {result.platform.value} 平台的收集結果")
            return True
        
        except Exception as e:
            logger.error(f"儲存收集結果失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # =========================================================================
    # 查詢功能
    # =========================================================================
    
    def get_active_users(self, platform: Optional[str] = None) -> pd.DataFrame:
        """
        取得所有啟用的使用者列表（只返回唯一的使用者，避免重複）
        
        參數:
            platform: 平台名稱（None 表示所有平台）
        
        返回:
            使用者資料 DataFrame（每個使用者只會出現一次）
        """
        if platform:
            # 使用子查詢取得每個使用者的最新記錄，避免重複
            query = """
                SELECT t1.* 
                FROM social_users t1
                INNER JOIN (
                    SELECT username, platform, MAX(id) as max_id
                    FROM social_users
                    WHERE status = 1 AND platform = %s
                    GROUP BY username, platform
                ) t2 ON t1.username = t2.username 
                    AND t1.platform = t2.platform 
                    AND t1.id = t2.max_id
                WHERE t1.status = 1
            """
            df = pd.read_sql_query(query, self.engine, params=(platform,))
        else:
            query = """
                SELECT t1.* 
                FROM social_users t1
                INNER JOIN (
                    SELECT username, platform, MAX(id) as max_id
                    FROM social_users
                    WHERE status = 1
                    GROUP BY username, platform
                ) t2 ON t1.username = t2.username 
                    AND t1.platform = t2.platform 
                    AND t1.id = t2.max_id
                WHERE t1.status = 1
            """
            df = pd.read_sql_query(query, self.engine)
        
        logger.info(f"從資料庫讀取到 {len(df)} 個唯一的啟用使用者")
        return df
    
    def get_user_posts(
        self, 
        platform: str, 
        username: str, 
        limit: int = 50
    ) -> pd.DataFrame:
        """
        取得指定使用者的貼文
        
        參數:
            platform: 平台名稱
            username: 使用者名稱
            limit: 限制筆數
        
        返回:
            貼文資料 DataFrame
        """
        query = """
            SELECT * FROM social_posts
            WHERE platform = %s AND author_username = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        df = pd.read_sql_query(query, self.engine, params=(platform, username, limit))
        return df
    
    # =========================================================================
    # Hashtag 貼文管理
    # =========================================================================
    
    def save_hashtag_posts(self, posts: List, hashtag: str):
        """
        儲存 hashtag 貼文列表
        
        參數:
            posts: HashtagPost 物件列表
            hashtag: 收集的 hashtag（不含 # 符號）
        """
        if not posts:
            logger.info("沒有 hashtag 貼文需要儲存")
            return
        
        # 轉換為 DataFrame
        posts_data = []
        for post in posts:
            post_dict = post.to_dict()
            post_dict['hashtag'] = hashtag.lstrip('#')  # 移除 # 符號
            post_dict['create_time'] = datetime.datetime.now()
            post_dict['updated_at'] = datetime.datetime.now()
            
            # 套用欄位轉換器
            post_dict = apply_field_transformers(post_dict)
            
            posts_data.append(post_dict)
        
        df = pd.DataFrame(posts_data)
        
        # ========== 去重處理 ==========
        # 根據唯一鍵 (platform, hashtag, post_id) 去除重複資料
        # 保留最後一筆（最新的）
        original_count = len(df)
        df = df.drop_duplicates(
            subset=['platform', 'hashtag', 'post_id'], 
            keep='last'
        )
        deduplicated_count = len(df)
        
        if original_count > deduplicated_count:
            logger.info(
                f"去除了 {original_count - deduplicated_count} 筆重複的 hashtag 貼文 "
                f"(原始: {original_count}, 去重後: {deduplicated_count})"
            )
        # ==============================
        
        if len(df) == 0:
            logger.info("去重後沒有需要儲存的 hashtag 貼文")
            return
        
        # 使用 update_table 方法儲存
        self._update_table(
            df=df,
            table_name='social_hashtag_posts',
            diff_table_name='social_hashtag_posts_diff',
            primary_keys=['platform', 'hashtag', 'post_id']
        )
        
        logger.info(f"已儲存 {len(df)} 筆 hashtag 貼文 (#{hashtag})")
    
    def save_hashtag_collection_result(self, result) -> bool:
        """
        儲存完整的 hashtag 收集結果
        
        參數:
            result: HashtagCollectionResult 物件
        
        返回:
            是否成功儲存
        """
        if not result.success:
            logger.warning(f"Hashtag 收集失敗，不儲存資料: {result.error_message}")
            return False
        
        try:
            # 儲存 hashtag 貼文
            if result.posts:
                self.save_hashtag_posts(result.posts, result.hashtag)
            else:
                logger.warning(f"沒有 hashtag 貼文資料 (#{result.hashtag})")
            
            logger.info(f"成功儲存 {result.platform.value} 平台的 hashtag 收集結果 (#{result.hashtag})")
            return True
        
        except Exception as e:
            logger.error(f"儲存 hashtag 收集結果失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # =========================================================================
    # 收集歷史記錄管理
    # =========================================================================
    
    def save_collection_history(
        self,
        platform: str,
        username: str,
        success: bool,
        post_count: int = 0,
        story_count: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime.datetime] = None,
        finished_at: Optional[datetime.datetime] = None,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """
        儲存收集歷史記錄到 collection_history 資料表
        
        參數:
            platform: 平台類型
            username: 使用者名稱
            success: 是否成功
            post_count: 收集的貼文數
            story_count: 收集的限時動態數
            error_message: 錯誤訊息
            started_at: 開始時間
            finished_at: 完成時間
            duration_seconds: 執行時長（秒）
        
        返回:
            是否成功儲存
        """
        try:
            history_data = {
                'platform': platform,
                'username': username,
                'success': 1 if success else 0,
                'post_count': post_count,
                'story_count': story_count,
                'error_message': error_message,
                'started_at': started_at,
                'finished_at': finished_at,
                'duration_seconds': duration_seconds
            }
            
            df = pd.DataFrame([history_data])
            df.to_sql('collection_history', self.engine, if_exists='append', index=False)
            
            return True
        
        except Exception as e:
            logger.error(f"儲存收集歷史記錄失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def __enter__(self):
        """支援 with 語句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支援 with 語句"""
        self.close()


def create_database_manager_from_config(config_path: str = None) -> DatabaseManager:
    """
    從設定檔或環境變數建立資料庫管理器
    
    優先順序:
    1. 環境變數 (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
    2. 設定檔 (CSV 格式)
    
    參數:
        config_path: 設定檔路徑 (CSV 格式)，如果為 None 則只使用環境變數
    
    返回:
        DatabaseManager 實例
    """
    import os
    
    # 優先使用環境變數
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME', 'crawler')
    
    # 如果環境變數完整，直接使用
    if db_host and db_port and db_user and db_password:
        return DatabaseManager(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name
        )
    
    # 否則嘗試從設定檔讀取（向下相容）
    if config_path and os.path.exists(config_path):
        config = pd.read_csv(config_path, index_col='name')
        return DatabaseManager(
            host=config.loc['ip', 'value'],
            port=int(config.loc['port', 'value']),
            user=config.loc['user', 'value'],
            password=config.loc['password', 'value'],
            database=db_name
        )
    
    # 都沒有的話顯示錯誤
    raise ValueError(
        "無法建立資料庫連接！請設定以下任一方式：\n"
        "1. 在 .env 檔案中設定 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME\n"
        "2. 提供有效的 config_path 參數指向 CSV 格式的設定檔"
    )

