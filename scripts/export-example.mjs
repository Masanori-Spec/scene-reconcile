import fs from 'node:fs/promises';import {parseCollection,analyze,resolve,buildReceipt} from '../src/core.mjs';
await fs.mkdir('generated',{recursive:true});
for(const variant of ['merged','conflict-resolved']){
 const roles=['baseline','operator','incoming'];const inputs={};
 for(const role of roles){const name=role==='incoming'&&variant==='conflict-resolved'?'incoming-conflict.json':role+'.json';inputs[role]={name,text:await fs.readFile('tests/fixtures/native/'+name,'utf8')};}
 const plan=analyze(...roles.map(role=>parseCollection(inputs[role].text)));
 if(plan.errors.length)throw new Error(plan.errors.join('; '));
 const decisions=Object.fromEntries(plan.units.filter(u=>u.status==='conflict').map(u=>[u.id,'operator']));
 const result=resolve(plan,decisions,{name:'SceneReconcile '+variant});
 const outputText=JSON.stringify(result.collection,null,2)+'\n';
 const receipt=await buildReceipt(inputs,result,outputText);
 await fs.writeFile(`generated/native-${variant}.json`,outputText);
 await fs.writeFile(`generated/native-${variant}.receipt.json`,JSON.stringify(receipt,null,2)+'\n');
 console.log(`${variant}: ${result.stats.sources} sources, ${result.stats.scenes} scenes, ${result.stats.items} items`);
}
