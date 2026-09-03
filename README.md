# 永恆北極星

「永恆北極星」是一套 LINE 天文與科幻物理問答機器人。它透過 LINE Webhook、ngrok、本機 Flask／Waitress 與 OpenAI Responses API 回覆繁體中文答案，並標示「已觀測／已驗證」、「理論上可行但尚未實現」、「科幻設定」或「超出範圍」。

本專題使用既有語言模型，**沒有自行訓練神經網路**。24 張知識卡會完整放入固定模型上下文；不做即時網路搜尋、RAG、向量資料庫或永久記憶。

## 系統需求

- Windows 10/11
- Python 3.11（固定使用 `py -3.11`）
- LINE Messaging API Channel
- OpenAI API Key
- ngrok 3.x

## 1. 安裝

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

## 2. 一次性金鑰遷移

遷移工具只接受有明確名稱的應用程式金鑰；`NGROK.txt` 可以是單一未命名 ngrok token。它不顯示金鑰值、不覆寫 `.env`，也不刪除來源檔。

來源檔應整理成下面的格式（等號右側放實際值）：

```text
# NGROK.txt
NGROK_AUTHTOKEN=...

# OWO.TXT
OPENAI_API_KEY=...
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
```

若檔案混有課堂筆記、網址或多個未標記 token，工具會安全停止。請先把名稱補齊，不要依長度猜用途。

```powershell
.\.venv\Scripts\eternal-polaris-migrate-secrets.exe `
  --ngrok-source "D:\MyGame\LINE_BOT\NGROK.txt" `
  --app-source "D:\MyGame\OWO.TXT" `
  --output "D:\MyGame\LINE_BOT\.env"
```

必要欄位為 `NGROK_AUTHTOKEN`、`OPENAI_API_KEY`、`LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`。遷移完成並確認服務正常後，請自行把原始 TXT 移至安全位置。

## 3. 啟動順序

第一個 PowerShell 視窗：

```powershell
.\scripts\start_app.ps1
```

確認本機健康狀態：

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
```

看到 `status: ok` 後，再開第二個 PowerShell 視窗：

```powershell
.\scripts\start_ngrok.ps1
```

把 ngrok 顯示的 HTTPS 網址加上 `/callback`，例如 `https://example.ngrok-free.app/callback`，貼到 LINE Developers 的 Webhook URL 並按 Verify。切勿貼 `/health`。

## 4. 測試

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\eternal-polaris-eval.exe
```

第二個命令只驗證 24 張知識卡與 30 題資料，不會呼叫 OpenAI，也不會製造假指標。需要實際評估時：

```powershell
.\.venv\Scripts\eternal-polaris-eval.exe --online
```

線上評估結果寫入 `results/evaluation.json`，包括 3×3 confusion matrix、Accuracy、各類 Precision／Recall／F1、Macro-F1、拒答率、來源匹配率及延遲。答案事實正確率保留人工評分，不與分類 Accuracy 混為一談。
只要有任何 API 或格式錯誤，報表會標記 `run_status: invalid`，命令也會以非零狀態結束，避免把服務失敗誤當成模型 0 分。

## 5. 隱私與可靠性

- 在解析 JSON 前驗證 `X-Line-Signature`。
- 每個 reply token 只使用一次，不重試 LINE reply。
- 以 `webhookEventId` 在記憶體內去重 10 分鐘。
- 使用者 ID 經雜湊後作為記憶索引；只保留最近三組對話並於 30 分鐘後失效。
- 日誌不記錄金鑰、原始 Webhook body、完整 LINE ID 或使用者問題全文。
- OpenAI 逾時、限流或格式錯誤時，回覆固定的安全備援文字。

## 6. 常見問題

### ngrok 顯示 Connection refused

代表 tunnel 已啟動，但本機 Waitress／Flask 尚未監聽。先停止 ngrok，重新啟動應用程式，確認 `http://127.0.0.1:5000/health` 回傳正常後，再啟動 ngrok。

### LINE Verify 失敗

確認網址是 HTTPS、結尾為 `/callback`、Flask 與 ngrok 都仍在執行，且 `.env` 的 Channel Secret/Access Token 屬於同一個 Messaging API Channel。

### 回覆「暫時接收不到宇宙訊號」

檢查 OpenAI API Key、帳戶額度及網路。服務不會把實際金鑰或使用者文字寫進日誌。

更多設計與報告素材請見 [docs/architecture.md](docs/architecture.md)、[docs/report-outline.md](docs/report-outline.md) 與 [docs/demo-checklist.md](docs/demo-checklist.md)。
