import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {speech} from './presentation_speech.mjs';
const runtime='C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const {FileBlob,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const dir=path.resolve('.presentation-build/visual-v2/final');
await fs.mkdir(dir,{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(path.resolve('deliverables/永恆北極星_全視覺導引學習版_v9.pptx')));
for(let i=0;i<p.slides.items.length;i++){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(dir,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
console.log(JSON.stringify({slides:p.slides.items.length,speechCharacters:speech.map(s=>s.body.replace(/\s/g,'').length),totalSpeechCharacters:speech.reduce((n,s)=>n+s.body.replace(/\s/g,'').length,0)}));
