"""
通用媒體下載工具
支援下載圖片、影片等媒體檔案
"""
import os
import requests
import time
import random
from typing import Optional


class MediaDownloader:
    """
    媒體檔案下載器
    
    功能:
    - 下載圖片
    - 下載影片
    - 自動重試
    - 隨機延遲
    """
    
    def __init__(
        self, 
        retry_count: int = 3, 
        timeout: int = 30,
        min_delay: float = 0.5,
        max_delay: float = 2.0
    ):
        """
        初始化下載器
        
        參數:
            retry_count: 重試次數
            timeout: 超時時間（秒）
            min_delay: 最小延遲（秒）
            max_delay: 最大延遲（秒）
        """
        self.retry_count = retry_count
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    def download(
        self, 
        url: str, 
        file_path: str, 
        overwrite: bool = False
    ) -> bool:
        """
        下載媒體檔案
        
        參數:
            url: 媒體 URL
            file_path: 儲存路徑
            overwrite: 是否覆蓋已存在的檔案
        
        返回:
            是否成功下載
        """
        # 檢查 URL 是否有效
        if not url or url == 'None' or url == '':
            return False
        
        # 檢查檔案是否已存在
        if os.path.isfile(file_path) and not overwrite:
            print(f"  ⊙ 檔案已存在，跳過: {os.path.basename(file_path)}")
            return False
        
        # 建立目錄
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 重試下載
        for attempt in range(self.retry_count):
            try:
                # 下載檔案
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # 儲存檔案
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = os.path.getsize(file_path)
                print(f"  ✓ 下載成功: {os.path.basename(file_path)} ({file_size / 1024:.1f} KB)")
                
                # 隨機延遲
                time.sleep(random.uniform(self.min_delay, self.max_delay))
                return True
            
            except Exception as e:
                print(f"  ✗ 下載失敗 (嘗試 {attempt + 1}/{self.retry_count}): {e}")
                
                if attempt < self.retry_count - 1:
                    # 等待後重試
                    time.sleep(random.uniform(2.0, 5.0))
        
        return False
    
    def download_multiple(
        self, 
        urls: list, 
        save_dir: str, 
        filename_prefix: str,
        file_extension: str = None
    ) -> int:
        """
        批次下載多個檔案
        
        參數:
            urls: URL 列表
            save_dir: 儲存目錄
            filename_prefix: 檔名前綴
            file_extension: 檔案副檔名（None 表示從 URL 推測）
        
        返回:
            成功下載的數量
        """
        success_count = 0
        
        for index, url in enumerate(urls):
            if not url:
                continue
            
            # 決定副檔名
            if file_extension:
                ext = file_extension
            else:
                # 從 URL 推測副檔名
                if 'video' in url.lower() or url.endswith('.mp4'):
                    ext = 'mp4'
                elif 'image' in url.lower() or any(url.endswith(f'.{e}') for e in ['jpg', 'jpeg', 'png', 'webp']):
                    ext = 'jpg'
                else:
                    ext = 'jpg'  # 預設為 jpg
            
            # 建立檔案路徑
            filename = f"{filename_prefix}_{index}.{ext}"
            file_path = os.path.join(save_dir, filename)
            
            # 下載
            if self.download(url, file_path):
                success_count += 1
        
        return success_count
    
    def get_file_size(self, url: str) -> Optional[int]:
        """
        取得檔案大小（不下載）
        
        參數:
            url: 媒體 URL
        
        返回:
            檔案大小（bytes），失敗則返回 None
        """
        try:
            response = requests.head(url, timeout=10)
            content_length = response.headers.get('Content-Length')
            
            if content_length:
                return int(content_length)
            return None
        except:
            return None

