import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {speech} from './presentation_speech.mjs';
const home=process.env.USERPROFILE||process.env.HOME;
if(!home)throw new Error('USERPROFILE or HOME is required to locate Codex presentation dependencies.');
const codexHome=process.env.CODEX_HOME||path.join(home,'.codex');
// Optional overrides for rebuilding outside the Codex desktop defaults.
const runtime=path.resolve(process.env.CODEX_WORKSPACE_DEPENDENCIES||path.join(home,'.cache','codex-runtimes','codex-primary-runtime','dependencies'));
async function resolvePresentationSkill(){
 if(process.env.CODEX_PRESENTATIONS_SKILL_DIR)return path.resolve(process.env.CODEX_PRESENTATIONS_SKILL_DIR);
 const root=path.join(codexHome,'plugins','cache','openai-primary-runtime','presentations');
 const versions=(await fs.readdir(root,{withFileTypes:true})).filter(entry=>entry.isDirectory()).map(entry=>entry.name).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
 for(const version of versions){const candidate=path.join(root,version,'skills','presentations');try{await fs.access(path.join(candidate,'container_tools','artifact_tool_utils.mjs'));return candidate}catch{}}
 throw new Error(`Presentation skill not found under ${root}; set CODEX_PRESENTATIONS_SKILL_DIR.`);
}
const skill=await resolvePresentationSkill();
const nodeModules=path.join(runtime,'node','node_modules');
process.env.RUNTIME_NODE_MODULES=nodeModules;
const pythonExecutable=process.env.CODEX_PYTHON_EXECUTABLE||path.join(runtime,'python','python.exe');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(nodeModules,'@oai','artifact-tool','dist','artifact_tool.mjs')));
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools','artifact_tool_utils.mjs')));
const workspace=path.resolve('.'),build=path.join(workspace,'.presentation-build','visual-v11'),output=path.join(workspace,'deliverables');
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}}),font='Microsoft JhengHei';
const C={paper:'#F7F5F0',ink:'#242830',red:'#843C46',muted:'#66717A',white:'#FFFFFF',line:'#D8D1C7',gold:'#B9904A',blue:'#58748E',green:'#557869',violet:'#77658B',soft:'#EEE8DE',bot:'#DDF2FF',botLine:'#79AFCB',botInk:'#1E4E67',user:'#E7EFE9'};
const repo='https://github.com/Gale0418/SFLINE_BOT',lineUrl='https://developers.line.biz/en/docs/messaging-api/receiving-messages/',gemma='https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api',notebook='https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-discover-sources/',kahoot='https://kahoot.com/schools/how-it-works/';
function txt(s,str,x,y,w,h,size=26,color=C.ink,bold=false,align='left'){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=str;a.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',alignment:align,verticalAlignment:'middle'};return a;}
function shape(s,g,x,y,w,h,fill=C.white,stroke=C.line,width=1){return s.shapes.add({geometry:g,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width}});}
function box(s,label,x,y,w,h,o={}){const z={fill:C.white,stroke:C.line,color:C.ink,size:24,bold:true,...o};const b=shape(s,'roundRect',x,y,w,h,z.fill,z.stroke,2);txt(s,label,x+10,y+7,w-20,h-14,z.size,z.color,z.bold,'center');return b;}
function chatBubble(s,label,x,y,w,h,role='bot'){const isBot=role==='bot';return box(s,label,x,y,w,h,{fill:isBot?C.bot:C.user,stroke:isBot?C.botLine:C.green,color:isBot?C.botInk:C.ink,size:20,bold:true});}
function arrow(s,x,y,w,h,color=C.red){return shape(s,'rightArrow',x,y,w,h,color,color,0)}function rule(s,x,y,w,h,color=C.line){return shape(s,'rect',x,y,w,h,color,color,0)}
function page(title,n){const s=p.slides.add();s.background.fill=C.paper;txt(s,title,72,45,1136,66,41,C.ink,true);txt(s,String(n).padStart(2,'0'),1165,655,45,25,17,C.muted);return s}function notes(s,i,src=[]){s.speakerNotes.textFrame.setText(speech[i].body+'\n\n資料來源：\n'+src.join('\n'))}
{
 const s=p.slides.add();s.background.fill=C.ink;s.images.add({blob:await fs.readFile(path.join(workspace,'assets/report/observatory-cover.png')),contentType:'image/png',alt:'AI生成的天文觀測室概念插畫，非真實觀測照片',fit:'cover',position:{left:0,top:0,width:1280,height:720}});txt(s,'永恆北極星',72,158,690,112,76,C.paper,true);txt(s,'LINE 科學問答、四座寶庫與導引式學習',78,297,745,88,29,C.paper);rule(s,78,414,116,5,'#D5B9AD');txt(s,'半導體 AI 課程專題報告\n2026 年 9 月',78,450,700,90,22,'#D5B9AD');notes(s,0,[repo,'AI 概念插畫：內建 imagegen 生成，2026-09-13']);
}
{
 const s=page('報告大綱',2);txt(s,'五個部分，從動機走到可展示的系統',72,139,1136,48,31,C.red,true);rule(s,130,337,1005,4);const outline=[['01','背景與目標','為什麼想做',C.red],['02','工具與情境','LINE 與相關產品',C.blue],['03','系統與架構','問答、試煉、導引',C.violet],['04','系統驗證','主要流程會不會壞',C.green],['05','結論與資料','成果、限制、來源',C.gold]];outline.forEach((o,i)=>{const x=104+i*232;shape(s,'ellipse',x,281,112,112,C.paper,o[3],5);txt(s,o[0],x+21,302,70,36,24,o[3],true,'center');txt(s,o[1],x-37,420,186,34,22,o[3],true,'center');txt(s,o[2],x-54,466,220,52,18,C.muted,false,'center')});notes(s,1,['本機 README.md']);
}
{
 const s=page('1. 簡介',3);s.images.add({blob:await fs.readFile(path.join(workspace,'assets/report/pluto-concept.png')),contentType:'image/png',alt:'AI生成的冥王星概念插畫，非探測器照片',fit:'contain',position:{left:760,top:176,width:405,height:405}});txt(s,'因為喜歡，所以想把好奇心做成作品',72,145,650,54,31,C.red,true);rule(s,529,289,240,3);rule(s,529,416,240,3);box(s,'看見\n冥王星的愛心',72,244,235,91,{fill:'#F0E2DF',stroke:C.red,size:23});box(s,'追問\n它為什麼長這樣',332,244,214,91,{stroke:C.red,size:23});box(s,'理解\n科學與未知的邊界',72,371,235,91,{fill:'#E5ECEA',stroke:C.green,size:23});box(s,'做出\n能陪人探索的機器人',332,371,214,91,{stroke:C.green,size:22});arrow(s,558,279,80,22);arrow(s,558,406,80,22,C.green);txt(s,'應用情境：課後探索、科學活動與展場導覽',72,567,655,56,21,C.muted);txt(s,'冥王星概念插畫，非觀測照片',806,593,345,30,17,C.muted,false,'center');notes(s,2,['https://science.nasa.gov/dwarf-planets/pluto/facts/','本機 README.md、docs/solar-wonders.md']);
}
{
 const s=page('2. 專題目的、相關產品',4);txt(s,'三種能力在同一個 LINE 對話裡相遇',72,145,1136,48,31,C.red,true);rule(s,355,300,570,3);rule(s,487,255,3,250);rule(s,790,255,3,250);shape(s,'ellipse',505,248,270,270,'#EFE6E2',C.red,2);txt(s,'永恆北極星',540,328,200,44,29,C.red,true,'center');txt(s,'問答＋導引＋試煉',530,379,220,38,22,C.ink,true,'center');box(s,'NotebookLM\n依來源整理',94,276,250,112,{stroke:C.blue,size:23});box(s,'Kahoot!\n題目與即時回饋',936,276,250,112,{stroke:C.gold,size:22});box(s,'LINE\n日常聊天入口',515,518,250,92,{stroke:C.green,size:23});txt(s,'參考來源呈現',109,414,220,30,19,C.blue,true,'center');txt(s,'參考五題挑戰',951,414,220,30,19,C.gold,true,'center');txt(s,'重點是把問答、導引與固定試煉放進同一個聊天室。',72,630,1040,28,18,C.muted);notes(s,3,[notebook,kahoot,lineUrl,repo]);
}
{
 const s=page('3. 系統架構與技術：整體流程',5);txt(s,'LINE 手機 → ngrok → NAS／Docker → 回覆',72,141,1136,46,31,C.red,true);const labels=[['LINE 使用者','文字／按鈕'],['ngrok','HTTPS 通道'],['Synology NAS','Docker 常駐'],['Webhook','簽章／去重'],['路由判斷','命令／問答'],['回覆 LINE','文字／Quick Reply']],xs=[40,240,440,640,840,1040];for(let i=0;i<labels.length;i++){if(i<5)arrow(s,xs[i]+160,286,36,20,i===4?C.green:C.red);box(s,labels[i][0]+'\n'+labels[i][1],xs[i],238,156,112,{fill:i===0||i===5?'#E5ECEA':i===2?C.bot:C.white,stroke:i===0||i===5?C.green:i===2?C.botLine:C.red,size:19})}rule(s,918,350,3,78);box(s,'規則路徑\nHelp、學習、計分',690,440,270,94,{fill:'#F0E2DF',stroke:C.red,size:21});box(s,'模型路徑\n開放問題與追問',978,440,236,94,{fill:'#E7EBEF',stroke:C.blue,size:20});txt(s,'服務與 SQLite 都在 NAS；ngrok 只負責把 LINE 的 HTTPS Webhook 安全轉進來。',72,568,1136,40,22,C.ink,true);txt(s,'LINE ID 轉成假名代碼；學習進度保存在 NAS 的持久化資料卷。',72,620,1136,30,18,C.muted);notes(s,4,[lineUrl,'本機 README.md、deploy/nas/、src/eternal_polaris/app.py、dispatcher.py、learning.py']);
}
{
 const s=page('3. 系統架構與技術：內容資料',6);txt(s,'1,234 張知識卡、300 題、24 個主題',72,139,1136,51,33,C.red,true);const chart=s.charts.add('bar',{position:{left:52,top:218,width:635,height:360},categories:['星海','地脈與生命','萬象法則','未來幻夢'],series:[{name:'題數',values:[161,37,30,72],fill:C.red}],barOptions:{direction:'bar',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:21,fill:C.ink}},xAxis:{textStyle:{fontSize:18,fill:C.ink}},yAxis:{textStyle:{fontSize:19,fill:C.ink}},chartFill:C.paper,plotAreaFill:C.paper});applyPresentationChartFont(chart,{fontFamily:font});shape(s,'ellipse',772,221,344,344,C.soft,C.line,1);shape(s,'ellipse',827,276,234,234,C.white,C.red,2);shape(s,'ellipse',884,333,120,120,C.ink,C.ink,0);txt(s,'四座寶庫',884,359,120,30,21,C.white,true,'center');txt(s,'100 張重點知識卡圖片',795,500,300,28,19,C.blue,true,'center');txt(s,'80 段重組導引教材',810,541,270,28,19,C.red,true,'center');txt(s,'固定題庫不依賴 AI API',790,582,310,30,19,C.ink,true,'center');txt(s,'知識卡保留來源；題庫答案固定；圖片與導引教材支援手機閱讀。',72,615,1090,34,21,C.muted);notes(s,5,['本機 README.md、data/knowledge_cards.json、data/quiz_questions.tsv','assets/knowledge/、docs/guided-learning.md']);
}
{
 const s=page('3. 系統架構與技術：回答策略',7);txt(s,'先查本機知識卡，再決定是否呼叫模型',72,141,1136,49,31,C.red,true);box(s,'使用者問題',83,265,215,92,{fill:C.ink,stroke:C.ink,color:C.white,size:25});arrow(s,316,300,70,22);box(s,'高信心命中\n知識卡？',405,251,222,119,{stroke:C.red,size:23});txt(s,'是',648,246,52,28,18,C.red,true,'center');txt(s,'否',648,391,52,28,18,C.blue,true,'center');arrow(s,642,286,70,22);arrow(s,642,419,70,22,C.blue);box(s,'本機回答\n內容＋來源',731,251,205,119,{fill:'#F0E2DF',stroke:C.red,size:23});box(s,'模型回答\n開放問題＋三組對話',731,392,265,119,{fill:'#E7EBEF',stroke:C.blue,size:22});arrow(s,1014,300,70,22,C.green);arrow(s,1014,435,70,22,C.green);box(s,'格式與\n內容檢查',1093,323,130,112,{fill:'#E5ECEA',stroke:C.green,size:20});txt(s,'課程 OpenAI 額度用完後，目前改採 Google AI Studio 免費方案',72,565,1120,38,22,C.ink,true);txt(s,'設定使用 Google 時，不會在執行途中偷偷切回付費 OpenAI。',72,614,1090,32,19,C.muted);notes(s,6,[gemma,'本機 README.md、src/eternal_polaris/answer_service.py、knowledge.py']);
}
{
 const s=page('3. 系統架構與技術：導引式學習',8);chatBubble(s,'守門人：你對這世界感到好奇嗎？',72,126,500,58,'bot');chatBubble(s,'使用者：學習',956,130,252,50,'user');box(s,'選擇路線',72,261,150,72,{fill:C.ink,stroke:C.ink,color:C.white,size:22});arrow(s,235,286,53,21);const routes=[['🌌 星海之庫',C.blue],['🌍 地脈與生命',C.green],['⚛️ 萬象法則',C.violet],['🚀 未來幻夢',C.gold]];routes.forEach((r,i)=>box(s,r[0],306,202+i*92,240,65,{stroke:r[1],size:21}));rule(s,563,235,3,298);const steps=[['短講','5 段'],['理解題','立即解說'],['過關挑戰','5 題答對 4 題'],['下一階段','各路獨立進度']];steps.forEach((r,i)=>{if(i<3)arrow(s,718+i*150,319,42,20);shape(s,'ellipse',615+i*150,270,112,112,i===3?'#E5ECEA':C.white,i===3?C.green:C.red,2);txt(s,String(i+1),649+i*150,286,44,30,20,C.red,true,'center');txt(s,r[0],627+i*150,320,88,28,18,C.ink,true,'center');txt(s,r[1],605+i*150,386,132,55,17,C.muted,false,'center')});txt(s,'四條路線各自保存進度，使用者可以自由換路再回來。',608,505,590,73,22,C.ink,true,'center');txt(s,'淺藍色＝守門人對話；SQLite 位於 NAS，手機端不執行 SQL。',608,592,590,30,18,C.muted,false,'center');notes(s,7,['本機 README.md、docs/guided-learning.md、src/eternal_polaris/learning.py、tests/test_learning.py']);
}
{
 const s=page('4. 系統驗證',9);txt(s,'LINE 機器人的主要流程有沒有照規則運作？',72,139,1136,51,31,C.red,true);const checks=[['1','入口安全','LINE 簽章\n偽造請求拒絕',C.red],['2','訊息一致','事件去重\nReply Token 只用一次',C.blue],['3','功能路由','幫助、試煉\n計分、退出、問答',C.violet],['4','進度保存','四條路線\nSQLite 交易',C.green]];rule(s,147,333,890,4);checks.forEach((c,i)=>{const x=105+i*286;shape(s,'ellipse',x,278,112,112,C.paper,c[3],5);txt(s,c[0],x+30,299,52,36,24,c[3],true,'center');txt(s,c[1],x-28,420,168,34,22,c[3],true,'center');txt(s,c[2],x-58,462,228,62,18,C.muted,false,'center')});shape(s,'roundRect',748,548,442,74,'#E5ECEA',C.green,2);txt(s,'完整自動測試＋branch coverage\n另保留 4 次真實聊天紀錄',766,558,406,54,18,C.green,true,'center');txt(s,'程式測試 ≠ 學習成效；模型 Accuracy／F1／P95 尚未正式驗證。',72,636,820,27,18,C.muted);notes(s,8,['本機 README.md、tests/','2026-09-08：gemma-4-26b-a4b-it 四次真實聊天 smoke test']);
}
{
 const s=page('5. 結論與未來工作',10);txt(s,'已完成能長期運作的骨架，也保留誠實邊界',72,139,1136,50,31,C.red,true);rule(s,125,349,1015,5);const nodes=[['問答','1,234 卡＋300 題',C.red],['導引','80 段＋四路進度',C.blue],['視覺','100 張知識卡圖片',C.green],['部署','NAS／Docker 常駐',C.gold]];nodes.forEach((n,i)=>{const x=105+i*292;shape(s,'ellipse',x,297,108,108,C.paper,n[2],5);txt(s,String(i+1),x+31,318,46,38,25,n[2],true,'center');txt(s,n[0],x-31,230,170,35,22,n[2],true,'center');txt(s,n[1],x-61,429,230,85,21,C.ink,true,'center')});txt(s,'尚待驗證：不同手機的實機操作，以及固定測試集的線上模型效能。',72,564,1136,37,23,C.ink,true,'center');txt(s,'自動測試證明程式規則，不代表學生學習成效。',72,615,1136,30,19,C.muted,false,'center');notes(s,9,[repo,'本機 README.md、deploy/nas/、docs/guided-learning.md']);
}
{
 const s=page('6. 參考文獻',11);txt(s,'每份資料實際用在哪一頁',72,130,1136,40,28,C.red,true);
 const cards=[
  {p:'P3',title:'NASA Pluto Facts',tag:'天體分類與地貌',content:'• 冥王星矮行星分類\n• 湯博區「愛心」地貌\n• 研究動機與問題引導',stroke:C.gold,x:72,y:185},
  {p:'P4',title:'NotebookLM / Kahoot!',tag:'相關產品與情境',content:'• NotebookLM：依據來源整理\n• Kahoot!：題目與即時回饋\n• 本專題的功能定位',stroke:C.red,x:460,y:185},
  {p:'P5',title:'LINE Developers Docs',tag:'通訊架構',content:'• Webhook 簽章驗證\n• Messaging API 訊息回覆\n• Reply Token 使用規則',stroke:C.green,x:848,y:185},
  {p:'P7',title:'Google AI Gemma Docs',tag:'模型與 API',content:'• Gemma 4 26B A4B\n• Google AI Studio 使用方式\n• 模型輸出與提示設定',stroke:C.blue,x:72,y:415},
  {p:'P5/P6/P8/P10',title:'專案 README、程式與資料',tag:'系統實作',content:'• 1,234 張知識卡與 300 題\n• 100 張圖片、80 段教材\n• NAS、SQLite 與四路進度',stroke:C.violet,x:460,y:415},
  {p:'P9',title:'README 與本機測試',tag:'系統驗證',content:'• 簽章、去重與路由\n• 題庫、按鈕與進度交易\n• 4 次真實聊天測試紀錄',stroke:C.ink,x:848,y:415}
 ];
 cards.forEach(c=>{
  const pageTagWidth=c.p.length>5?118:64;
  shape(s,'roundRect',c.x,c.y,360,210,C.white,c.stroke,2);
  shape(s,'roundRect',c.x+14,c.y+14,pageTagWidth,26,c.stroke,c.stroke,0);
  txt(s,c.p,c.x+14,c.y+14,pageTagWidth,26,pageTagWidth>64?11:14,C.white,true,'center');
  txt(s,c.tag,c.x+pageTagWidth+22,c.y+14,336-pageTagWidth,26,15,c.stroke,true);
  txt(s,c.title,c.x+14,c.y+46,330,30,17,C.ink,true);
  rule(s,c.x+14,c.y+82,332,1,C.line);
  txt(s,c.content,c.x+14,c.y+90,332,106,14,C.muted,false,'left');
 });
 txt(s,'完整網址放在投影片備忘稿；專案內容以 README 與原始檔案為準。',72,648,1136,26,17,C.muted);
 notes(s,10,[
  'P3: https://science.nasa.gov/dwarf-planets/pluto/ (NASA Pluto Facts)',
  'P4: '+notebook+' (NotebookLM 官方介紹)',
  'P4: '+kahoot+' (Kahoot! 運作機制)',
  'P5: '+lineUrl+' (LINE Messaging API Webhook)',
  'P7: '+gemma+' (Gemma on Gemini Developer API)',
  'P5/P6/P8/P10: '+repo+' (README、專案程式、題庫資料與 docs/guided-learning.md)',
  'P9: 本機 README.md 與 tests/（主要流程測試範圍、2026-09-08 四次真實聊天紀錄）'
 ]);
}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);for(let i=0;i<p.slides.items.length;i++){const preview=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await preview.arrayBuffer()))}
const finalPath=path.join(output,'永恆北極星_全視覺導引學習版_v11.pptx');const result=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath,pythonExecutable,integrityValidatorPath:path.join(skill,'container_tools','inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools','inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:11,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[6],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-v11.json')});
const scriptPath=path.join(output,'永恆北極星_全視覺導引學習版_v11_逐頁演講稿.md');const intro='# 永恆北極星：逐頁演講稿（全視覺導引學習版 v11）\n\n對應檔案：永恆北極星_全視覺導引學習版_v11.pptx，共 11 頁。預計約 30 分鐘，包含操作與互動；請依實際語速排練。\n\n## 講者設定\n\n講者採聰慧、俐落、略帶活潑的天才少女學生風格。機器人本身維持沉穩而慈祥的睿智老人；投影片中的機器人對話一律使用淺藍色氣泡。\n\n';await fs.writeFile(scriptPath,intro+speech.map((n,i)=>`## 第 ${i+1} 頁　${n.title}\n\n${n.body}\n`).join('\n'),'utf8');console.log(JSON.stringify({final:result.finalPath,slides:p.slides.items.length,script:scriptPath}));
