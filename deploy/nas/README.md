# Synology NAS 部署

正式資料位於 `/volume1/docker/eternal-polaris`：

- `app/`：目前程式碼與 Docker 建置內容。
- `data/private/`：SQLite 導引學習進度；升級不得覆蓋。
- `backups/`：資料庫備份。
- `.env`：秘密設定，權限必須為 `600`。

容器 `eternal-polaris-bot` 對內提供 `5050` 健康檢查；`eternal-polaris-ngrok` 使用既有固定網域把 LINE webhook 導向 bot。兩者皆使用 `restart: unless-stopped`。

安全切換順序：先只啟動 `bot`，確認 `http://NAS:5050/health`；再停止舊 ngrok、啟動 NAS `ngrok`，最後用 LINE Webhook Test 驗證。SQLite 目錄與 `.env` 不放入映像檔。
