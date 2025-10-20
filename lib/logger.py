"""
統一的日誌管理模組
提供檔案和 console 的雙重輸出
支援按日期分檔，並自動清理舊日誌
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import glob


class Logger:
    """
    統一的日誌管理器
    
    功能:
    - 同時輸出到檔案和 console
    - 自動建立 logs 目錄
    - 按日期建立日誌檔案（格式：yyyy-MM-dd）
    - 自動清理舊日誌（預設保留 30 天）
    - 支援不同的日誌等級
    """
    
    _instances = {}
    
    @classmethod
    def _cleanup_old_logs(cls, log_dir: str, name: str, keep_days: int = 30):
        """
        清理舊的日誌檔案
        
        參數:
            log_dir: 日誌目錄
            name: logger 名稱
            keep_days: 保留天數（預設 30 天）
        """
        try:
            # 計算截止日期
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            # 找出所有相關的日誌檔案
            pattern = os.path.join(log_dir, f'{name}_*.log')
            log_files = glob.glob(pattern)
            
            deleted_count = 0
            for log_file in log_files:
                try:
                    # 從檔名提取日期
                    filename = os.path.basename(log_file)
                    date_str = filename.replace(f'{name}_', '').replace('.log', '')
                    
                    # 支援兩種格式：yyyy-MM-dd 和 yyyyMMdd
                    try:
                        if '-' in date_str:
                            file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            file_date = datetime.strptime(date_str, '%Y%m%d')
                    except ValueError:
                        continue  # 跳過無法解析的檔案
                    
                    # 如果檔案太舊，則刪除
                    if file_date < cutoff_date:
                        os.remove(log_file)
                        deleted_count += 1
                except Exception as e:
                    # 個別檔案處理失敗不影響其他檔案
                    continue
            
            if deleted_count > 0:
                print(f"已清理 {deleted_count} 個舊日誌檔案（保留 {keep_days} 天內的記錄）")
        except Exception as e:
            # 清理失敗不影響程式運行
            print(f"清理舊日誌時發生錯誤: {e}")
    
    @classmethod
    def get_logger(cls, name: str = 'MediaCollect', log_dir: str = 'logs', keep_days: int = 30) -> logging.Logger:
        """
        取得或建立 logger 實例（單例模式）
        
        參數:
            name: logger 名稱
            log_dir: 日誌目錄
            keep_days: 保留日誌的天數（預設 30 天）
        
        返回:
            Logger 實例
        """
        if name in cls._instances:
            return cls._instances[name]
        
        # 建立 logs 目錄
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 清理舊日誌
        cls._cleanup_old_logs(log_dir, name, keep_days)
        
        # 建立 logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重複添加 handler
        if logger.handlers:
            cls._instances[name] = logger
            return logger
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 檔案處理器 - 按日期建立檔案（使用 yyyy-MM-dd 格式）
        today = datetime.now().strftime('%Y-%m-%d')
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f'{name}_{today}.log'),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Console 處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 添加處理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        cls._instances[name] = logger
        return logger


# 全域 logger 實例
logger = Logger.get_logger('MediaCollect')


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    取得 logger 實例
    
    參數:
        name: logger 名稱，如果為 None 則使用預設的 'MediaCollect'
    
    返回:
        Logger 實例
    """
    if name:
        return Logger.get_logger(name)
    return logger

