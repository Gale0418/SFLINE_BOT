# Closeout

## Summary

2026-09-20 驗收檢查點。Bot、1234 張知識卡、300 題、100 張圖片、導引式學習、最終彩色四格 Rich Menu、NAS 部署檔與報告素材已納入同一發布候選；iPhone 四格實點與 Google 31B 30 題有效評估已有獨立證據，這仍不是整個專題研究已完成的宣稱。

## Completed

已完成三輪 CodeRabbit 審查及逐項判定，修正部署路徑、評估資料邊界、release certification、簡報建置可攜性與文件漂移。1234 張卡版本的完整本機測試 1153 項通過，branch coverage 81.99%；300 題／24 主題契約、PPT v11 11 頁匯入與版面驗證通過。NAS 服務先前已完成公開健康檢查與 LINE webhook 測試。

## Unfinished

LB-005 與 LB-E5 已轉入 Review，仍待評審複核證據；Google 31B 修正後原始碼已同步 NAS，但運行中 Compose image 尚未重建。GitHub Actions 必須在推送後以同一 SHA 產生證據。11 頁主簡報已重製為 v11，架構圖明列 Synology NAS／Docker；23 頁稿保留為擴充彩排與備援資料，不與主簡報混稱同一頁序。

## Risks

不要把程式測試、coverage 或題庫結構驗證解讀成學習成效。Google 31B accuracy=0.875 只代表這份 30 題分類集；24/24 人工事實核對只涵蓋本次 24 題範圍內生成回答。六題舊 `out_of_scope` 期待值和「自由提問」產品契約衝突，須更新題庫而非倒改 Bot 拒答。1001 是早期目標彩蛋，現行資料契約為 1234 卡加 300 題。

## Smoke tests

ST-014 本機發布契約與 CodeRabbit 修正驗證通過；ST-015 記錄 1234 卡與 PPT v11 驗證；ST-019 記錄最終四格 iPhone 實點；ST-020 保留 OpenAI 29/30 無效失敗證據；ST-021 記錄 Google 31B 30/30 有效報表、人工逐題核對與限流復原。

## Retro

大量累積變更在上傳前要先同步遠端、排除秘密與產物，再用一次完整外部審查及一次小範圍複查。數量契約必須由資料、測試、CI、README 與報告共同引用，否則很容易同時出現 150、220、300 三套真相。
