# AI Provider 設定

更新日期：2026-09-04

「永恆北極星」自由問答支援 Google Gemini Developer API 與 OpenAI。試煉題庫不依賴任何 AI provider。

## 推薦：Google Gemma 4 31B

Google 於 2026-04-02 將 Gemma 4 上架 AI Studio / Gemini API，31B instruction-tuned 模型 ID：

```text
gemma-4-31b-it
```

本專案設定：

```text
AI_PROVIDER=google
GEMINI_API_KEY=...
GEMINI_MODEL=gemma-4-31b-it
```

Google 路徑：

- 使用 Gemini Developer API `generateContent`。
- 使用 `x-goog-api-key` 認證。
- 使用 JSON structured output。
- Gemma 4 thinking level 設為 `minimal`，降低 LINE 回覆延遲。
- 程式端仍驗證 label、來源 ID 與答案長度。

官方資料：

- https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/api-key

### 免費層注意事項

2026-09-04 的官方價格頁將 Gemma 4 Free Tier 的輸入、輸出標為免費，但也標示 Free Tier 內容可用於改善 Google 產品。因此不要把敏感資料送入本專題 Bot。

Google 也正在遷移 Gemini API key 機制；新 key 應直接從 Google AI Studio 建立。避免沿用未受限制的舊 Standard key。

## OpenAI Luna

若使用者已有 OpenAI 額度：

```text
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna
```

OpenAI 路徑繼續使用 Responses API structured output。

## Auto 模式

```text
AI_PROVIDER=auto
```

選擇規則：

```text
有 GEMINI_API_KEY → Google
否則有 OPENAI_API_KEY → OpenAI
否則 → 啟動失敗
```

重要：這只是**啟動時選擇**。如果 Google 已被選中，執行時出現 rate limit、timeout 或服務失敗，程式不會偷偷切到 OpenAI。原因是自動跨供應商 fallback 可能在使用者不知道的情況下產生費用。

## 舊環境相容

舊的：

```text
OPENAI_TIMEOUT_SECONDS=5
```

仍可使用；新的通用名稱優先：

```text
MODEL_TIMEOUT_SECONDS=5
```

`GOOGLE_API_KEY` 也可作為 `GEMINI_API_KEY` 的環境變數別名。
