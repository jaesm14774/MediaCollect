# 🔒 安全檢查清單

本文件說明專案中的機敏資訊處理和安全措施。

---

## ✅ 已完成的安全措施

### 1. 機敏資訊抽離

所有機敏資訊已從程式碼中移除，並遷移到環境變數：

| 機敏資訊類型 | 原位置 | 新位置 | 狀態 |
|------------|-------|-------|------|
| Apify API Tokens | `config/platform_config.py` | `.env` (APIFY_TOKEN_1~20) | ✅ 完成 |
| 資料庫帳號密碼 | `sql_config.txt` / 程式碼 | `.env` (DB_*) | ✅ 完成 |
| Discord Webhook | `Discord.txt` / 程式碼 | `.env` (DISCORD_WEBHOOK_URL) | ✅ 完成 |
| 本地檔案路徑 | 程式碼硬編碼 | `.env` (MEDIA_FOLDER_PATH) | ✅ 完成 |

### 2. Git 版本控制

已建立 `.gitignore` 檔案，排除以下機敏檔案：

```gitignore
.env                  # 環境變數（包含所有機敏資訊）
accounts.txt          # 帳號列表
sql_config.txt        # 舊版資料庫設定檔
Discord.txt           # 舊版 Discord 設定檔
```

### 3. 文件與範本

已建立以下文件協助使用者安全設定：

- ✅ `.env.example` - 環境變數範本（不包含真實資料）
- ✅ `SETUP.md` - 詳細的環境設定指南
- ✅ `SECURITY_CHECKLIST.md` - 本檔案
- ✅ 更新 `README.md` - 加入環境變數設定說明

### 4. 程式碼更新

已更新以下檔案以支援環境變數：

- ✅ `config/platform_config.py` - 從環境變數讀取設定
- ✅ `core/database_manager.py` - 支援環境變數資料庫設定
- ✅ `main.py` - Discord 通知支援環境變數
- ✅ `legacy/config_apify.py` - 舊版檔案也已更新

### 5. 向下相容

系統仍支援舊版設定檔方式，不會破壞現有使用者的設定：

- 優先使用環境變數
- 環境變數不存在時，退回使用舊版設定檔
- 平滑遷移，無需強制更新

---

## 📋 上傳到 Git 前的檢查清單

在執行 `git push` 之前，請確認：

- [ ] `.env` 檔案**不存在**於專案目錄（或已加入 .gitignore）
- [ ] `accounts.txt` 不包含真實帳號（或已加入 .gitignore）
- [ ] `sql_config.txt` 不包含真實資料庫資訊（或已加入 .gitignore）
- [ ] `Discord.txt` 不包含真實 Webhook URL（或已加入 .gitignore）
- [ ] `.gitignore` 檔案已正確設定
- [ ] 所有程式碼中**沒有硬編碼的機敏資訊**
- [ ] `.env.example` 只包含範例值，不包含真實資料

### 快速驗證指令

```bash
# 檢查是否有機敏檔案被追蹤
git ls-files | grep -E "\.env$|accounts\.txt$|sql_config\.txt$|Discord\.txt$"

# 應該沒有任何輸出。如果有輸出，表示機敏檔案被 Git 追蹤了！

# 檢查程式碼中是否還有硬編碼的 API Token
git grep -E "apify_api_[a-zA-Z0-9]{30,}" -- "*.py"

# 應該沒有輸出（.example 和 .md 文件中的範例不算）

# 檢查是否有絕對路徑包含使用者名稱
git grep -E "C:/Users/[^/]+/" -- "*.py"

# 應該沒有輸出
```

---

## 🚨 機敏資訊洩漏的處理

### 如果不小心將機敏資訊推送到 Git：

1. **立即更換所有洩漏的金鑰/密碼**
   ```bash
   # 前往 Apify 更換 API Token
   # 更改資料庫密碼
   # 重新生成 Discord Webhook URL
   ```

2. **從 Git 歷史中移除機敏資訊**
   ```bash
   # 使用 git filter-branch（危險操作！）
   # 或使用 BFG Repo-Cleaner
   # 建議尋求專業協助
   ```

3. **如果是公開倉庫，考慮重建倉庫**
   ```bash
   # 複製乾淨的程式碼
   # 建立新的 Git 倉庫
   # 重新推送
   ```

---

## 🔐 額外安全建議

### 開發環境

1. **使用測試用 API Token**
   - 開發時使用限制較多的測試 Token
   - 正式環境才使用完整權限的 Token

2. **限制資料庫使用者權限**
   ```sql
   -- 只給必要的權限
   GRANT SELECT, INSERT, UPDATE ON crawler.* TO 'app_user'@'localhost';
   ```

3. **定期更換密碼**
   - 至少每 3 個月更換一次
   - 懷疑洩漏時立即更換

### 團隊協作

1. **不要在聊天軟體分享 .env 檔案**
   - 使用安全的密碼管理器（如 1Password、Bitwarden）
   - 或面對面傳遞

2. **每個開發者使用自己的 API Token**
   - 方便追蹤 API 使用情況
   - 發生問題時可以快速定位

3. **Code Review 時注意檢查**
   - 確認沒有硬編碼的密碼
   - 確認 .gitignore 正確設定

### 正式環境

1. **使用環境變數或密鑰管理服務**
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

2. **啟用監控和告警**
   - API 使用異常時發送通知
   - 資料庫異常登入時告警

3. **定期安全審計**
   - 檢查存取日誌
   - 審查權限設定

---

## 📞 發現安全問題？

如果您發現任何安全漏洞，請：

1. **不要**在公開的 Issue 中揭露
2. 私下聯繫專案維護者
3. 等待安全補丁發布後再公開討論

---

## 📚 相關文件

- [SETUP.md](SETUP.md) - 環境設定指南
- [README.md](README.md) - 專案主要文件
- [.env.example](.env.example) - 環境變數範本

---

最後更新：2024-10-19

