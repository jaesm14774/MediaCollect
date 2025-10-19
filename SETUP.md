# 📋 環境設定指南

本專案已將所有機敏資訊抽離到環境變數中，請按照以下步驟進行設定。

## 🚀 快速開始

### 步驟 1: 複製環境變數範本

```bash
# 複製 .env.example 為 .env
cp .env.example .env
```

### 步驟 2: 編輯 .env 檔案

使用文字編輯器開啟 `.env` 檔案，填入您的實際設定：

```env
# Apify API Token 設定
# 可以設定多個 Token，系統會隨機選擇使用
APIFY_TOKEN_1=apify_api_your_actual_token_1
APIFY_TOKEN_2=apify_api_your_actual_token_2
APIFY_TOKEN_3=apify_api_your_actual_token_3
# ... 最多可設定 20 個

# 媒體儲存路徑
MEDIA_FOLDER_PATH=E:/your_actual_path/SocialMedia/

# 資料庫設定
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_actual_username
DB_PASSWORD=your_actual_password
DB_NAME=crawler

# Discord 通知設定（選用）
DISCORD_WEBHOOK_URL=your_actual_discord_webhook_url
```

### 步驟 3: 設定帳號列表（選用）

如果您要使用每日收集功能，需要設定帳號列表：

```bash
# 複製帳號配置範本
cp accounts.example.txt accounts.txt

# 編輯 accounts.txt，填入要收集的社群媒體帳號
```

### 步驟 4: 完成！

現在您可以開始使用系統了：

```bash
# 測試設定是否正確
python main.py --mode interactive

# 執行每日收集
python main.py --mode daily
```

---

## 📁 機敏檔案清單

以下檔案包含機敏資訊，**請勿上傳到 Git**：

- `.env` - 環境變數設定檔（包含 API Token、資料庫密碼等）
- `accounts.txt` - 要收集的帳號列表
- `sql_config.txt` - 舊版資料庫設定檔（已棄用，但仍支援）
- `Discord.txt` - 舊版 Discord 通知設定檔（已棄用，但仍支援）

這些檔案已被加入 `.gitignore`，不會被 Git 追蹤。

---

## 🔄 從舊版設定遷移

如果您之前使用的是舊版設定方式（直接在程式碼中寫入 Token），請按照以下步驟遷移：

### 1. 從 `config/platform_config.py` 遷移

**舊版（不推薦）：**
```python
APIFY_TOKEN_LIST = [
    'apify_api_xxxxx',
    'apify_api_yyyyy',
]
MEDIA_FOLDER_PATH = 'E:/path/to/media/'
SQL_CONFIGURE_PATH = 'C:/path/to/sql_config.txt'
```

**新版（推薦）：**
在 `.env` 檔案中設定：
```env
APIFY_TOKEN_1=apify_api_xxxxx
APIFY_TOKEN_2=apify_api_yyyyy
MEDIA_FOLDER_PATH=E:/path/to/media/
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
```

### 2. 從 `sql_config.txt` 遷移

**舊版 sql_config.txt：**
```csv
name,value
ip,127.0.0.1
port,3306
user,my_username
password,my_password
```

**新版 .env：**
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=my_username
DB_PASSWORD=my_password
DB_NAME=crawler
```

### 3. 從 `Discord.txt` 遷移

**舊版 Discord.txt：**
```csv
name,token
程式bug權杖,https://discord.com/api/webhooks/xxxxx
```

**新版 .env：**
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxx
```

---

## ✅ 驗證設定

執行以下命令驗證設定是否正確：

```python
# 測試環境變數是否載入
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('APIFY_TOKEN:', 'OK' if os.getenv('APIFY_TOKEN_1') else 'NOT SET'); print('DB_HOST:', 'OK' if os.getenv('DB_HOST') else 'NOT SET')"
```

如果看到 "OK"，表示設定成功！

---

## 🔒 安全建議

1. **永遠不要將 `.env` 檔案上傳到 Git**
2. **定期更換 API Token**
3. **使用強密碼**
4. **限制資料庫使用者權限**（只給必要的權限）
5. **備份您的 `.env` 檔案**（但要存放在安全的地方）

---

## ❓ 常見問題

### Q: 我可以同時使用舊版和新版設定嗎？

A: 可以！系統優先使用環境變數（新版），如果找不到環境變數，會退回使用設定檔（舊版）。這樣可以平滑過渡。

### Q: 為什麼要使用 .env 檔案？

A: 使用 `.env` 檔案有以下好處：
- 機敏資訊不會被上傳到 Git
- 不同環境（開發、測試、正式）可以使用不同的設定
- 更容易管理和更新設定
- 符合業界最佳實踐

### Q: 我忘記備份 .env 檔案就重裝系統了怎麼辦？

A: 您需要重新填寫所有設定。建議將 `.env` 檔案備份到：
- 加密的雲端硬碟
- 密碼管理器（如 1Password、Bitwarden）
- 加密的外接硬碟

### Q: 團隊協作時如何分享設定？

A: **不要直接分享 `.env` 檔案**！建議：
1. 透過安全管道（如加密通訊軟體）單獨分享
2. 使用企業級密鑰管理服務（如 AWS Secrets Manager、Azure Key Vault）
3. 每個團隊成員使用自己的 API Token

---

## 📞 需要協助？

如果您在設定過程中遇到問題，請查看：
- [主要 README](README.md)
- [架構說明](ARCHITECTURE.md)
- [GitHub Issues](../../issues)

