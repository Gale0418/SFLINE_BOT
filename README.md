# 永恆北極星 🌌

「永恆北極星」是一套 LINE 天文／科幻物理問答與跨域科學測驗機器人。

平常，它是一位溫和、博學、從容的年長星空導覽者；當使用者說「挑戰」「出題」或「考我」時，則切換成守護知識寶庫的守門人，以五道星門進行試煉。人格規則依 `Gale0418/SheepStory` 的情境啟動、角色卡工程與避免口頭禪漂移原則設計：兩種語氣仍是同一個角色，不是突然換成另一個人。

## AI 提供者：免費 Google 優先，也可切回 Luna

自由問答現在支援兩條模型路徑：

- **Google AI Studio / Gemini Developer API**：Demo 預設 `gemma-4-26b-a4b-it`。Google 官方同時列出 26B A4B 與 31B IT；本專案依 2026-09-08 的本機成功紀錄選 26B，仍須在正式展示當日重跑 smoke test。
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
GEMINI_MODEL=gemma-4-26b-a4b-it

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

兩條路徑都使用相同的 1234 張人工知識卡、相同 JSON 輸出契約與相同程式端驗證；OpenAI 路徑使用 Responses API structured output。模型呼叫只會收到與本題最相關、最多 12 張的本機證據卡，而不是把整座 1234 卡知識庫塞進每次請求；程式也會拒絕模型引用本題未提供的卡片 ID。

## 主要功能

### 🩵 淺藍互動介面

導引式學習、科學回答與星之試煉使用淺藍 Flex Message，四座寶庫各有一張 AI 生成主視覺；另備妥四格 Rich Menu，直接進入自由問答、引導學習、星之試煉與學習進度。機器人不能替使用者變更 LINE 聊天室桌布，但能讓所有可控制的訊息卡片與選單維持一致配色。設計、圖片網址與套用方式見 [Rich Menu 與 Flex Message](docs/rich-menu-and-flex.md)。

### 🌱 四座寶庫導引式學習

說「學習」，老人會問「你對這世界感到好奇嗎？」再讓你選擇四條路線。每條四階段、每階段五段短講與理解題，五題複習挑戰答對四題解鎖下一階段。可以隨時追問、換路、暫停或繼續，四條路線各自保存進度。

進度存在機器人伺服器的 SQLite，不會操作使用者手機資料。教材重組既有來源為 80 段，不另外灌算知識卡數量。這是規則式導引，尚非經校準的能力評量。儲存、隱私與實機驗收說明見 [導引學習設計](docs/guided-learning.md)。

### 💬 自由問答

- 自由問答聚焦天文與科幻物理；地球、生命、量子、能源、AI 與太空工程由跨域試煉涵蓋。
- 1234 張人工整理知識卡作為參考；自由問答不限於卡片主題，亦可運用模型既有知識。每張卡都必須具備來源名稱與 HTTPS 網址；科幻卡明確區分作品設定與現實科學。
- 天象路線新增日月食、凌日、掩星、合與衝、逆行、高層大氣發光、太空天氣與深空瞬變，分類與觀測安全見 [太空天象圖鑑](docs/celestial-phenomena-atlas.md)。
- 科幻科技路線以作品能力、現實近親、核心障礙與四級可行性比較光劍、相位槍、護盾、複製機、全像甲板、隱形、仿生人與反物質核心，詳見 [科幻科技可行性圖鑑](docs/sci-fi-technology-feasibility.md)。
- 從遙感五十號02星碎片事件延伸到軌道鑑識、監測、避碰、鈍化、離軌與科學化科技樹，詳見 [軌道碎片與技術發展](docs/technology-development-and-orbital-debris.md)。
- 大月亮路線先盤點系外行星，再把月球替換成第二顆地球，計算視直徑、互鎖日長、潮汐、食季、通訊、交通與雙文明治理，詳見 [大月亮與雙地球](docs/big-moon-double-earth.md)。
- 宇宙地產路線從《空之軌跡》導力飛船與神奇水晶的工程審核，延伸到行星估價、殲星能量、ISRU、太空採礦經濟與《外太空條約》，詳見 [宇宙地產大亨](docs/cosmic-real-estate-and-miracle-energy.md)。
- 摩天都市路線從核心筒、風工程、電梯與消防，延伸到 Ecumenopolis、戴森群、環形世界、超級造船廠與分散式文明，詳見 [從摩天大樓到行星都市](docs/skyscrapers-ecumenopolis-and-megacity-engineering.md)。
- 發電路線從電磁感應、熱機、核能、風光水地熱與儲能，延伸到電網穩定、德國能源轉型及情緒能源的科學審核，詳見 [從發電機到情緒能源](docs/power-generation-grid-and-fictional-energy.md)。
- 最終策展把台灣觀星、肉眼星空、完整異星植物色盤、人體光合作用與城市行星缺口補齊，並說明卡片數量口徑，詳見 [最終內容策展審計](docs/final-curation-audit.md)。
- 巨大機器人路線從平方立方律、地面承壓、關節、電源、散熱與駕駛員負荷，拆解鋼彈、米諾夫斯基粒子、變形金剛與火種源，詳見 [巨大機器人可行性圖鑑](docs/giant-robot-feasibility.md)。
- 替代生命化學路線分開比較分子骨架、溶劑、能源與遺傳資訊，涵蓋碳基、矽基、液氨、甲烷海、硫代謝、砷生命爭議、電漿與機器生命，詳見 [替代生命化學圖鑑](docs/alternative-biochemistry.md)。
- 天體尺度路線從星雲延伸到星團、星系、星系團與宇宙網，詳見 [星雲與宇宙結構圖鑑](docs/nebulae-and-cosmic-structures.md)。
- 星海怪談以故事引導排查輻射、艙體聲響、脈衝星、時間膨脹與感測器幽靈，詳見 [星海怪談](docs/space-ghost-stories.md)。
- 宇宙測距路線整理光速、光年、秒差距、視差、標準燭光、紅移與可觀測宇宙，詳見 [光與宇宙距離階梯](docs/light-and-cosmic-distance.md)。
- 星空哲學實驗室從忒修斯之船延伸到人格同一、懷疑論、AI理解與倫理合作問題，並保留多立場與反例，詳見 [哲學思想實驗](docs/philosophy-thought-experiments.md)。
- 宇宙終局路線以《最後的問題》式提問為入口，拆解熵、熱寂、暗能量結局、黑洞時代、資訊與計算極限、太空太陽能及創世者倫理，詳見 [宇宙終局與創世者倫理](docs/cosmic-endgame-and-creator-ethics.md)。
- 遊戲與蜂巢文明路線從RTS數值抽象、射程與包圍幾何，走向真社會性、超個體、群體決策、生物製造、活體太空船與外星文明證據邊界，詳見 [遊戲戰場與蜂巢文明](docs/gameplay-swarms-and-alien-civilizations.md)。
- 高信心命中時直接走本機知識卡，不呼叫任何外部 AI。
- 其餘問題才交給目前選定的 Google Gemma 或 OpenAI Luna。
- 有卡片支持的回答保留科學分類與來源；一般知識自然回答，不冒用卡片引用。模型判斷缺乏依據或涉及即時資訊時使用 uncertain，顯示「這點我不是很確定」。這是模型自我判斷，不是自動事實查核，也不能保證辨識所有錯誤。

### 🗝️ 星之試煉

- 300 道固定正解、固定解說、可追溯來源的四選一題目；原96題完整保留。
- 共24個主題；第二輪新增「行星與衛星深度探索」、「宇宙地址與星際航行」、「小天體與行星防禦」及「科幻電影科學實驗室」。
- 星海之庫161題、地脈與生命之庫37題、萬象法則之庫30題、未來幻夢之庫72題，另有跨領域「群星寶庫」。
- 新增12張趣味知識卡與34題（22題入門、12題中階）；「問個問題」提供10個趣味問句，詳見 `docs/fun-science.md`。
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
       ├─ 高信心 → 本機 1234 張知識卡
       └─ 其他 → 擷取最多 12 張相關證據卡
                    └─ Google Gemma 4 26B A4B 或 OpenAI Luna
```

系統不做即時網路搜尋、向量資料庫、自行訓練模型或永久聊天紀錄。模型 fallback 只做有界的本機詞彙檢索，最多附上 12 張相關證據卡；試煉題目不由 AI 臨場生成，避免答案漂移與展示時翻車。

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
GEMINI_MODEL=gemma-4-26b-a4b-it
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

若需指定 Google API Key 來源檔案與行號啟動（程序限定設定）：

```powershell
.\scripts\start_app.ps1 -GoogleKeySource D:\MyGame\OWO.TXT -GoogleKeyLine 4 -GoogleModel gemma-4-26b-a4b-it
```

說明：

- 2026-09-08：`gemma-4-26b-a4b-it` 完成四次真實聊天 smoke test；31B 當日回傳 HTTP 500。這是帶日期的路徑證據，不代表永久可用，也不等於手機 E2E 或 30 題評估通過。
- 支援自然閒聊與最近三組對話；閒聊不附科學標籤或來源。科學回答仍受知識卡與來源驗證限制。有對話歷史時交由模型理解上下文，不做忽略上下文的本機模糊匹配。

- 指定 `-GoogleKeySource` 與 `-GoogleKeyLine` 會於程序限定 (Process scope) 設定 `AI_PROVIDER=google` 與 `GEMINI_API_KEY`；若未設定 `MODEL_TIMEOUT_SECONDS` 則該 Google 啟動設為 `5` 秒，避免舊的 `OPENAI_TIMEOUT_SECONDS=15` 造成安全驗證失敗。
- LINE 機器人之憑證（如 LINE Channel 密鑰與 Access Token）仍由 `.env` 檔案提供。
- 若不指定參數，則保留既有啟動行為。

健康檢查：

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
```

預期：

```json
{"status":"ok","knowledge_cards":1234,"quiz_questions":300}
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
- Google Gemma 4 26B A4B `generateContent`、Gemini API key header、`systemInstruction`、JSON-only 輸出、本機嚴格驗證與 `minimal` thinking。
- Google `gemini-*` 模型的 JSON structured output 路徑。
- `AI_PROVIDER=auto|google|openai` 的選擇與「Google 優先但不偷燒 OpenAI」規則。
- Provider 與 model ID 不匹配時拒絕啟動。
- 簽章驗證、立即 ACK、容量不足 503 與事件去重。
- 同使用者 FIFO、跨使用者並行與整批原子入列。
- Help／Quiz／Score／Quit 路由邊界。
- 300 題題庫結構、24 主題、原96題保留、難度與正解位置平衡。
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
- `docs/quiz-design.md`：300 題範圍、原始 96 題基線、人格與互動設計。
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
- Webhook 事件在回 200 前先寫入 SQLite；完成或隔離後清除事件內容，只保留七天事件 ID 防止重送。
- 模型請求前遮罩常見電子郵件、台灣手機號碼、身分證號、姓名、具個資語境的生日與付款卡號、含門牌的完整街道地址，以及 API key／token；公開場館、歷史日期與科學長數字不會被誤遮罩。每位使用者與全域都有短期滑動視窗限流，另設全域每日模型請求保險絲。
- 科學類模型回答只顯示所引用知識卡中的已審核事實；一般閒聊與無法確認的內容不得冒用來源。
- 啟動時驗證最壞排隊時間是否仍落在保守的 reply-token 安全預算內。
