"""
帳號配置檔載入模組
用於從 accounts.txt 讀取要收集的社群媒體帳號清單
"""
import os
from typing import Dict, List
from pathlib import Path


def load_accounts_from_file(file_path: str = 'accounts.txt') -> Dict[str, List[str]]:
    """
    從配置檔載入帳號清單
    
    參數:
        file_path: 配置檔路徑（預設為 accounts.txt）
    
    返回:
        字典格式: {'platform': ['username1', 'username2', ...]}
    
    配置檔格式範例:
        [instagram]
        username1
        username2
        
        [facebook]
        page1
        page2
    """
    accounts = {
        'instagram': [],
        'facebook': [],
        'twitter': [],
        'threads': []
    }
    
    # 如果檔案不存在，返回空字典
    if not os.path.exists(file_path):
        print(f"[警告] 帳號配置檔不存在: {file_path}")
        print(f"[提示] 請複製 accounts.example.txt 為 accounts.txt 並填入帳號")
        return accounts
    
    try:
        current_platform = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 移除前後空白
                line = line.strip()
                
                # 跳過空行和註解
                if not line or line.startswith('#'):
                    continue
                
                # 檢查是否為平台標記 [platform]
                if line.startswith('[') and line.endswith(']'):
                    platform = line[1:-1].lower()
                    if platform in accounts:
                        current_platform = platform
                    else:
                        print(f"[警告] 不支援的平台: {platform}")
                    continue
                
                # 將帳號加入對應平台
                if current_platform:
                    username = line.strip()
                    if username:
                        accounts[current_platform].append(username)
        
        # 顯示載入結果
        print("\n" + "="*60)
        print("已載入帳號配置")
        print("="*60)
        for platform, usernames in accounts.items():
            if usernames:
                print(f"  {platform.upper()}: {len(usernames)} 個帳號")
                for username in usernames:
                    print(f"    - {username}")
        print("="*60 + "\n")
        
        return accounts
    
    except Exception as e:
        print(f"[錯誤] 讀取帳號配置檔失敗: {e}")
        return accounts


def get_accounts_for_platform(platform: str, file_path: str = 'accounts.txt') -> List[str]:
    """
    取得指定平台的帳號清單
    
    參數:
        platform: 平台名稱 (instagram, facebook, twitter, threads)
        file_path: 配置檔路徑
    
    返回:
        帳號清單
    """
    accounts = load_accounts_from_file(file_path)
    return accounts.get(platform.lower(), [])


def get_all_enabled_accounts(file_path: str = 'accounts.txt') -> Dict[str, List[str]]:
    """
    取得所有平台的帳號清單（只包含有帳號的平台）
    
    參數:
        file_path: 配置檔路徑
    
    返回:
        字典格式: {'platform': ['username1', 'username2', ...]}
        只包含有帳號的平台
    """
    all_accounts = load_accounts_from_file(file_path)
    # 過濾掉沒有帳號的平台
    return {
        platform: usernames 
        for platform, usernames in all_accounts.items() 
        if usernames
    }


def validate_accounts_file(file_path: str = 'accounts.txt') -> bool:
    """
    驗證帳號配置檔是否存在且格式正確
    
    參數:
        file_path: 配置檔路徑
    
    返回:
        是否有效
    """
    if not os.path.exists(file_path):
        return False
    
    accounts = load_accounts_from_file(file_path)
    # 至少要有一個平台有帳號
    return any(usernames for usernames in accounts.values())


# ============================================================================
# 測試程式
# ============================================================================
if __name__ == '__main__':
    print("測試帳號配置檔載入功能\n")
    
    # 測試載入所有帳號
    print("1. 載入所有帳號:")
    accounts = load_accounts_from_file('accounts.txt')
    
    # 測試取得特定平台帳號
    print("\n2. 取得 Instagram 帳號:")
    ig_accounts = get_accounts_for_platform('instagram')
    print(f"   Instagram 帳號數: {len(ig_accounts)}")
    
    # 測試取得所有啟用的平台
    print("\n3. 取得所有有帳號的平台:")
    enabled = get_all_enabled_accounts()
    print(f"   啟用的平台: {list(enabled.keys())}")
    
    # 測試驗證
    print("\n4. 驗證配置檔:")
    is_valid = validate_accounts_file('accounts.txt')
    print(f"   配置檔有效: {is_valid}")

