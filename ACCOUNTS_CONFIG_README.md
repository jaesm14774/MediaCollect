# 📝 帳號配置檔說明

## 概述

`accounts.txt` 是用於管理要收集的社群媒體帳號的配置檔。透過這個檔案，你可以輕鬆管理所有要監控的帳號，無需在程式碼中硬編碼或手動指定。

---

## 檔案格式

### 基本結構

```ini
# 這是註解

[platform_name]
username1
username2
username3

[another_platform]
another_user1
another_user2
```

### 支援的平台

- `[instagram]` - Instagram 帳號
- `[facebook]` - Facebook 粉絲專頁
- `[twitter]` - Twitter (X) 帳號
- `[threads]` - Threads 帳號

### 規則

1. **平台標記**：使用 `[platform_name]` 來標記平台區塊
2. **帳號名稱**：一行一個帳號，不需要加 `@` 符號
3. **註解**：使用 `#` 開頭可以加註解
4. **空白行**：會被自動忽略
5. **大小寫**：平台名稱不區分大小寫（instagram = Instagram = INSTAGRAM）

---

## 完整範例

```ini
# ============================================================================
# Instagram 帳號清單
# ============================================================================
[instagram]
# 官方帳號
instagram
# 科學類
nasa
natgeo
# 科技類
apple
google
microsoft

# ============================================================================
# Facebook 粉絲專頁清單
# ============================================================================
[facebook]
facebook
microsoft
# 暫時停用
# old_page_name

# ============================================================================
# Twitter (X) 帳號清單
# ============================================================================
[twitter]
twitter
elonmusk
# 新聞媒體
BBCBreaking
CNN

# ============================================================================
# Threads 帳號清單
# ============================================================================
[threads]
zuck
instagram
```

---

## 使用方式

### 1. 建立配置檔

```bash
# 複製範本
copy accounts.example.txt accounts.txt

# Linux/Mac
cp accounts.example.txt accounts.txt
```

### 2. 編輯配置檔

使用任何文字編輯器開啟 `accounts.txt`，填入你要收集的帳號。

### 3. 執行收集

```bash
# 使用預設配置檔 (accounts.txt)
python main.py --mode daily

# 使用自訂配置檔
python main.py --mode daily --accounts-file my_accounts.txt
```

---

## 進階技巧

### 1. 多個配置檔

你可以建立多個配置檔用於不同目的：

```bash
# 每日收集的重要帳號
accounts_daily.txt

# 每週收集的次要帳號
accounts_weekly.txt

# 測試用帳號
accounts_test.txt
```

執行時指定檔案：
```bash
python main.py --mode daily --accounts-file accounts_daily.txt
```

### 2. 暫時停用帳號

在帳號前加上 `#` 即可暫時停用：

```ini
[instagram]
nasa
# natgeo  # 暫時停用這個帳號
instagram
```

### 3. 分類管理

使用註解將帳號分類：

```ini
[instagram]
# === 官方帳號 ===
instagram
facebook

# === 科學類 ===
nasa
natgeo
sciencechannel

# === 科技類 ===
apple
google
microsoft
```

### 4. 版本控制

如果使用 Git，建議：

```bash
# 將實際配置檔加入 .gitignore
echo "accounts.txt" >> .gitignore

# 只提交範例檔案
git add accounts.example.txt
```

---

## 與資料庫模式的差異

### 配置檔模式 (`--mode daily`)

**優點：**
- ✅ 簡單直觀，易於管理
- ✅ 可以用文字編輯器快速修改
- ✅ 適合定期排程執行
- ✅ 不需要操作資料庫

**缺點：**
- ❌ 無法動態新增/移除帳號（需重啟）
- ❌ 無法儲存額外的帳號屬性

**適用場景：**
- 固定的監控帳號清單
- 定期排程收集
- 簡單的使用場景

### 資料庫模式 (`--mode batch` / `--mode all`)

**優點：**
- ✅ 可動態管理帳號
- ✅ 可儲存帳號的額外資訊（標籤、優先級等）
- ✅ 可透過程式介面管理

**缺點：**
- ❌ 需要操作資料庫
- ❌ 設定較複雜

**適用場景：**
- 動態管理大量帳號
- 需要儲存帳號的額外屬性
- 複雜的使用場景

---

## 配置檔驗證

### 手動驗證

執行測試腳本檢查配置檔是否正確：

```bash
python test_accounts_loader.py
```

### 在程式中驗證

```python
from config.accounts_loader import validate_accounts_file, load_accounts_from_file

# 檢查檔案是否有效
if validate_accounts_file('accounts.txt'):
    print("配置檔有效")
    accounts = load_accounts_from_file('accounts.txt')
else:
    print("配置檔無效或不存在")
```

---

## 常見問題

### Q: 帳號名稱需要加 @ 嗎？

**A:** 不需要。直接寫帳號名稱即可。

```ini
# ✅ 正確
[instagram]
nasa

# ❌ 錯誤
[instagram]
@nasa
```

### Q: 可以在配置檔中設定每個帳號的收集參數嗎？

**A:** 目前不支援。所有帳號使用 `config/platform_config.py` 中的統一設定。如需個別設定，請使用資料庫模式。

### Q: 配置檔更新後需要重啟嗎？

**A:** 是的。配置檔在程式啟動時讀取，更新後需要重新執行程式。

### Q: 支援中文帳號名稱嗎？

**A:** 支援，只要該平台允許中文帳號名稱。請確保檔案使用 UTF-8 編碼。

### Q: 可以設定某個平台只收集特定帳號嗎？

**A:** 可以。只在該平台區塊填入要收集的帳號，其他帳號不要加入配置檔。

### Q: 如何知道哪些帳號收集成功？

**A:** 執行時會在終端顯示詳細日誌。你也可以：
1. 查看終端輸出
2. 檢查資料庫中的 `collection_history` 表
3. 設定 Discord 通知接收錯誤訊息

---

## 範例場景

### 場景 1: 每日新聞監控

```ini
[twitter]
# 國際新聞
BBCBreaking
CNN
Reuters

# 科技新聞
TechCrunch
TheVerge
engadget
```

```bash
# 每天早上 6 點執行
python main.py --mode daily
```

### 場景 2: 競品分析

```ini
[instagram]
# 我們的品牌
our_brand

# 競爭對手
competitor1
competitor2
competitor3
```

### 場景 3: 網紅追蹤

```ini
[instagram]
# 美食類
food_blogger1
food_blogger2

# 旅遊類
travel_blogger1
travel_blogger2

[threads]
# 科技評測
tech_reviewer1
tech_reviewer2
```

---

## 相關檔案

- `accounts.txt` - 實際使用的配置檔（建議加入 .gitignore）
- `accounts.example.txt` - 配置檔範本
- `config/accounts_loader.py` - 配置檔載入模組
- `test_accounts_loader.py` - 測試腳本

---

## 技術細節

### 檔案編碼

配置檔使用 **UTF-8** 編碼，支援中文和特殊字元。

### 載入邏輯

1. 讀取檔案內容
2. 解析平台區塊 `[platform]`
3. 提取各平台的帳號列表
4. 移除空白行和註解
5. 返回字典格式的資料結構

### 資料結構

```python
{
    'instagram': ['nasa', 'natgeo', 'instagram'],
    'facebook': [],
    'twitter': ['twitter', 'elonmusk'],
    'threads': []
}
```

---

需要更多協助？請參考：
- [README.md](README.md) - 完整系統文件
- [QUICKSTART.md](QUICKSTART.md) - 快速入門指南

