import fs from 'node:fs/promises';import {build} from 'esbuild';import {fixtures} from '../tests/fixture.mjs';
const sample={};let genuine=true;
for(const role of ['baseline','operator','incoming','conflict']){try{sample[role]=JSON.parse(await fs.readFile(`tests/fixtures/native/${role==='conflict'?'incoming-conflict':role}.json`,'utf8'));}catch{genuine=false;sample[role]=fixtures()[role];}}
if(!genuine && process.env.REQUIRE_NATIVE_FIXTURES==='1')throw new Error('Native fixture files required. Run hosted OBS prepare gate first.');
const result=await build({entryPoints:['web/app.mjs'],bundle:true,write:false,format:'iife',platform:'browser',target:['chrome120','safari17','firefox121'],legalComments:'inline',define:{SCENE_SAMPLE:JSON.stringify(sample),SCENE_SAMPLE_GENUINE:JSON.stringify(genuine)}});
let html=await fs.readFile('web/index.html','utf8');const css=await fs.readFile('web/styles.css','utf8');const js=result.outputFiles[0].text;
html=html.replace('<link rel="stylesheet" href="styles.css">',()=>'<style>'+css+'</style>').replace('<script type="module" src="app.mjs"></script>',()=>'<script>'+js.replaceAll('</script','<\\/script')+'</script>');
if(/<link[^>]+styles\.css|<script[^>]+src=/.test(html))throw new Error('Build entry replacement failed');
await fs.mkdir('dist',{recursive:true});await fs.writeFile('dist/index.html',html);console.log(JSON.stringify({bytes:Buffer.byteLength(html),sample:genuine?'native OBS generated':'synthetic development sample; native gate unverified'}));
