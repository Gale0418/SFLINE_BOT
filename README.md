# 永恆北極星 🌌

「永恆北極星」是一套 LINE 跨域科學問答與互動測驗機器人。

平常，它是一位溫和、博學、從容的年長星空導覽者；當使用者說「挑戰」「出題」或「考我」時，則切換成守護知識寶庫的守門人，以五道星門進行試煉。人格規則依 `Gale0418/SheepStory` 的情境啟動、角色卡工程與避免口頭禪漂移原則設計：兩種語氣仍是同一個角色，不是突然換成另一個人。

## 主要功能

### 💬 自由問答

- 回答天文、地球、生命科學、物理、未來科技與科幻物理。
- 24 張人工整理知識卡作為受限上下文。
- 高信心命中時直接走本機知識卡，不呼叫 OpenAI；其餘問題才交給受限模型。
- 回答標示「已觀測／已驗證」「理論上可描述但尚未實現」「科幻設定」或「超出範圍」。

### 🗝️ 星之試煉

- 96 道固定正解、固定解說、可追溯來源的四選一題目。
- 16 個主題，涵蓋宇宙、恆星、太陽系、地質、海洋、演化、人體、相對論、量子、材料、能源、AI、太空工程與科幻邊界。
- 四座正式寶庫各 24 題，另有跨領域「群星寶庫」。
- 見習、遠征、守門人與命運混合四種入口。
- 每次隨機抽 5 題；可使用 Quick Reply 或直接輸入 A／B／C／D。
- 每題立即公布正解、概念解說與來源，最後給出分數、最高連勝與稱號。
- 答案 Postback 使用 HMAC 簽章並綁定使用者、場次、題目與選項，防止竄改、重播與跨使用者套用。

### 📜 確定性功能導覽

下列指令由程式路由，不交給模型猜測：

| 說法範例 | 功能 |
|---|---|
| `幫助`、`功能`、`你會什麼` | 顯示功能導覽 |
| `挑戰`、`出題`、`考我` | 開啟寶庫選單 |
| `試煉規則`、`玩法` | 顯示規則 |
| `分數`、`目前成績` | 查看本次試煉進度 |
| `退出`、`停止挑戰` | 結束試煉並回到問答模式 |

## 系統架構

```text
LINE Webhook
  ├─ 驗證原始 body 的 X-Line-Signature
  ├─ 整批事件原子入列
  └─ 立即回覆 200；容量不足時回覆 503
          │
          ▼
有界背景工作池
  ├─ 同一使用者 FIFO
  ├─ 不同使用者可並行
  ├─ webhookEventId 去重
  ├─ Help / Quiz / Score / Quit 確定性路由
  ├─ QuizManager（簽章、TTL、進度、評分）
  └─ HybridAnswerService（本機卡片優先、模型受限補助）
```

系統不做即時網路搜尋、RAG、向量資料庫、自行訓練模型或永久聊天紀錄。試煉題目不由 AI 臨場生成，避免答案漂移與展示時翻車。

## 系統需求

- Windows 10/11
- Python 3.11（固定使用 `py -3.11`）
- LINE Messaging API Channel
- OpenAI API Key
- ngrok 3.x

## 安裝

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

## 金鑰設定

`.env` 至少需要：

```text
NGROK_AUTHTOKEN=...
OPENAI_API_KEY=...
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
```

若金鑰仍存放在專案外的 `OWO.TXT`／`NGROK.txt`，可使用一次性遷移工具；工具不顯示值、不覆寫既有 `.env`，也不自動刪除來源檔：

```powershell
.\.venv\Scripts\eternal-polaris-migrate-secrets.exe `
  --ngrok-source "D:\MyGame\LINE_BOT\NGROK.txt" `
  --app-source "D:\MyGame\OWO.TXT" `
  --output "D:\MyGame\LINE_BOT\.env"
```

## 啟動

第一個 PowerShell：

```powershell
.\scripts\start_app.ps1
```

健康檢查：

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
```

預期：

```json
{"status":"ok","quiz_questions":96}
```

第二個 PowerShell：

```powershell
.\scripts\start_ngrok.ps1
```

把 ngrok HTTPS 網址加上 `/callback`，貼到 LINE Developers 的 Webhook URL 並按 Verify。

## 測試與驗收

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest --cov=eternal_polaris --cov-branch --cov-report=term-missing
.\.venv\Scripts\eternal-polaris-eval.exe
```

測試涵蓋：

- 簽章驗證、立即 ACK、容量不足 503 與事件去重。
- 同使用者 FIFO、跨使用者並行與整批原子入列。
- Help／Quiz／Score／Quit 路由邊界。
- 96 題題庫結構、16 主題、難度與正解位置平衡。
- 5 座入口 × 4 種難度共 20 條完整通關模擬。
- 答案符文竄改、跨使用者套用、舊題重播與 TTL。
- LINE Quick Reply 的按鈕數、文字長度與 action schema。

`data/eval_questions.csv` 驗證的是自由問答分類資料；`data/quiz_questions.tsv` 則是固定題庫，兩種評估不可混成同一分數。

## 文件

- `docs/architecture.md`：系統資料流與可靠性邊界。
- `docs/quiz-design.md`：96 題範圍、人格與互動設計。
- `docs/quiz-strict-review-prompt.md`：嚴格專家審查提示詞。
- `docs/demo-checklist.md`：手機 Demo 與截圖驗收。
- `skills/science-vault-quiz/SKILL.md`：可重用的 LINE 科學測驗強化流程。

## 隱私與可靠性

- 在解析事件前驗證 LINE 簽章。
- 日誌不寫入原始 Webhook body、完整 LINE ID、問題全文或金鑰。
- 使用者 ID 只以加鹽 SHA-256 作為記憶、排程與試煉索引。
- 問答記憶只保留最近三組，預設 30 分鐘失效。
- 試煉場次預設 30 分鐘失效，並有最大場次容量。
- 每個 reply token 只送一次；不做可能造成重複訊息的網路不確定重試。
- 啟動時驗證最壞排隊時間是否仍落在保守的 reply-token 安全預算內。
