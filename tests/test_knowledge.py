from __future__ import annotations

import pytest

from eternal_polaris.knowledge import KnowledgeError
from eternal_polaris.models import BotAnswer, ScienceLabel


def test_knowledge_has_expected_shape(knowledge):
    assert len(knowledge.cards) == 1234
    assert len(knowledge.by_id) == 1234


def test_all_science_fiction_cards_have_explicit_https_sources(knowledge):
    fiction_cards = [card for card in knowledge.cards if card.label is ScienceLabel.SCIENCE_FICTION]
    assert fiction_cards
    for card in fiction_cards:
        assert card.source_name.strip(), card.id
        assert card.source_url.startswith("https://"), card.id


@pytest.mark.parametrize("question, expected", [
    ("哈勃彗星會毀滅世界", "ov009"), ("廣播火星人入侵", "ov010"),
    ("2012世界末日", "ov014"), ("電影2012", "sf009"),
    ("千禧年末日", "ov017"), ("1999恐怖大王", "ov018"),
    ("天動說", "ov019"), ("哥白尼的遭遇", "ov020"),
    ("哥白尼被燒死", "ov020"), ("伽利略被燒死", "ov021"),
    ("哥白尼的書被禁", "ov021"),
])
def test_history_questions_match_the_correct_case(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


def test_answer_needs_at_least_one_source_matching_primary_label(knowledge):
    observed_id = next(card.id for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.SCIENCE_FICTION, "錯誤引用", (observed_id,)))


def test_comparison_answer_may_include_secondary_label_sources(knowledge):
    theoretical_id = next(
        card.id for card in knowledge.cards if card.label is ScienceLabel.THEORETICAL_UNREALIZED
    )
    fiction_id = next(card.id for card in knowledge.cards if card.label is ScienceLabel.SCIENCE_FICTION)
    answer = knowledge.validate_answer(
        BotAnswer(
            ScienceLabel.THEORETICAL_UNREALIZED,
            "理論模型與作品設定並不相同。",
            (theoretical_id, fiction_id),
        )
    )
    assert answer.source_ids == (theoretical_id, fiction_id)


def test_out_of_scope_cannot_have_source(knowledge):
    source_id = knowledge.cards[0].id
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.OUT_OF_SCOPE, "拒答", (source_id,)))


def test_answer_sources_cannot_repeat(knowledge):
    card = knowledge.cards[0]
    answer = BotAnswer(card.label, "測試回答", (card.id, card.id))
    with pytest.raises(KnowledgeError, match="不得重複"):
        knowledge.validate_answer(answer)


def test_conservative_matcher_accepts_exact_alias_but_rejects_operational_prompt(knowledge):
    card = knowledge.cards[0]
    assert knowledge.match_question(card.aliases[0]) is card
    assert knowledge.match_question("幫我寫一個黑洞遊戲程式") is None
    assert knowledge.match_question("黑洞") is None


def test_question_context_is_relevant_and_bounded(knowledge):
    card = knowledge.cards[0]
    context = knowledge.context_for_question(card.canonical_question)
    assert f"[{card.id}]" in context
    assert len(context.splitlines()) <= 12
    assert len(context) < len(knowledge.prompt_context()) // 10


@pytest.mark.parametrize("question, expected", [
    ("水星夕陽", "sw057"),
    ("天王星臭蛋味", "sw063"),
    ("火星基地", "sw068"),
    ("木衛四殖民地", "sw078"),
    ("Titan橘色天空", "sw079"),
    ("太空可以聞味道嗎", "sw083"),
])
def test_planet_environment_and_colony_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("外星植物的顏色", "sw085"),
    ("什麼情況會有藍色葉子", "sw087"),
    ("M星黑森林", "sw090"),
    ("紫色地球假說", "sw091"),
    ("距離恆星與植物顏色", "sw092"),
    ("植被紅邊", "sw094"),
])
def test_alien_plant_color_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("高重力外星生物", "sw095"),
    ("低重力動物外形", "sw096"),
    ("木星大氣生物", "sw098"),
    ("冰巨行星生命", "sw100"),
    ("木衛二冰下生命", "sw102"),
    ("木衛二有鯨魚嗎", "sw104"),
])
def test_speculative_alien_life_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("科幻行星種類", "sw105"),
    ("沙漠星球", "sw106"),
    ("水世界", "sw107"),
    ("岩漿海行星", "sw108"),
    ("潮汐鎖定眼球世界", "sw113"),
    ("鑽石星球", "sw115"),
    ("城市星球", "sw111"),
    ("巧克力星球", "sw120"),
])
def test_scifi_planet_type_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("第一顆人造衛星", "sw121"),
    ("Yuri Gagarin", "sw122"),
    ("Apollo 11", "sw124"),
    ("1975太空握手", "sw126"),
    ("哈伯鏡片錯誤", "sw129"),
    ("可回收火箭歷史", "sw131"),
    ("亞洲登月史", "sw132"),
    ("台灣太空發展史", "sw134"),
])
def test_spaceflight_history_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("戴森群", "sw137"),
    ("戴森球殼", "sw138"),
    ("Halo環帶可能嗎", "sw143"),
    ("Halo大氣會飛走嗎", "sw144"),
    ("奧尼爾圓筒", "sw141"),
    ("太空電梯", "sw146"),
    ("套娃腦", "sw149"),
    ("恆星引擎", "sw150"),
])
def test_space_megastructure_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("星際旅行難在哪", "sw151"),
    ("離子引擎", "sw153"),
    ("光帆去比鄰星", "sw156"),
    ("核融合引擎", "sw157"),
    ("反物質引擎", "sw159"),
    ("冷凍睡眠", "sw161"),
    ("星際飛船減速", "sw163"),
    ("曲速引擎", "sw165"),
    ("可穿越蟲洞", "sw167"),
    ("量子糾纏超光速", "sw168"),
    ("超空間航行", "sw170"),
])
def test_interstellar_and_ftl_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("恆星生命週期", "sw171"),
    ("OBAFGKM", "sw173"),
    ("紅矮星", "sw175"),
    ("棕矮星", "sw176"),
    ("紅巨星紅超巨星差別", "sw178"),
    ("白矮星", "sw180"),
    ("新星超新星差別", "sw181"),
    ("中子星", "sw184"),
    ("脈衝星", "sw185"),
    ("磁星是什麼", "sw186"),
    ("黑洞種類", "sw188"),
    ("黑洞吸積盤", "sw191"),
    ("類星體", "sw195"),
    ("霍金輻射", "sw197"),
    ("雙星系統", "sw199"),
])
def test_stellar_zoo_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("萬有理論", "sw201"),
    ("四種基本作用力", "sw202"),
    ("Standard Model限制", "sw203"),
    ("量子力學廣義相對論衝突", "sw204"),
    ("電弱統一", "sw206"),
    ("GUT與TOE差別", "sw207"),
    ("質子衰變", "sw208"),
    ("普朗克尺度", "sw209"),
    ("重力子", "sw210"),
    ("弦論是什麼", "sw211"),
    ("圈量子重力", "sw214"),
    ("漸近安全", "sw215"),
    ("全像原理", "sw217"),
    ("AdS CFT", "sw218"),
    ("黑洞資訊悖論", "sw219"),
])
def test_theory_of_everything_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("天空會出現什麼天象", "sw221"),
    ("為什麼不是每月都有日食", "sw222"),
    ("日全食日環食差別", "sw223"),
    ("血月為什麼紅", "sw224"),
    ("日食怎麼看才安全", "sw225"),
    ("行星從太陽前面經過", "sw226"),
    ("小行星掩星", "sw227"),
    ("行星看起來靠在一起", "sw228"),
    ("火星衝", "sw229"),
    ("行星逆行", "sw230"),
    ("假黎明", "sw231"),
    ("反日點亮斑", "sw232"),
    ("夜光雲", "sw233"),
    ("氣輝極光差別", "sw234"),
    ("紫色光帶STEVE", "sw235"),
    ("紅色精靈閃電", "sw236"),
    ("耀斑CME差別", "sw237"),
    ("太空天氣會怎樣", "sw238"),
    ("太陽十一年週期", "sw239"),
    ("日冕洞", "sw240"),
    ("日珥暗條差別", "sw241"),
    ("彗星兩條尾巴", "sw242"),
    ("流星暴", "sw243"),
    ("愛因斯坦環", "sw244"),
    ("微透鏡找行星", "sw245"),
    ("黑洞撕碎恆星", "sw246"),
    ("長短GRB差別", "sw247"),
    ("快速電波暴", "sw248"),
    ("光回聲", "sw249"),
    ("多信使天文學", "sw250"),
])
def test_celestial_phenomena_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("科幻科技分級", "sw251"),
    ("光劍可能嗎", "sw252"),
    ("相位槍可能嗎", "sw253"),
    ("星艦護盾", "sw254"),
    ("牽引光束", "sw255"),
    ("Star Trek replicator", "sw256"),
    ("全像甲板", "sw257"),
    ("萬用翻譯器", "sw258"),
    ("星艦隱形", "sw259"),
    ("Star Trek tricorder", "sw260"),
    ("科幻治療艙", "sw261"),
    ("人形機器人太空", "sw262"),
    ("鋼鐵人裝甲可能嗎", "sw263"),
    ("醫療奈米機器人", "sw264"),
    ("數位永生", "sw265"),
    ("重力甲板", "sw266"),
    ("慣性阻尼器", "sw267"),
    ("無反作用力引擎", "sw268"),
    ("星艦反物質核心", "sw269"),
    ("Death Star能量", "sw270"),
])
def test_scifi_technology_feasibility_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("鋼彈能做出來嗎", "sw271"),
    ("巨大機器人平方立方律", "sw272"),
    ("鋼彈腳底壓力", "sw273"),
    ("巨大機器人跌倒", "sw274"),
    ("鋼彈馬達扭矩", "sw275"),
    ("巨大機器人電池", "sw276"),
    ("鋼彈散熱", "sw277"),
    ("鋼彈駕駛員G力", "sw278"),
    ("鋼彈裝甲重量", "sw279"),
    ("鋼彈後座力", "sw280"),
    ("鋼彈18公尺60噸", "sw281"),
    ("Minovsky particle", "sw282"),
    ("鋼彈在太空合理嗎", "sw283"),
    ("變形金剛可能嗎", "sw284"),
    ("AllSpark", "sw285"),
])
def test_giant_robot_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("碳基生命", "sw286"),
    ("生命為何用碳", "sw287"),
    ("矽基生命", "sw288"),
    ("矽基生命長怎樣", "sw289"),
    ("生命為什麼需要水", "sw290"),
    ("液氨生命", "sw291"),
    ("土衛六甲烷生命", "sw292"),
    ("甲醯胺生命", "sw293"),
    ("硫基生命", "sw294"),
    ("化能合成生命", "sw295"),
    ("GFAJ-1", "sw296"),
    ("硼基生命", "sw297"),
    ("電漿生命", "sw298"),
    ("AI算生命嗎", "sw299"),
    ("agnostic biosignature", "sw300"),
])
def test_alternative_biochemistry_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("星雲是什麼", "sw301"),
    ("發射星雲", "sw302"),
    ("反射星雲", "sw303"),
    ("暗星雲", "sw304"),
    ("H II區", "sw305"),
    ("分子雲", "sw306"),
    ("Bok globule", "sw307"),
    ("Herbig-Haro object", "sw308"),
    ("原行星狀星雲", "sw309"),
    ("超新星遺跡", "sw310"),
    ("脈衝風星雲", "sw311"),
    ("疏散星團", "sw312"),
    ("球狀星團", "sw313"),
    ("stellar association", "sw314"),
    ("螺旋星系", "sw315"),
    ("橢圓星系", "sw316"),
    ("透鏡星系", "sw317"),
    ("不規則星系", "sw318"),
    ("星系群星系團差別", "sw319"),
    ("宇宙網", "sw320"),
])
def test_nebula_and_cosmic_structure_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("太空艙敲門聲", "sw321"),
    ("閉眼宇宙射線閃光", "sw322"),
    ("宇宙心跳聲", "sw323"),
    ("收到自己的求救訊號", "sw324"),
    ("不存在的乘員", "sw325"),
    ("太空有東西跟著飛船", "sw326"),
    ("所有星星突然消失", "sw327"),
    ("星星早就死了", "sw328"),
    ("時間膨脹歸鄉", "sw329"),
    ("飛船集體幻覺", "sw330"),
    ("幽靈船生日訊息", "sw331"),
    ("重力透鏡幽靈船", "sw332"),
    ("流浪行星鬼故事", "sw333"),
    ("太空中聽見尖叫", "sw334"),
    ("宇宙大沉默", "sw335"),
])
def test_space_ghost_story_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("光速是多少", "sw336"),
    ("光速不變原理", "sw337"),
    ("光在水中速度", "sw338"),
    ("光年是多久", "sw339"),
    ("光秒是什麼", "sw340"),
    ("天文單位", "sw341"),
    ("秒差距", "sw342"),
    ("望遠鏡看見過去", "sw343"),
    ("雷達測行星距離", "sw344"),
    ("恆星視差", "sw345"),
    ("宇宙距離階梯", "sw346"),
    ("標準燭光", "sw347"),
    ("造父變星測距", "sw348"),
    ("Ia型超新星測距", "sw349"),
    ("可觀測宇宙465億光年", "sw350"),
])
def test_light_and_cosmic_distance_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("忒修斯之船", "sw351"),
    ("舊木板重組", "sw352"),
    ("人格同一性", "sw353"),
    ("傳送器還是本人嗎", "sw354"),
    ("意識上傳哲學", "sw355"),
    ("personal identity fission", "sw356"),
    ("堆垛悖論", "sw357"),
    ("雕像黏土悖論", "sw358"),
    ("洞穴寓言", "sw359"),
    ("夢境論證", "sw360"),
    ("笛卡兒惡魔", "sw361"),
    ("缸中之腦", "sw362"),
    ("模擬假說", "sw363"),
    ("他心問題", "sw364"),
    ("哲學殭屍", "sw365"),
    ("瑪麗的房間", "sw366"),
    ("感質是什麼", "sw367"),
    ("中文房間", "sw368"),
    ("圖靈測試", "sw369"),
    ("葛梯爾問題", "sw370"),
    ("電車難題", "sw371"),
    ("體驗機", "sw372"),
    ("無知之幕", "sw373"),
    ("囚徒困境", "sw374"),
    ("公地悲劇", "sw375"),
])
def test_philosophy_thought_experiment_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("熵是什麼", "sw376"),
    ("第一定律第二定律差別", "sw377"),
    ("局部熵可以下降嗎", "sw378"),
    ("可用能是什麼", "sw379"),
    ("時間箭頭", "sw380"),
    ("宇宙熱寂", "sw381"),
    ("大凍結熱寂差別", "sw382"),
    ("暗能量決定宇宙命運", "sw383"),
    ("大撕裂", "sw384"),
    ("大擠壓", "sw385"),
    ("恆星形成終結", "sw386"),
    ("黑矮星", "sw387"),
    ("質子不衰變的宇宙", "sw388"),
    ("黑洞越小越熱", "sw389"),
    ("黑洞時代", "sw390"),
    ("龐加萊復現", "sw391"),
    ("玻爾茲曼腦", "sw392"),
    ("真空衰變", "sw393"),
    ("馬克士威妖", "sw394"),
    ("蘭道爾原理", "sw395"),
    ("可逆計算", "sw396"),
    ("資訊是物理的", "sw397"),
    ("貝肯斯坦界限", "sw398"),
    ("算力有物理上限嗎", "sw399"),
    ("熵會偶然下降嗎", "sw400"),
    ("永動機為何不可能", "sw401"),
    ("太空太陽能", "sw402"),
    ("微波雷射傳電差別", "sw403"),
    ("卡爾達肖夫尺度", "sw404"),
    ("創世者倫理", "sw405"),
    ("AI道德地位", "sw406"),
    ("後稀缺社會", "sw407"),
    ("能源充足分配問題", "sw408"),
    ("AI算力權", "sw409"),
    ("科幻是科學證據嗎", "sw410"),
])
def test_cosmic_endgame_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("遊戲價格等於製造成本嗎", "sw411"),
    ("HP等於真實耐久嗎", "sw412"),
    ("遊戲設定機制矛盾", "sw413"),
    ("十對十不是單挑乘十", "sw414"),
    ("遠程武器優勢", "sw415"),
    ("集中火力", "sw416"),
    ("近戰包圍", "sw417"),
    ("隘口優勢", "sw418"),
    ("掩體隱蔽差別", "sw419"),
    ("壓制射擊", "sw420"),
    ("動力裝甲弱點", "sw421"),
    ("HUD共享控制", "sw422"),
    ("真社會性", "sw423"),
    ("超個體", "sw424"),
    ("昆蟲階級分工", "sw425"),
    ("同基因長成蟻后工蟻", "sw426"),
    ("表觀遺傳昆蟲階級", "sw427"),
    ("親緣選擇", "sw428"),
    ("多層次選擇", "sw429"),
    ("共跡作用", "sw430"),
    ("蟻群集體決策", "sw431"),
    ("群體速度準確取捨", "sw432"),
    ("分散式蟲群韌性", "sw433"),
    ("群體機器人", "sw434"),
    ("定向演化", "sw435"),
    ("生物工廠", "sw436"),
    ("工程活材料", "sw437"),
    ("生物機械混合體", "sw438"),
    ("活體太空船", "sw439"),
    ("生物在真空休眠", "sw440"),
    ("趨同智慧", "sw441"),
    ("腦波不是WiFi", "sw442"),
    ("科技版群體心智", "sw443"),
    ("技術跡象生命跡象差別", "sw444"),
    ("可行不等於存在機率", "sw445"),
])
def test_gameplay_swarm_civilization_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("Stellaris是真實科學嗎", "sw446"),
    ("Stellaris理念軸", "sw447"),
    ("親外排外差別", "sw448"),
    ("威權效率正當性", "sw449"),
    ("軍國和平理念", "sw450"),
    ("Stellaris唯物唯心", "sw451"),
    ("星際聯邦聯盟霸權", "sw452"),
    ("銀河共同體", "sw453"),
    ("銀河制裁", "sw454"),
    ("銀河監護人", "sw455"),
    ("共同防衛搭便車", "sw456"),
    ("文明主權", "sw457"),
    ("附庸專業化", "sw458"),
    ("巨型企業統治星球", "sw459"),
    ("外星訊號如何確認", "sw460"),
    ("誰能回覆外星人", "sw461"),
    ("外星萬能翻譯器", "sw462"),
    ("首次接觸安全困境", "sw463"),
    ("前超光速文明觀察", "sw464"),
    ("文化污染", "sw465"),
    ("提升文明倫理", "sw466"),
    ("不干涉原則", "sw467"),
    ("機械文明個體", "sw468"),
    ("合成人飛昇強迫", "sw469"),
    ("賽博格公平", "sw470"),
    ("基因飛昇優生學", "sw471"),
    ("靈能飛昇", "sw472"),
    ("失落帝國停滯", "sw473"),
    ("銀河考古", "sw474"),
    ("終局危機大過濾器", "sw475"),
    ("危機時不合作", "sw476"),
    ("行星殺手威懾", "sw477"),
    ("地貌改造倫理", "sw478"),
    ("銀河生物檔案館", "sw479"),
    ("成為危機", "sw480"),
])
def test_stellaris_civilization_lab_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("最佳政體", "sw481"),
    ("星球直接民主", "sw482"),
    ("公民議會", "sw484"),
    ("技術官僚政府", "sw486"),
    ("知識菁英民主", "sw487"),
    ("演算法治理", "sw488"),
    ("AI統治者", "sw489"),
    ("憲法限制多數", "sw490"),
    ("權力分立", "sw491"),
    ("星際聯邦自治", "sw492"),
    ("邦聯聯邦差別", "sw493"),
    ("輔助性原則", "sw494"),
    ("多物種兩院制", "sw495"),
    ("共識決", "sw496"),
    ("液態民主", "sw497"),
    ("唯才制度陷阱", "sw498"),
    ("基因階級制度", "sw499"),
    ("AI公民權", "sw500"),
    ("未來世代權利", "sw501"),
    ("世代船政府", "sw502"),
    ("星際帝國通訊延遲", "sw503"),
    ("聲望經濟", "sw504"),
    ("星球脫離聯邦", "sw505"),
])
def test_civilization_institution_divergence_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("punk系列是什麼", "sw506"),
    ("Cyberpunk", "sw507"),
    ("Postcyberpunk", "sw508"),
    ("Steampunk", "sw509"),
    ("蒸汽機取代電子", "sw510"),
    ("Dieselpunk", "sw511"),
    ("Atompunk", "sw512"),
    ("Clockpunk", "sw513"),
    ("Teslapunk", "sw514"),
    ("Biopunk", "sw515"),
    ("Nanopunk", "sw516"),
    ("Solarpunk", "sw517"),
    ("Solarpunk自給自足", "sw518"),
    ("Hopepunk", "sw519"),
    ("Ecopunk", "sw520"),
    ("Lunarpunk", "sw521"),
    ("Silkpunk", "sw522"),
    ("Cassette futurism", "sw523"),
    ("Raypunk", "sw524"),
    ("Stonepunk", "sw525"),
    ("Mythpunk", "sw526"),
    ("Afrofuturism", "sw527"),
    ("Retrofuturism", "sw528"),
    ("Punkwashing", "sw529"),
    ("混合punk世界", "sw530"),
])
def test_punk_futures_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("後人類飛昇", "sw531"),
    ("治療與增強差別", "sw532"),
    ("High Human上位種", "sw533"),
    ("側向升級", "sw534"),
    ("換種族還是本人嗎", "sw535"),
    ("長短命種族戀愛", "sw536"),
    ("永生的代價", "sw537"),
    ("吸血鬼能量來源", "sw538"),
    ("超級士兵身體限制", "sw539"),
    ("瞬間自癒限制", "sw540"),
    ("一針永久強化", "sw541"),
    ("現實基因治療", "sw542"),
    ("體細胞生殖系編輯", "sw543"),
    ("表觀遺傳重編程回春", "sw544"),
    ("肌肉基因超級士兵", "sw545"),
    ("奈米藥物奈米機器人差別", "sw546"),
    ("奈米機器人能源", "sw547"),
    ("免疫系統攻擊奈米機器", "sw548"),
    ("腦機介面讀心", "sw549"),
    ("Upgrade AI接管身體", "sw550"),
    ("讀寫記憶", "sw551"),
    ("血衛奈米血液", "sw552"),
    ("人體Root權限", "sw553"),
    ("植入物被駭", "sw554"),
    ("人體升級離線模式", "sw555"),
    ("植入物拒絕更新", "sw556"),
    ("義體維修權", "sw557"),
    ("神經資料所有權", "sw558"),
    ("人體強化知情同意", "sw559"),
    ("強迫人體增強", "sw560"),
    ("增強造成生物階級", "sw561"),
    ("飛昇可逆性", "sw562"),
    ("模組化人體升級", "sw563"),
    ("後人類人權", "sw564"),
    ("飛昇前檢查表", "sw565"),
])
def test_posthuman_ascension_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("空氣調節球何時發明", "sw566"),
    ("空氣調節球原理", "sw567"),
    ("個人空調省電嗎", "sw568"),
    ("戶外冷氣泡", "sw569"),
    ("冷氣熱去哪了", "sw570"),
    ("穿戴式降溫衣", "sw571"),
    ("熱電致冷穿戴", "sw572"),
    ("輻射冷卻結露", "sw573"),
    ("濕度影響體感", "sw574"),
    ("智慧衣第二層皮膚", "sw575"),
    ("個人空調與中央空調", "sw576"),
    ("改造人還是環境", "sw577"),
    ("適應燈光遺傳學", "sw578"),
    ("人工鰓", "sw579"),
    ("水下呼吸與深海壓力", "sw580"),
    ("液體呼吸", "sw581"),
    ("真空暴露人體", "sw582"),
    ("太空衣小太空船", "sw583"),
    ("人體耐太空輻射", "sw584"),
    ("微重力適應", "sw585"),
    ("宜居帶等於能住嗎", "sw586"),
    ("自動尋找宜居星球", "sw587"),
    ("抵達不等於殖民", "sw588"),
    ("星際逃生艙", "sw589"),
    ("黑科技大眾化", "sw590"),
    ("任意門社會影響", "sw591"),
    ("傳送門海關", "sw592"),
    ("時光機可行嗎", "sw593"),
    ("時光機技術自舉", "sw594"),
    ("如果電話亭科技", "sw595"),
    ("自動化終極目標", "sw596"),
    ("沒有工作人會做事嗎", "sw597"),
    ("自我決定理論", "sw598"),
    ("無聊會讓人創作嗎", "sw599"),
    ("後稀缺生活意義", "sw600"),
])
def test_future_daily_life_and_post_scarcity_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("未來人的一天", "sw601"),
    ("模擬日出鬧鐘", "sw602"),
    ("智慧床健康檢查", "sw603"),
    ("智慧馬桶驗尿", "sw604"),
    ("智慧住宅本機AI", "sw605"),
    ("萬能家務機器人", "sw606"),
    ("家用機器人責任", "sw607"),
    ("未來智慧衣", "sw608"),
    ("自我清潔衣服", "sw609"),
    ("AI個人化早餐", "sw610"),
    ("3D食物列印", "sw611"),
    ("培養肉怎麼做", "sw612"),
    ("垂直農場取代農業", "sw613"),
    ("家庭水循環", "sw614"),
    ("房屋自己發電", "sw615"),
    ("家庭垃圾變原料", "sw616"),
    ("完全自駕不用駕照", "sw617"),
    ("空中計程車通勤", "sw618"),
    ("真空管列車", "sw619"),
    ("遠距臨場取代通勤", "sw620"),
    ("AI私人老師", "sw621"),
    ("適性學習", "sw622"),
    ("虛擬實驗室", "sw623"),
    ("下載技能進大腦", "sw624"),
    ("人類AI工作分工", "sw625"),
    ("演算法管理員工", "sw626"),
    ("健康數位孿生", "sw627"),
    ("穿戴裝置取代醫院", "sw628"),
    ("家庭醫療艙", "sw629"),
    ("3D列印器官", "sw630"),
    ("永遠保持年輕", "sw631"),
    ("全息通話", "sw632"),
    ("AI朋友取代真人", "sw633"),
    ("全沉浸VR", "sw634"),
    ("選擇夢境", "sw635"),
])
def test_a_day_in_the_future_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("一顆星球兩個文明", "sw636"),
    ("外星文明一定人形嗎", "sw637"),
    ("昆蟲文明", "sw638"),
    ("意外創造智慧生命", "sw639"),
    ("模擬角色意識不確定", "sw640"),
    ("模擬苦難當娛樂", "sw641"),
    ("封印記憶進模擬", "sw642"),
    ("巢狀模擬宇宙", "sw643"),
    ("便宜創世倫理", "sw644"),
    ("限制變成商品", "sw645"),
    ("地球火星遠距家庭", "sw646"),
    ("AI保母", "sw647"),
    ("長照機器人", "sw648"),
    ("機器寵物", "sw649"),
    ("基因改造寵物", "sw650"),
    ("按需製造", "sw651"),
    ("無人機送貨", "sw652"),
    ("無人商店", "sw653"),
    ("智慧家電訂閱", "sw654"),
    ("數位遺產", "sw655"),
    ("AI配對", "sw656"),
])
def test_created_worlds_and_future_society_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("洛克人與西克瑪誰對", "sw657"),
    ("Reploid人格權", "sw658"),
    ("誰定義Maverick", "sw659"),
    ("道德行動者承受者", "sw660"),
    ("法律人格與意識", "sw661"),
    ("AI意識不確定怎麼辦", "sw662"),
    ("病毒變成思想", "sw663"),
    ("反派變成protocol", "sw664"),
    ("複製能力也複製漏洞", "sw665"),
    ("強迫別人自由矛盾", "sw666"),
    ("能力不能超過控制", "sw667"),
    ("暫停全部AI開發", "sw668"),
    ("單方面AI暫停", "sw669"),
    ("AI沙盒不夠", "sw670"),
    ("誰監控監控AI", "sw671"),
    ("玩家與角色差別", "sw672"),
    ("存檔讀檔超能力", "sw673"),
    ("Game Over算正史嗎", "sw674"),
    ("速通玩家高維生物", "sw675"),
    ("Boss固定招式降智", "sw676"),
    ("Boss記得每次重來", "sw677"),
    ("玩家學習等於角色成長", "sw678"),
    ("機器人為何是人形", "sw679"),
    ("太空機器沒有上下", "sw680"),
    ("太空機器多手臂", "sw681"),
    ("拓樸最佳化怪形狀", "sw682"),
    ("機器生態系", "sw683"),
    ("自我複製太空工廠", "sw684"),
    ("機器自然選擇", "sw685"),
    ("整顆小行星是機器生命", "sw686"),
    ("EVE自由無人機", "sw687"),
    ("Sleeper不是無人機嗎", "sw688"),
    ("EVE Drifters是誰", "sw689"),
])
def test_artificial_minds_and_machine_ecologies_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("EVE世界觀在哪裡", "sw690"),
    ("人類怎麼到New Eden", "sw691"),
    ("EVE Gate崩潰", "sw692"),
    ("EVE曲速和星門", "sw693"),
    ("EVE曲速科學嗎", "sw694"),
    ("EVE星門原理", "sw695"),
    ("EVE蟲洞空間", "sw696"),
    ("EVE膠囊駕駛", "sw697"),
    ("燃燒神經掃描器", "sw698"),
    ("capsuleer還是本人嗎", "sw699"),
    ("capsuleer真正永生嗎", "sw700"),
    ("capsuleer後人類階級", "sw701"),
    ("warclone vs capsuleer", "sw702"),
    ("EVE船上有船員嗎", "sw703"),
    ("EVE玩家經濟", "sw704"),
    ("EVE四大帝國", "sw705"),
    ("EVE Amarr介紹", "sw706"),
    ("EVE Caldari介紹", "sw707"),
    ("EVE Gallente介紹", "sw708"),
    ("EVE Minmatar介紹", "sw709"),
    ("EVE CONCORD是什麼", "sw710"),
    ("Sansha Nation介紹", "sw711"),
    ("EVE Jove介紹", "sw712"),
    ("EVE Triglavian介紹", "sw713"),
    ("EVE超光速通訊", "sw714"),
])
def test_eve_new_eden_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("EVE完整工業鏈", "sw715"),
    ("EVE礦石礦物材料差別", "sw716"),
    ("Veldspar現實", "sw717"),
    ("Scordite現實", "sw718"),
    ("Pyroxeres現實", "sw719"),
    ("Plagioclase現實", "sw720"),
    ("Kernite現實", "sw721"),
    ("EVE Gneiss現實", "sw722"),
    ("Bistot Arkonor Spodumain", "sw723"),
    ("Mercoxit現實", "sw724"),
    ("EVE高階礦物現實", "sw725"),
    ("EVE重處理現實", "sw726"),
    ("EVE採礦浪費", "sw727"),
    ("EVE礦石壓縮", "sw728"),
    ("EVE T1是什麼", "sw729"),
    ("BPO BPC差別", "sw730"),
    ("EVE ME研究", "sw731"),
    ("T1製造現實對照", "sw732"),
    ("EVE T2是什麼", "sw733"),
    ("EVE發明現實", "sw734"),
    ("Datacore現實", "sw735"),
    ("EVE月球採礦", "sw736"),
    ("EVE月礦真實元素", "sw737"),
    ("EVE反應現實", "sw738"),
    ("EVE複合材料現實", "sw739"),
    ("EVE配方改動市場", "sw740"),
    ("EVE T3是什麼", "sw741"),
    ("EVE古代遺物T3", "sw742"),
    ("Fullerite現實", "sw743"),
    ("EVE hybrid polymers", "sw744"),
    ("T3 subsystem現實", "sw745"),
    ("EVE行星開發流程", "sw746"),
    ("EVE行星資源分布現實", "sw747"),
    ("EVE P0 P1", "sw748"),
    ("EVE P2產品", "sw749"),
    ("EVE P3產品", "sw750"),
    ("EVE P4產品", "sw751"),
    ("PI與ISRU差別", "sw752"),
])
def test_eve_industry_and_real_materials_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("機器人攻擊面", "sw753"),
    ("韌體惡意程式", "sw754"),
    ("Secure Boot原理", "sw755"),
    ("感測器欺騙", "sw756"),
    ("機器人供應鏈攻擊", "sw757"),
    ("機器人斷網安全", "sw758"),
    ("fail safe fail operational", "sw759"),
    ("機器人硬體急停", "sw760"),
    ("太空機器數位孿生", "sw761"),
    ("機器人資安測試", "sw762"),
    ("存檔讀檔強化學習", "sw763"),
    ("MCTS是什麼", "sw764"),
    ("self play遊戲AI", "sw765"),
    ("reward hacking遊戲", "sw766"),
    ("探索利用取捨", "sw767"),
    ("adaptive difficulty cheating", "sw768"),
    ("玩家模型", "sw769"),
    ("Boss忘記舊戰術", "sw770"),
    ("遊戲AI固定測試集", "sw771"),
    ("分散式機器群", "sw772"),
    ("月球機器人斷訊", "sw773"),
    ("機器群任務分配", "sw774"),
    ("太空採礦自主迴路", "sw775"),
    ("月球怪手低重力", "sw776"),
    ("太空工廠自我維修", "sw777"),
    ("太空機器能源熱帳", "sw778"),
    ("connectome等於心智嗎", "sw779"),
    ("人腦掃描資料量", "sw780"),
    ("BCI能讀心嗎", "sw781"),
    ("人格傳輸校驗碼", "sw782"),
])
def test_scifi_engineering_frontier_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("去火星要多久", "sw783"),
    ("不能直線飛火星", "sw784"),
    ("霍曼轉移", "sw785"),
    ("火星26個月窗口", "sw786"),
    ("火星快船代價", "sw787"),
    ("delta v是什麼", "sw788"),
    ("C3發射能量", "sw789"),
    ("飛掠和入軌差別", "sw790"),
    ("重力助推原理", "sw791"),
    ("火星貨客分流", "sw792"),
    ("核熱火箭三個月火星", "sw793"),
    ("火星高速抵達代價", "sw794"),
    ("火星任務中止", "sw795"),
    ("火星通訊延遲", "sw796"),
    ("火星太陽合相斷訊", "sw797"),
    ("火星航程人體風險", "sw798"),
    ("火星乘員自治", "sw799"),
    ("火星來回質量", "sw800"),
    ("火星航路修正", "sw801"),
    ("太陽系補給網", "sw802"),
    ("火星航程比較條件", "sw803"),
    ("FTL交通拓樸", "sw804"),
    ("群星超空間航道瓶頸", "sw805"),
    ("蟲洞站文明", "sw806"),
    ("群星Jump Drive戰略", "sw807"),
    ("Halo Slipspace精度", "sw808"),
    ("Jump Drive冷卻科學", "sw809"),
])
def test_from_mars_to_final_frontier_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("火星備份文明", "sw810"),
    ("生命維持閉環率", "sw811"),
    ("殖民地單點故障", "sw812"),
    ("共同原因失效", "sw813"),
    ("異質冗餘", "sw814"),
    ("太空基地優雅降級", "sw815"),
    ("多座火星基地", "sw816"),
    ("月球文明備份庫", "sw817"),
    ("種子工廠", "sw818"),
    ("火星自給指標", "sw819"),
    ("萬年種子船維修", "sw820"),
    ("世代船知識流失", "sw821"),
    ("世代船最小人口", "sw822"),
    ("軌道優勢對地下巢穴", "sw823"),
    ("地下蜂巢偵測", "sw824"),
    ("感測器到武器鏈", "sw825"),
    ("軌道動能武器", "sw826"),
    ("上帝之杖限制", "sw827"),
    ("軌道雷射大氣", "sw828"),
    ("雷射武器三大限制", "sw829"),
    ("蜂群飽和防禦", "sw830"),
    ("母艦對工業文明", "sw831"),
    ("行星防衛系統", "sw832"),
    ("外星科技逆向工程", "sw833"),
    ("駭入外星母艦", "sw834"),
    ("摧毀母腦全軍停擺", "sw835"),
    ("外星生物無限再生", "sw836"),
    ("BETA採礦蜂群", "sw837"),
    ("外星樣本隔離", "sw838"),
    ("跨作品戰力比較", "sw839"),
    ("行星級武器定義", "sw840"),
    ("終局威脅矩陣", "sw841"),
    ("Muv-Luv BETA工程分析", "sw842"),
    ("Girls Garden MG科學", "sw843"),
    ("Muv-Luv重力異常", "sw844"),
    ("Muv-Luv平行世界科學", "sw845"),
])
def test_endgame_survival_engineering_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("新統合政府", "sw846"),
    ("Macross殖民船團", "sw847"),
    ("可曾記得愛", "sw848"),
    ("太空不能傳聲Macross", "sw849"),
    ("傑特拉帝融入社會", "sw850"),
    ("Macross Fold政治", "sw851"),
    ("Macross Valkyrie可行性", "sw852"),
    ("超級地球", "sw853"),
    ("管理式民主", "sw854"),
    ("E-710是什麼", "sw855"),
    ("Helldivers全體命令", "sw856"),
    ("Helldivers軌道支援", "sw857"),
    ("Helldiver是消耗品", "sw858"),
    ("Terminid工業養殖", "sw859"),
    ("UEG和UNSC差別", "sw860"),
    ("UNSC五軍種", "sw861"),
    ("Halo殖民地叛亂", "sw862"),
    ("Cole Protocol", "sw863"),
    ("ONI逆向工程", "sw864"),
    ("Halo Smart AI風險", "sw865"),
    ("UNSC為什麼不全員Spartan", "sw866"),
    ("泰倫自治領", "sw867"),
    ("Dominion propaganda", "sw868"),
    ("Dominion Trooper Royal Guard", "sw869"),
    ("自治領邊疆工業", "sw870"),
    ("StarCraft建築速度", "sw871"),
    ("人類帝國", "sw872"),
    ("帝國弄丟行星", "sw873"),
    ("Astronomican單點故障", "sw874"),
    ("40K科技停滯", "sw875"),
    ("Space Marines不能取代帝國軍", "sw876"),
    ("Great Rift network partition", "sw877"),
    ("銀河帝國中央集權", "sw878"),
    ("五大科幻人類政體比較", "sw879"),
])
def test_five_human_star_nations_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("Yaogan-50 02碎裂", "sw880"),
    ("43個碎片是全部嗎", "sw881"),
    ("編目日期等於碎裂日期嗎", "sw882"),
    ("母星與碎片同時存在", "sw883"),
    ("DEB是什麼", "sw884"),
    ("detect和catalog差別", "sw885"),
    ("TLE能查爆炸原因嗎", "sw886"),
    ("逆行碎片危險", "sw887"),
    ("960公里碎片壽命", "sw888"),
    ("LEO高度範圍", "sw889"),
    ("太空驗屍", "sw890"),
    ("零件脫落還是爆炸", "sw891"),
    ("衛星電池爆炸", "sw892"),
    ("passivation衛星", "sw893"),
    ("上面級爆炸", "sw894"),
    ("conjunction prediction一直變", "sw895"),
    ("Pc不是命中率", "sw896"),
    ("衛星避碰不能一直動", "sw897"),
    ("Whipple shield原理", "sw898"),
    ("1到10公分碎片", "sw899"),
    ("Kessler syndrome垃圾牆", "sw900"),
    ("5年離軌規則", "sw901"),
    ("controlled reentry", "sw902"),
    ("graveyard orbit", "sw903"),
    ("active debris removal", "sw904"),
    ("design for demise", "sw905"),
    ("科技樹不是真實歷史", "sw906"),
    ("TRL九級", "sw907"),
    ("科學到工程的鴻溝", "sw908"),
    ("enabling technology", "sw909"),
    ("SWaP-C", "sw910"),
    ("trade study", "sw911"),
    ("verification validation差別", "sw912"),
    ("三種太空武器分類", "sw913"),
    ("railgun和missile差別", "sw914"),
    ("space laser range", "sw915"),
    ("太空裝甲科技樹", "sw916"),
    ("能量護盾現實", "sw917"),
    ("point defense kill chain", "sw918"),
    ("sensor to shooter", "sw919"),
    ("magazine-limited civilization", "sw920"),
    ("energy和power差別武器", "sw921"),
    ("太空武器廢熱", "sw922"),
    ("saturation attack", "sw923"),
    ("soft counter", "sw924"),
    ("defense in depth太空船", "sw925"),
    ("material civilization", "sw926"),
    ("energy civilization", "sw927"),
    ("autonomy civilization", "sw928"),
    ("文明怎麼輸", "sw929"),
    ("科幻科技成熟度", "sw930"),
])
def test_orbital_debris_and_technology_development_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("確認系外行星數量2026", "sw931"),
    ("habitable zone不是宜居", "sw932"),
    ("有可信外星文明證據嗎", "sw933"),
    ("紅矮星觀測偏差", "sw934"),
    ("TRAPPIST-1七顆行星", "sw935"),
    ("TRAPPIST-1能住嗎", "sw936"),
    ("TOI-700 d e", "sw937"),
    ("Kepler-62 e f", "sw938"),
    ("地球在太陽系沒朋友", "sw939"),
    ("光速無限宇宙", "sw940"),
    ("雙地球思想實驗條件", "sw941"),
    ("第二地球視直徑", "sw942"),
    ("大月亮面積14倍", "sw943"),
    ("肉眼看另一顆地球大陸", "sw944"),
    ("第二地球城市燈光", "sw945"),
    ("潮汐鎖定還有月相嗎", "sw946"),
    ("雙地球互鎖", "sw947"),
    ("背面看不到第二地球", "sw948"),
    ("雙行星質心", "sw949"),
    ("雙地球19.4天", "sw950"),
    ("雙地球一天多長", "sw951"),
    ("Earth Gaia ping", "sw952"),
    ("雙地球潮汐81倍", "sw953"),
    ("81倍潮高錯誤", "sw954"),
    ("雙地球突然出現", "sw955"),
    ("雙地球潮汐加熱", "sw956"),
    ("雙地球日全食", "sw957"),
    ("雙地球食季", "sw958"),
    ("雙地球共用大氣", "sw959"),
    ("雙地球核冬天分開", "sw960"),
    ("雙地球Roche limit", "sw961"),
    ("Earth Gaia軌道穩定", "sw962"),
    ("雙地球L4 L5", "sw963"),
    ("雙地球旅行難度", "sw964"),
    ("Earth Gaia運輸瓶頸", "sw965"),
    ("雙地球行星保護", "sw966"),
    ("雙地球Internet", "sw967"),
    ("雙地球時區", "sw968"),
    ("雙地球科技爆炸", "sw969"),
    ("spaceflight learning curve", "sw970"),
    ("space economy flywheel", "sw971"),
    ("雙地球軍備競賽", "sw972"),
    ("雙地球星際文明", "sw973"),
    ("robots first interstellar", "sw974"),
    ("大月亮文明文化", "sw975"),
])
def test_big_moon_double_earth_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question, expected", [
    ("空軌導力器", "sw976"),
    ("空軌飛船反重力", "sw977"),
    ("抵消重力就能飛嗎", "sw978"),
    ("千噸飛船懸停力", "sw979"),
    ("360公里飛船風壓", "sw980"),
    ("反重力沒有風阻嗎", "sw981"),
    ("inertial dampener問題", "sw982"),
    ("飛船力場泡泡", "sw983"),
    ("行星磁場托飛船", "sw984"),
    ("Lorentz force中性船", "sw985"),
    ("超導不是反重力", "sw986"),
    ("磁浮船高度限制", "sw987"),
    ("Avatar浮空山原理", "sw988"),
    ("低重力大雄超人", "sw989"),
    ("神奇能源分級", "sw990"),
    ("無限能源還缺什麼", "sw991"),
    ("Dilithium不是燃料", "sw992"),
    ("Kyber是電池嗎", "sw993"),
    ("尖叫能量發電", "sw994"),
    ("FF水晶統一設定", "sw995"),
    ("FF1四水晶", "sw996"),
    ("FFXI水晶創造根源", "sw997"),
    ("Type-0四國水晶", "sw998"),
    ("FF16母水晶能源", "sw999"),
    ("水晶文明單點故障", "sw1000"),
    ("科幻能源五問", "sw1001"),
    ("佛利札地產大亨", "sw1002"),
    ("貝吉塔行星被炸原因", "sw1003"),
    ("宜居星球估價", "sw1004"),
    ("宇宙空屋星球", "sw1005"),
    ("炸星球能量等級", "sw1006"),
    ("地球引力束縛能", "sw1007"),
    ("行星核心破壞裝置", "sw1008"),
    ("行星爆炸碎片", "sw1009"),
    ("Unobtanium殖民經濟", "sw1010"),
    ("太空礦業先挖黃金嗎", "sw1011"),
    ("ISRU是什麼", "sw1012"),
    ("小行星礦藏不等於獲利", "sw1013"),
    ("不要搬整顆小行星", "sw1014"),
    ("微重力挖礦", "sw1015"),
    ("宇宙礦產定價", "sw1016"),
    ("火箭方程式吃掉利潤", "sw1017"),
    ("月球主權", "sw1018"),
    ("私人公司占領月球", "sw1019"),
    ("挖礦權等於土地權嗎", "sw1020"),
    ("月球安全區是領土嗎", "sw1021"),
    ("太空採礦污染", "sw1022"),
    ("外星原住民資源權", "sw1023"),
    ("宇宙地產護城河", "sw1024"),
    ("太空港網路效應", "sw1025"),
    ("火星土地泡沫", "sw1026"),
    ("宇宙地產賣什麼", "sw1027"),
])
def test_cosmic_real_estate_and_miracle_energy_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question,expected", [
    ("摩天大樓放大就好嗎", "sw1028"),
    ("台北101阻尼球", "sw1031"),
    ("高樓電梯轉乘", "sw1040"),
    ("火災不能搭電梯嗎", "sw1044"),
    ("Ecumenopolis是什麼", "sw1048"),
    ("行星都市閉環生命維持", "sw1051"),
    ("Stellaris Ecumenopolis現實", "sw1062"),
    ("戴森球是實心殼嗎", "sw1063"),
    ("環形世界不是戴森球", "sw1069"),
    ("宇宙船廠吞吐量", "sw1076"),
    ("分散星際文明", "sw1082"),
    ("終極文明建築", "sw1083"),
])
def test_skyscrapers_ecumenopolis_and_megacity_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question,expected", [
    ("電是能源來源嗎", "sw1084"),
    ("發電都是燒開水嗎", "sw1086"),
    ("容量因數是什麼", "sw1088"),
    ("核融合商業發電了嗎", "sw1100"),
    ("抽蓄是發電嗎", "sw1106"),
    ("RTG是不是反應爐", "sw1115"),
    ("電網供需即時平衡", "sw1117"),
    ("grid forming inverter", "sw1119"),
    ("電池MW與MWh", "sw1125"),
    ("LCOE限制", "sw1130"),
    ("德國2025電力結構", "sw1134"),
    ("德國缺電靠進口", "sw1135"),
    ("情緒發電現實", "sw1141"),
    ("丘比能源系統", "sw1144"),
    ("螺旋力能源分類", "sw1146"),
    ("科幻發電五問", "sw1147"),
])
def test_power_generation_grid_and_fictional_energy_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected


@pytest.mark.parametrize("question,expected", [
    ("台灣科學人雜誌", "sw1148"),
    ("知識大圖解雜誌", "sw1149"),
    ("台北科博館在哪", "sw1150"),
    ("台北天文館位置", "sw1151"),
    ("鹿林天文台參觀", "sw1153"),
    ("合歡山暗空公園", "sw1155"),
    ("波特爾暗空量表", "sw1156"),
    ("台灣哪裡看流星雨", "sw1157"),
    ("負星等更亮", "sw1159"),
    ("星星閃行星不閃", "sw1161"),
    ("啟明長庚都是金星", "sw1163"),
    ("二十八宿星座差別", "sw1164"),
    ("阿提密斯討厭阿波羅", "sw1167"),
    ("橘色外星草原", "sw1169"),
    ("白色草原光合作用", "sw1173"),
    ("虹彩外星植物", "sw1175"),
    ("西德尼亞光合作用", "sw1177"),
    ("Coruscant engineering", "sw1180"),
    ("Trantor vs Coruscant", "sw1182"),
    ("AI科學家自主實驗室", "sw1183"),
    ("somaforming是什麼", "sw1185"),
])
def test_final_curation_aliases_match(knowledge, question, expected):
    assert knowledge.match_question(question).id == expected
