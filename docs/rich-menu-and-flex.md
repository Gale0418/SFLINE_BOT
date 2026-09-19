# 淺藍互動介面：Rich Menu 與 Flex Message

LINE Messaging API 不能替使用者變更聊天室桌布；聊天室背景仍由每支手機的 LINE 設定控制。本專案能控制的是機器人送出的 Flex Message 與聊天室底部的 Rich Menu，因此兩者統一採霧白、淺藍與深藍文字，維持足夠對比。

## Flex Message

- 四座寶庫選單、導引短講、學習地圖、理解題與有科學標籤的回答會使用淺藍卡片。
- 星海、地脈與生命、萬象法則、未來幻夢各有一張 AI 生成主視覺；程式依卡片內容選擇最接近的寶庫圖片。圖片只負責視覺分類，不作為科學證據。
- 星之試煉保留四個大型選項，並套用相同淺藍色系。
- 原有 Quick Reply、HMAC 簽章及訊息文字完全保留；若內容過長或無法辨識卡片類型，自動回到一般文字訊息。
- 卡片使用 `scaling` 與自動換行，但 LINE 官方提醒不同手機、解析度與字體設定仍可能產生些微差異，部署後應再以實機確認。

LINE 只能讀取公開 HTTPS 圖片。啟動展示網址後，把根網址填入 `.env`：

```text
PUBLIC_BASE_URL=https://你的公開網址
```

若沒有設定，卡片仍會以純文字 Flex 正常運作，不會產生壞圖。圖片由應用程式的 `/media/knowledge/` 白名單路由提供，不允許任意讀取其他檔案。
若先執行 `scripts/start_ngrok.ps1` 再執行 `scripts/start_app.ps1`，啟動腳本會嘗試從本機 ngrok API 自動取得 HTTPS 根網址，不必每次手動修改 `.env`。

## Rich Menu

選單為 2500×843 PNG、3×2 六格，所有按鈕都連到現有功能，不會出現尚未完成的死入口：

1. 觀星入門 → `星等是什麼？`
2. 問守門人 → `你會什麼？`
3. 四座寶庫 → `學習`
4. 星之試煉 → `挑戰`
5. 我的旅程 → `學習進度`
6. 功能說明 → `幫助`

重新產生圖片：

```powershell
python scripts/build_rich_menu.py
```

只預覽 Rich Menu 定義，不修改 LINE 帳號：

```powershell
$env:PYTHONPATH='src'
python -m eternal_polaris.rich_menu
```

確認圖片與六個點擊區後，才明確套用到 LINE 官方帳號：

```powershell
$env:PYTHONPATH='src'
python -m eternal_polaris.rich_menu --apply
```

套用流程依序執行官方驗證、建立、上傳圖片與設為預設選單；若建立後上傳失敗，會刪除本次產生的孤立選單。Rich Menu 不會出現在 LINE 電腦版；手機重新開啟聊天室後才會看到更新。

LINE 電腦版也可能不顯示 Quick Reply，或把貼圖退化成 `[folded]` 一類的文字代號；這是用戶端能力差異，不代表 Webhook 壞掉。Bot 會在本機辨識常見顏文字與這類貼圖代號，直接以守門人口吻回覆；所有核心功能仍可輸入「首頁」、「學習」、「挑戰」或「幫助」使用。正式展示以手機版為準。

參考：

- LINE Developers — [Use rich menus](https://developers.line.biz/en/docs/messaging-api/using-rich-menus/)
- LINE Developers — [Rich menus overview](https://developers.line.biz/en/docs/messaging-api/rich-menus-overview/)
- LINE Developers — [Send Flex Messages](https://developers.line.biz/en/docs/messaging-api/using-flex-messages/)
