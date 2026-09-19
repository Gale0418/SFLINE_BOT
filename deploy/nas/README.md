# Synology NAS 部署

正式資料位於 `/volume1/docker/eternal-polaris`：

- `app/`：目前程式碼與 Docker 建置內容。
- `data/private/`：SQLite 導引學習進度；升級不得覆蓋。
- `backups/`：資料庫備份。
- `.env`：Bot 的 LINE 與 AI 秘密設定，權限必須為 `600`。
- `ngrok.env`：只含 `NGROK_AUTHTOKEN`，由 `ngrok.env.example` 複製，權限必須為 `600`。

容器 `eternal-polaris-bot` 只在 NAS loopback `127.0.0.1:5050` 提供健康檢查；`eternal-polaris-ngrok` 使用既有固定網域把 LINE webhook 導向 bot。兩者皆使用 `restart: unless-stopped`。

安全切換順序：先只啟動 `bot`，在 NAS 本機確認 `http://127.0.0.1:5050/ready`；再停止舊 ngrok、啟動 NAS `ngrok`，最後用 LINE Webhook Test 驗證。SQLite 目錄與 `.env` 不放入映像檔。

首次啟動前必須先在 NAS 建立資料與備份目錄，並確認容器使用者 `1026:100` 可寫；bind mount 會遮蔽映像檔內原本的權限，不能只依賴 Dockerfile 的 `chown`：

```sh
sudo install -d -o 1026 -g 100 -m 0750 /volume1/docker/eternal-polaris/data/private
sudo install -d -o 1026 -g 100 -m 0750 /volume1/docker/eternal-polaris/backups
test -w /volume1/docker/eternal-polaris/data/private
```

`ngrok` 服務只會讀取獨立的 `ngrok.env`；LINE 與 AI 金鑰只注入 `bot` 容器。部署前執行 `cp ngrok.env.example ngrok.env`，只填入 ngrok token，再將檔案設為 `600`。部署後可用 `docker compose exec bot test -w /app/data/private` 做寫入權限 preflight。

若 `/ready` 因 `ProcessInterruptedUnknown` 回 503，代表上次程序在事件處理中斷；系統不會冒險重送一次性 LINE 回覆。管理者可在一小時內於 `webhooks.sqlite3` 檢查 `state='interrupted'` 的隔離事件。若能確認尚未送出回覆，且理解 reply token 可能已失效或造成重複訊息，可用下列命令只重排一次；兩個 event ID 必須相同，且必須明示接受風險：

```sh
docker compose -f deploy/nas/compose.yaml exec -T bot python /app/scripts/requeue_webhook.py \
  --db /app/data/private/webhooks.sqlite3 \
  --event-id EVENT_ID --confirm-event-id EVENT_ID \
  --accept-duplicate-reply-risk
```

若不重排，請在完成判斷後刪除該列。一小時後 payload 會自動清除，事件 ID 最長保留七天。此流程是外部 Reply API 無冪等鍵時的人工風險決策，不宣稱 exactly-once。

## 備份與還原演練

用 DSM「工作排程器」每天執行一次下列命令；腳本使用 SQLite Online Backup API，不可在資料庫運作中直接複製 `.sqlite3` 檔：

```sh
cd /volume1/docker/eternal-polaris/app
docker compose -f deploy/nas/compose.yaml exec -T bot \
  python /app/scripts/backup_sqlite.py --data-dir /app/data/private --backup-dir /app/backups --keep 14
```

每次備份都會執行 `PRAGMA integrity_check` 並產生 SHA-256 manifest。Webhook inbox 含短期訊息與 reply token，刻意不納入長期備份；只有學習進度會備份。每月至少把最新一份備份還原到暫存目錄，重新執行 `PRAGMA integrity_check` 與一輪導引學習 smoke test；未完成還原演練的檔案不能稱為可用備份。
