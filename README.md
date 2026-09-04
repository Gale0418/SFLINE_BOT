# 永恆北極星 🌌

「永恆北極星」是一套 LINE 天文／科幻物理問答與跨域科學測驗機器人。

平常，它是一位溫和、博學、從容的年長星空導覽者；當使用者說「挑戰」「出題」或「考我」時，則切換成守護知識寶庫的守門人，以五道星門進行試煉。人格規則依 `Gale0418/SheepStory` 的情境啟動、角色卡工程與避免口頭禪漂移原則設計：兩種語氣仍是同一個角色，不是突然換成另一個人。

## AI 提供者：免費 Google 優先，也可切回 Luna

自由問答現在支援兩條模型路徑：

- **Google AI Studio / Gemini Developer API**：預設推薦 `gemma-4-31b-it`。Gemma 4 31B IT 可透過 Gemini API 代管使用；目前 Gemma 4 Free Tier 的輸入與輸出皆免費，但仍受 rate limit、quota、區域與服務政策限制。
- **OpenAI**：若你已有可用額度，可切回 `gpt-5.6-luna`。

設定方式：

```text
AI_PROVIDER=google   # google | openai | auto
```

- `google`：只用 Google，不會偷偷改用付費 OpenAI。
- `openai`：只用 OpenAI。
- `auto`：有 `GEMINI_API_KEY` 時優先 Google；沒有才使用 `OPENAI_API_KEY`。**不做執行時跨供應商自動 fallback**，避免 Google 額度用完後突然開始燒 OpenAI 費用。

### 免費推薦設定

請到 Google AI Studio 建立新的 Gemini API key。Google 正在淘汰舊式 unrestricted standard keys；新建立的 key 會使用新的 Auth key 流程。

```text
AI_PROVIDER=google
GEMINI_API_KEY=你的_Google_AI_Studio_Key
GEMINI_MODEL=gemma-4-31b-it

LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
NGROK_AUTHTOKEN=...
```

`GOOGLE_API_KEY` 也可當作 `GEMINI_API_KEY` 的相容別名。

> 隱私提醒：Google Gemini Developer API 的 Free Tier 目前標示「內容可用於改善 Google 產品」。本專題不要傳送敏感個資、密碼、私人醫療資料或秘密金鑰。程式本身仍不會把使用者全文寫入日誌。

Gemma 4 會使用官方 `systemInstruction` 與 `minimal` thinking，並要求只輸出 JSON，再由程式端嚴格解析與驗證。Google Structured Outputs 的目前支援清單未明列 Gemma 4，因此本專案不把 Gemma 4 的可靠性賭在 response schema 上；若改用支援 Structured Outputs 的 `gemini-*` 模型，才會送出 JSON schema。

### 如果要切回 OpenAI Luna

```text
AI_PROVIDER=openai
OPENAI_API_KEY=你的_OpenAI_Key
OPENAI_MODEL=gpt-5.6-luna
```

兩條路徑都使用相同的 24 張人工知識卡、相同 JSON 輸出契約與相同程式端驗證；OpenAI 路徑使用 Responses API structured output。

## 主要功能

### 💬 自由問答

- 自由問答聚焦天文與科幻物理；地球、生命、量子、能源、AI 與太空工程由跨域試煉涵蓋。
- 24 張人工整理知識卡作為受限上下文。
- 高信心命中時直接走本機知識卡，不呼叫任何外部 AI。
- 其餘問題才交給目前選定的 Google Gemma 或 OpenAI Luna。
- 回答標示「已觀測／已驗證」「理論上可描述但尚未實現」「科幻設定」或「超出範圍」。

### 🗝️ 星之試煉

- 96 道固定正解、固定解說、可追溯來源的四選一題目。
- 16 個主題，涵蓋宇宙、恆星、太陽系、地質、海洋、演化、人體、相對論、量子、材料、能源、AI、太空工程與科幻邊界。
- 四座正式寶庫各 24 題，另有跨領域「群星寶庫」。
- 見習、遠征、守門人與命運混合四種入口。
- 每次隨機抽 5 題；可使用 Quick Reply 或直接輸入 A／B／C／D。
- 每題立即公布正解、概念解說與來源，最後給出分數、最高連勝與稱號。
- 答案 Postback 使用 HMAC 簽章並綁定使用者、場次、題目與選項，防止竄改、重播與跨使用者套用。
- **題庫完全不依賴 AI API**；即使 Google/OpenAI 暫時不能用，挑戰模式仍能正常運作。

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
  └─ HybridAnswerService
       ├─ 高信心 → 本機 24 張知識卡
       └─ 其他 → Google Gemma 4 31B 或 OpenAI Luna
```

系統不做即時網路搜尋、RAG、向量資料庫、自行訓練模型或永久聊天紀錄。試煉題目不由 AI 臨場生成，避免答案漂移與展示時翻車。

## 系統需求

- Windows 10/11
- Python 3.11（固定使用 `py -3.11`）
- LINE Messaging API Channel
- **Google AI Studio API key（免費推薦）或 OpenAI API key（二選一）**
- ngrok 3.x

## 安裝

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

## 金鑰設定

`.env` 至少需要 LINE 與 ngrok 金鑰，再加 Google / OpenAI 任一 AI 金鑰。

Google 免費方案：

```text
NGROK_AUTHTOKEN=...
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...

AI_PROVIDER=google
GEMINI_API_KEY=...
GEMINI_MODEL=gemma-4-31b-it
```

OpenAI 方案：

```text
NGROK_AUTHTOKEN=...
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...

AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna
```

若金鑰仍存放在專案外的 `OWO.TXT`／`NGROK.txt`，一次性遷移工具現在接受 `GEMINI_API_KEY`、`GOOGLE_API_KEY` 或 `OPENAI_API_KEY`：

```powershell
.\.venv\Scripts\eternal-polaris-migrate-secrets.exe `
  --ngrok-source "D:\MyGame\LINE_BOT\NGROK.txt" `
  --app-source "D:\MyGame\OWO.TXT" `
  --output "D:\MyGame\LINE_BOT\.env"
```

工具不顯示值、不覆寫既有 `.env`，也不自動刪除來源檔。

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

- OpenAI Responses 結構化輸出。
- Google Gemma 4 31B `generateContent`、Gemini API key header、`systemInstruction`、JSON-only 輸出、本機嚴格驗證與 `minimal` thinking。
- Google `gemini-*` 模型的 JSON structured output 路徑。
- `AI_PROVIDER=auto|google|openai` 的選擇與「Google 優先但不偷燒 OpenAI」規則。
- Provider 與 model ID 不匹配時拒絕啟動。
- 簽章驗證、立即 ACK、容量不足 503 與事件去重。
- 同使用者 FIFO、跨使用者並行與整批原子入列。
- Help／Quiz／Score／Quit 路由邊界。
- 96 題題庫結構、16 主題、難度與正解位置平衡。
- 答案符文竄改、跨使用者套用、舊題重播與 TTL。
- LINE Quick Reply 的按鈕數、文字長度與 action schema。

`data/eval_questions.csv` 驗證的是自由問答分類資料；`data/quiz_questions.tsv` 則是固定題庫，兩種評估不可混成同一分數。

## CI 與發布認證

Actions 只保留：

- `Main CI`：安裝鎖定環境、依賴檢查、compile、完整 tests + branch coverage 與離線評估資料驗證。
- `Release certification`：Main CI 成功後，唯讀 checkout 剛通過測試的**精確 SHA**，再次驗證題庫、AI provider 契約與工作流清潔度。

Release certification 只有 `contents: read`，不會自己 commit、push main 或移動 tag。

## 文件

- `docs/architecture.md`：系統資料流與可靠性邊界。
- `docs/ai-providers.md`：Google Gemma／OpenAI 切換方式與隱私注意事項。
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
