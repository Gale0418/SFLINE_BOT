# New Eden工業考古學：從Veldspar到Wetware Mainframe

整理日期：2026-09-14。對應知識卡 `sw715`～`sw752`。EVE配方與物品名稱以官方Support、官方新聞與Static Data Export為出處；現實對照以NASA、USGS、NIST、IUPAC與PubChem為主。

## 一張圖看懂工業鏈

```text
Asteroid ore ──重處理──> 基礎 minerals ───────────────┐
                                                     ├─> T1 製造
Moon ore ──重處理──> moon materials ──reactions──┐  │
                                                  ├──┴─> T2 components ─> T2
T1 BPC + datacores + decryptor ──invention────────┘

Fullerite gas ──hybrid reactions──> T3材料─────────┐
Ancient Relic + subsystem datacores ──invention───┼─> T3 hull / subsystem
Sleeper salvage與其他components───────────────────┘

Planet P0 ─> P1 ─> P2 ─> P3 ─> P4 ─> Structures / ships / fuel / components
```

## 基礎礦石與現實名稱陷阱

| EVE物品 | 作品用途 | 現實對照提醒 |
|---|---|---|
| Veldspar → Tritanium | 基礎工業骨架 | 都是虛構物質；Tritanium不是鈦 |
| Scordite → Pyerite等 | 常見礦源 | Pyerite不是pyrite黃鐵礦 |
| Pyroxeres | 基礎ore | 名稱像pyroxene輝石，不等於同物 |
| Plagioclase | 遊戲ore | 現實斜長石確實存在，但配方不同 |
| Kernite、Jaspet | 遊戲ore | 現實kernite與jasper存在，性質不同 |
| Gneiss、Dark Ochre | 高階ore名稱 | 現實是片麻岩與赭石概念 |
| Bistot、Arkonor、Spodumain | 稀缺工業礦 | Spodumain不是spodumene鋰輝石 |
| Mercoxit → Morphite | 特殊高階供應 | 應視為New Eden虛構材料 |
| Isogen、Nocxium、Zydrine、Megacyte | 高階基礎minerals | 不是週期表元素 |

EVE的reprocessing把破碎、選礦、冶煉、化學分離與回收壓成一次操作。現實中真正昂貴的常不是「礦石存在」，而是品位、能源、雜質、尾礦、設備、環保與穩定量產。

## T1：設計主檔與量產

- BPO：可研究、可重複使用的藍圖原本。
- BPC：繼承複製時效率、只有有限licensed runs的工作副本。
- Material Efficiency：減少遊戲材料需求，但有上限與遞減研究時間。
- Manufacturing：依藍圖、物料、設施、位置與成本產出物品。

現實最接近BOM、受控圖面、製程路線、授權檔與工廠排程，但真工業還有公差、良率、報廢、供應商驗證與品質認證。

## T2：月球材料、反應與發明

T2通常從T1 BPC進行invention，以datacores和可選decryptor取得有限次T2 BPC，再使用moon-material reactions形成的中間材料與專用components製造。

Technetium、Promethium、Dysprosium等名稱來自真實元素，但New Eden的礦床與反應是虛構的。現實technetium與promethium沒有穩定同位素；dysprosium是稀土元素。遊戲曾因配方調整讓稀缺材料價格大幅轉移，正好展示供應鏈瓶頸的市場效應。

## T3：考古、氣體與模組化

Ancient Relics與wormhole datacores用於發明T3 BPC，Fullerite gases經hybrid reactions形成advanced materials，再與Sleeper來源零件構成Strategic Cruisers、Tactical Destroyers及subsystems。

現實fullerene是籠狀碳分子，fullerite通常指固態分子晶體，並不是可從蟲洞氣雲直接收集的戰艦材料。T3的模組化概念有工程意義，但真實共通介面會付出重量、熱控、結構與認證成本。

## PI完整產品層級

### P0 → P1

| P0 raw resource | P1 processed material |
|---|---|
| Aqueous Liquids | Water |
| Autotrophs | Industrial Fibers |
| Base Metals | Reactive Metals |
| Carbon Compounds | Biofuels |
| Complex Organisms | Proteins |
| Felsic Magma | Silicon |
| Heavy Metals | Toxic Metals |
| Ionic Solutions | Electrolytes |
| Micro Organisms | Bacteria |
| Noble Gas | Oxygen |
| Noble Metals | Precious Metals |
| Non-CS Crystals | Chiral Structures |
| Planktic Colonies | Biomass |
| Reactive Gas | Oxidizing Compound |
| Suspended Plasma | Plasmoids |

### P2 refined commodities

Biocells、Construction Blocks、Consumer Electronics、Coolant、Enriched Uranium、Fertilizer、Genetically Enhanced Livestock、Livestock、Mechanical Parts、Microfiber Shielding、Miniature Electronics、Nanites、Oxides、Polyaramids、Polytextiles、Rocket Fuel、Silicate Glass、Superconductors、Supertensile Plastics、Synthetic Oil、Test Cultures、Transmitter、Viral Agent、Water-Cooled CPU。

### P3 specialized commodities

Biotech Research Reports、Camera Drones、Condensates、Cryoprotectant Solution、Data Chips、Gel-Matrix Biopaste、Guidance Systems、Hazmat Detection Systems、Hermetic Membranes、High-Tech Transmitters、Industrial Explosives、Neocoms、Nuclear Reactors、Planetary Vehicles、Robotics、Smartfab Units、Supercomputers、Synthetic Synapses、Transcranial Microcontrollers、Ukomi Superconductors、Vaccines。

### P4 advanced commodities

Broadcast Node、Integrity Response Drones、Nano-Factory、Organic Mortar Applicators、Recursive Computing Module、Self-Harmonizing Power Core、Sterile Conduits、Wetware Mainframe。

這些同名詞只代表EVE庫存物品，不能直接套用現實配方。尤其Enriched Uranium、Nuclear Reactors、Vaccines與Superconductors在現實中都有嚴格材料、製程、法規和品質要求。

## PI與現實ISRU

PI把勘探、開採、加工、能源與上軌道物流簡化成熱點、建築連線與CPU／powergrid配置。NASA的ISRU則仍優先處理可驗證且任務價值高的水、氧、甲烷、金屬、矽與建材；月壤含大量與礦物結合的氧，但要以高溫或化學製程分離。

現實世界不會直接從行星表面吐出「Robotics」。必須先取得元素與化合物，再經過材料純化、晶片、馬達、感測器、軟體、組裝與測試。EVE最真實的地方不是配方，而是它讓玩家感受到：**任何高科技最後都站在一條又長又脆弱的供應鏈上。**

## 出處

- EVE Online Support：Industry、Blueprints、Copying、Manufacturing、Invention、Datacores、Ancient Relics、Reactions、Planetary Interaction。
- EVE Online官方新聞：From Extraction to Production、Moon Mineral Distribution Update、Quarterly Economic Newsletter。
- EVE Developer Documentation：Static Data Export；物品名稱與配方會隨Tranquility版本更新。
- NASA：In-Situ Resource Utilization與Lunar Surface Technology。
- USGS：Mineral Commodity Summaries 2026。
- IUPAC：Periodic Table of Elements。
- PubChem：Fullerene。
