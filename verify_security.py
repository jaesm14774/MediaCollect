#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全驗證腳本
檢查專案中是否還有機敏資訊未被移除
"""

import os
import re
import sys

def check_file_for_sensitive_info(filepath):
    """
    檢查檔案是否包含機敏資訊
    
    返回:
        (bool, list): (是否安全, 問題列表)
    """
    issues = []
    
    # 跳過二進位檔案和特定目錄
    skip_patterns = [
        '__pycache__',
        '.git',
        '.pyc',
        '.example',
        'SETUP.md',
        'SECURITY_CHECKLIST.md',
        'README.md',
        'verify_security.py'
    ]
    
    for pattern in skip_patterns:
        if pattern in filepath:
            return True, []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 檢查 Apify API Token (真實的 Token 格式)
            apify_tokens = re.findall(r'apify_api_[a-zA-Z0-9]{30,}', content)
            if apify_tokens:
                # 排除明顯的範例值
                real_tokens = [t for t in apify_tokens if 'your_token' not in t and 'xxxxx' not in t and 'yyyyy' not in t]
                if real_tokens:
                    issues.append(f"發現可疑的 Apify Token: {real_tokens[0][:20]}...")
            
            # 檢查包含使用者名稱的絕對路徑
            user_paths = re.findall(r'[C-Z]:/Users/[^/\s\'"]+/', content)
            if user_paths:
                # 排除範例路徑
                real_paths = [p for p in user_paths if 'your_user' not in p and 'username' not in p]
                if real_paths:
                    issues.append(f"發現包含使用者名稱的路徑: {real_paths[0]}")
            
            # 檢查密碼字串
            if re.search(r'password\s*=\s*["\'][^"\']{4,}["\']', content, re.IGNORECASE):
                # 確認不是預設值或範例
                if not re.search(r'password\s*=\s*["\'](?:your_password|password|xxxxx)', content, re.IGNORECASE):
                    issues.append("發現可疑的密碼字串")
            
            # 檢查 Discord Webhook URL
            discord_urls = re.findall(r'https://discord\.com/api/webhooks/\d+/[a-zA-Z0-9_-]+', content)
            if discord_urls:
                if not any('your_discord' in url or 'webhook_url' in url for url in discord_urls):
                    issues.append(f"發現 Discord Webhook URL")
    
    except Exception as e:
        pass
    
    return len(issues) == 0, issues


def main():
    """主程式"""
    # 設定 Windows 終端機的 UTF-8 輸出
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    
    print("=" * 70)
    print("安全驗證腳本 - 檢查機敏資訊")
    print("=" * 70)
    print()
    
    # 要檢查的目錄
    check_dirs = ['config', 'core', 'lib', 'platforms', 'legacy']
    check_files = ['main.py']
    
    all_safe = True
    total_issues = 0
    
    # 檢查目錄中的檔案
    for directory in check_dirs:
        if not os.path.exists(directory):
            continue
            
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    is_safe, issues = check_file_for_sensitive_info(filepath)
                    
                    if not is_safe:
                        all_safe = False
                        total_issues += len(issues)
                        print(f"[WARNING] {filepath}")
                        for issue in issues:
                            print(f"    - {issue}")
                        print()
    
    # 檢查根目錄的檔案
    for file in check_files:
        if os.path.exists(file):
            is_safe, issues = check_file_for_sensitive_info(file)
            
            if not is_safe:
                all_safe = False
                total_issues += len(issues)
                print(f"[WARNING] {file}")
                for issue in issues:
                    print(f"    - {issue}")
                print()
    
    # 檢查機敏檔案是否存在
    print("-" * 70)
    print("檢查機敏檔案是否存在:")
    print("-" * 70)
    
    sensitive_files = [
        '.env',
        'accounts.txt',
        'sql_config.txt',
        'Discord.txt'
    ]
    
    files_exist = False
    for file in sensitive_files:
        if os.path.exists(file):
            print(f"[WARNING] 發現機敏檔案: {file}")
            print(f"    請確認此檔案已加入 .gitignore")
            files_exist = True
    
    if not files_exist:
        print("[OK] 未發現機敏檔案（這是正常的，如果您還沒建立 .env）")
    
    print()
    
    # 檢查 .gitignore
    print("-" * 70)
    print("檢查 .gitignore 設定:")
    print("-" * 70)
    
    if os.path.exists('.gitignore'):
        with open('.gitignore', 'r', encoding='utf-8') as f:
            gitignore_content = f.read()
            
        required_entries = ['.env', 'accounts.txt', 'sql_config.txt', 'Discord.txt']
        missing_entries = []
        
        for entry in required_entries:
            if entry not in gitignore_content:
                missing_entries.append(entry)
        
        if missing_entries:
            print(f"[WARNING] .gitignore 中缺少以下項目:")
            for entry in missing_entries:
                print(f"    - {entry}")
            all_safe = False
        else:
            print("[OK] .gitignore 設定正確")
    else:
        print("[ERROR] 未找到 .gitignore 檔案")
        all_safe = False
    
    print()
    print("=" * 70)
    
    # 總結
    if all_safe and total_issues == 0:
        print("[SUCCESS] 太棒了！沒有發現任何機敏資訊")
        print("[SUCCESS] 專案可以安全上傳到 Git")
        print()
        print("下一步:")
        print("1. 確認 .env.example 已建立")
        print("2. 執行 git status 確認沒有機敏檔案被追蹤")
        print("3. 執行 git add . && git commit")
        print("4. 執行 git remote add origin <your-repo-url>")
        print("5. 執行 git push -u origin master")
        return 0
    else:
        print("[ERROR] 發現問題！請在上傳到 Git 前解決")
        print(f"[ERROR] 共發現 {total_issues} 個潛在問題")
        print()
        print("請檢查上方標記 [WARNING] 的項目")
        return 1


if __name__ == '__main__':
    sys.exit(main())

