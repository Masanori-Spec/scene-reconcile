/** Synthetic unit-test inputs only. Native accepted fixtures are generated independently in hosted OBS. */
export const ids=Object.fromEntries(['Main','Break','LowerThird','Background','Banner','Title','Thanks','ThanksText'].map((n,i)=>[n,`10000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`]));
export function item(id,name,x=0,y=0){return{id,name,source_uuid:ids[name],visible:true,locked:false,pos:{x,y},scale:{x:1,y:1},bounds:{x:0,y:0},rot:0,align:5,bounds_type:0,bounds_align:0,bounds_crop:false,crop_left:0,crop_top:0,crop_right:0,crop_bottom:0,group_item_backup:false,scale_filter:'disable',blend_method:'default',blend_type:'normal',show_transition:{duration:0},hide_transition:{duration:0},private_settings:{}};}
export function scene(name,items){return{uuid:ids[name],name,id:'scene',versioned_id:'scene',settings:{id_counter:Math.max(0,...items.map(x=>x.id)),custom_size:false,items},private_settings:{},filters:[]};}
export function fixtures(){
const baseline={name:'Workshop baseline',version:1,resolution:{x:1280,y:720},sources:[
 scene('Main',[item(1,'Background'),item(2,'LowerThird',100,100)]),scene('Break',[item(1,'Background'),item(2,'LowerThird',20,20)]),scene('LowerThird',[item(1,'Banner'),item(2,'Title',24,30)]),
 {uuid:ids.Background,name:'Background',id:'color_source',versioned_id:'color_source_v3',settings:{color:4278190080,width:1280,height:720},filters:[]},
 {uuid:ids.Banner,name:'Banner',id:'color_source',versioned_id:'color_source_v3',settings:{color:4291669810,width:650,height:110},filters:[]},
 {uuid:ids.Title,name:'Title',id:'text_ft2_source',versioned_id:'text_ft2_source_v2',settings:{text:'Workshop begins at 18:00',font:{face:'DejaVu Sans',size:32},color1:4294967295,color2:4294967295},filters:[]}
],groups:[],canvases:[],scene_order:[{name:'Main'},{name:'Break'},{name:'LowerThird'}],current_scene:'Main',current_program_scene:'Main',modules:{}};
const operator=structuredClone(baseline),incoming=structuredClone(baseline);operator.name='Workshop operator';incoming.name='Workshop incoming';
const source=(doc,name)=>doc.sources.find(s=>s.name===name);
source(operator,'Main').settings.items[1].pos={x:240,y:80};source(operator,'Break').settings.items[1].visible=false;source(operator,'Background').settings.color=4281541135;
source(incoming,'Break').settings.items[1].pos={x:40,y:30};source(incoming,'Title').settings.text='Workshop begins at 18:30';
incoming.sources.push(scene('Thanks',[item(1,'LowerThird',100,100),item(2,'ThanksText',100,280)]),{uuid:ids.ThanksText,name:'ThanksText',id:'text_ft2_source',versioned_id:'text_ft2_source_v2',settings:{text:'Thanks for joining',font:{face:'DejaVu Sans',size:40},color1:4294967295,color2:4294967295},filters:[]});incoming.scene_order.push({name:'Thanks'});
const conflict=structuredClone(incoming);source(conflict,'Main').settings.items[1].pos={x:120,y:140};
return{baseline,operator,incoming,conflict};}
export function source(doc,name){return doc.sources.find(s=>s.name===name);}
export function relative(doc){const result=structuredClone(doc);result.version=2;result.migration_resolution={...result.resolution};for(const s of result.sources)if(s.id==='scene')for(const x of s.settings.items){x.pos_rel={x:x.pos.x/640-1,y:x.pos.y/360-1};x.scale_rel={...x.scale};x.scale_ref={x:1280,y:720};x.bounds_rel={x:0,y:0};}return result;}
