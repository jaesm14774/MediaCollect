"""
通用社群媒體資料收集系統 - 主程式
支援多平台: Instagram, Facebook, Twitter(X), Threads 等
"""
import sys
import os
import time
import random
import pandas as pd
from typing import List, Optional

# 導入核心模組
from core.factory import CollectorFactory, register_all_collectors
from core.database_manager import create_database_manager_from_config
from core.data_models import CollectionResult

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
    
    def collect_user(
        self, 
        platform: str, 
        username: str,
        post_limit: Optional[int] = None,
        story_limit: Optional[int] = None,
        download_media: Optional[bool] = None
    ) -> CollectionResult:
        """
        收集指定使用者的資料
        
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
            print(f"\n{'='*60}")
            print(f"[{platform.upper()}] 開始處理使用者: {username}")
            print(f"{'='*60}")
            
            collector = CollectorFactory.create_collector(
                platform=platform,
                username=username,
                api_token=APIFY_TOKEN
            )
            
            if not collector:
                return CollectionResult(
                    platform=platform,
                    success=False,
                    error_message=f"無法建立 {platform} 收集器"
                )
            
            # 執行收集
            result = collector.collect_all(
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
            
            print(f"\n{result}")
            return result
        
        except Exception as e:
            import traceback
            error_msg = f"收集失敗: {str(e)}\n{traceback.format_exc()}"
            print(f"[錯誤] {error_msg}")
            
            # 發送錯誤通知
            if self.discord_token:
                notify(self.discord_token, f"[{platform.upper()}] 收集失敗 - {username}:\n{str(e)}")
            
            return CollectionResult(
                platform=platform,
                success=False,
                error_message=error_msg
            )
    
    def _download_media_for_result(self, result: CollectionResult, collector):
        """下載收集結果中的媒體檔案"""
        try:
            print(f"\n[{result.platform.value}] 開始下載媒體檔案...")
            
            # 下載貼文媒體
            for post in result.posts:
                collector.download_media(post, MEDIA_FOLDER_PATH)
            
            # 下載限時動態媒體
            for story in result.stories:
                collector.download_media(story, MEDIA_FOLDER_PATH)
            
            print(f"[{result.platform.value}] 媒體下載完成")
        
        except Exception as e:
            print(f"[{result.platform.value}] 下載媒體失敗: {e}")
    
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
            print(f"[{platform}] 沒有要處理的使用者")
            return
        
        # 隨機打亂順序（避免規律性）
        import numpy as np
        username_list = np.random.choice(
            username_list, 
            size=len(username_list), 
            replace=False
        ).tolist()
        
        print(f"\n{'='*60}")
        print(f"[{platform.upper()}] 批次收集模式")
        print(f"使用者數量: {len(username_list)}")
        print(f"{'='*60}\n")
        
        # 批次處理
        for i, username in enumerate(username_list):
            # 批次延遲
            if i % BATCH_SIZE == 0 and i != 0:
                delay = random.randint(BATCH_DELAY_MIN, BATCH_DELAY_MAX)
                print(f"\n[批次延遲] 等待 {delay} 秒...\n")
                time.sleep(delay)
            
            # 收集資料
            try:
                result = self.collect_user(platform, username)
                
                # 使用者間延遲
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                print(f"\n[延遲] 等待 {delay} 秒...\n")
                time.sleep(delay)
            
            except Exception as e:
                print(f"[錯誤] 處理 {username} 時發生錯誤: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 錯誤 - {username}: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"[{platform.upper()}] 批次收集完成")
        print(f"{'='*60}\n")
    
    def collect_all_platforms(self):
        """收集所有啟用平台的資料（從資料庫讀取使用者）"""
        for platform, settings in PLATFORM_SETTINGS.items():
            if not settings.get('enabled', False):
                continue
            
            try:
                self.batch_collect(platform)
            except Exception as e:
                print(f"[錯誤] {platform} 平台收集失敗: {e}")
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
            print(f"[錯誤] 帳號配置檔無效或不存在: {accounts_file}")
            print(f"[提示] 請複製 accounts.example.txt 為 accounts.txt 並填入帳號")
            return
        
        # 載入所有帳號
        all_accounts = get_all_enabled_accounts(accounts_file)
        
        if not all_accounts:
            print("[警告] 配置檔中沒有任何帳號")
            return
        
        print("\n" + "="*60)
        print("每日收集模式 - 從配置檔載入帳號")
        print("="*60)
        
        # 逐平台收集
        for platform, username_list in all_accounts.items():
            # 檢查平台是否啟用
            if not PLATFORM_SETTINGS.get(platform, {}).get('enabled', False):
                print(f"\n[跳過] {platform.upper()} 平台未啟用")
                continue
            
            if not username_list:
                print(f"\n[跳過] {platform.upper()} 沒有設定帳號")
                continue
            
            try:
                print(f"\n{'='*60}")
                print(f"[{platform.upper()}] 開始批次收集")
                print(f"帳號數量: {len(username_list)}")
                print(f"{'='*60}")
                
                # 使用 batch_collect，但提供帳號列表
                self.batch_collect(platform, username_list)
                
                print(f"\n[{platform.upper()}] 完成收集")
            
            except Exception as e:
                print(f"[錯誤] {platform} 平台收集失敗: {e}")
                if self.discord_token:
                    notify(self.discord_token, f"[{platform}] 平台收集失敗: {e}")
        
        print("\n" + "="*60)
        print("每日收集完成")
        print("="*60)
    
    def close(self):
        """關閉資源"""
        self.db.close()


def interactive_mode():
    """互動式測試模式"""
    print("\n" + "="*60)
    print("通用社群媒體資料收集系統 - 互動式測試")
    print("="*60)
    
    # 顯示支援的平台
    supported_platforms = CollectorFactory.get_supported_platforms()
    print("\n支援的平台:")
    for i, platform in enumerate(supported_platforms, 1):
        print(f"  {i}. {platform.upper()}")
    
    # 選擇平台
    print("\n請選擇平台 (輸入數字):")
    try:
        choice = int(input(">>> "))
        if choice < 1 or choice > len(supported_platforms):
            print("無效的選擇")
            return
        platform = supported_platforms[choice - 1]
    except:
        print("無效的輸入")
        return
    
    # 輸入使用者名稱
    print(f"\n請輸入 {platform.upper()} 使用者名稱:")
    username = input(">>> ").strip()
    
    if not username:
        print("使用者名稱不能為空")
        return
    
    # 執行收集
    crawler = SocialMediaCrawler()
    try:
        result = crawler.collect_user(platform, username)
        print("\n" + "="*60)
        print("收集結果:")
        print("="*60)
        print(result)
        print("="*60)
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
  
  # 互動式測試
  python main.py --mode interactive
  
  # 單一使用者收集
  python main.py --mode single --platform instagram --username nasa
  
  # 批次收集（從資料庫讀取使用者）
  python main.py --mode batch --platform twitter
  python main.py --mode all
        """
    )
    parser.add_argument('--mode', 
                       choices=['daily', 'batch', 'single', 'interactive', 'all'], 
                       default='interactive', 
                       help='執行模式:\n'
                            '  daily - 每日收集模式（從 accounts.txt 讀取）\n'
                            '  batch - 批次模式（從資料庫讀取）\n'
                            '  single - 單一使用者\n'
                            '  interactive - 互動式\n'
                            '  all - 所有平台（從資料庫讀取）')
    parser.add_argument('--platform', type=str, help='平台名稱')
    parser.add_argument('--username', type=str, help='使用者名稱')
    parser.add_argument('--post-limit', type=int, help='貼文數量限制')
    parser.add_argument('--story-limit', type=int, help='限時動態數量限制')
    parser.add_argument('--accounts-file', type=str, default='accounts.txt',
                       help='帳號配置檔路徑（預設: accounts.txt）')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        # 互動式模式
        interactive_mode()
    
    elif args.mode == 'daily':
        # 每日收集模式（從配置檔讀取帳號）
        crawler = SocialMediaCrawler()
        try:
            crawler.collect_from_accounts_file(args.accounts_file)
        finally:
            crawler.close()
    
    elif args.mode == 'single':
        # 單一使用者模式
        if not args.platform or not args.username:
            print("單一使用者模式需要指定 --platform 和 --username")
            return
        
        crawler = SocialMediaCrawler()
        try:
            crawler.collect_user(
                platform=args.platform,
                username=args.username,
                post_limit=args.post_limit,
                story_limit=args.story_limit
            )
        finally:
            crawler.close()
    
    elif args.mode == 'batch':
        # 批次模式（從資料庫讀取）
        if not args.platform:
            print("批次模式需要指定 --platform")
            return
        
        crawler = SocialMediaCrawler()
        try:
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

