/** SceneReconcile: bounded native collection reconciliation. No network, media or OBS execution. */
export const LIMITS = Object.freeze({bytes: 10 * 1024 * 1024, scenes: 20, sources: 200, items: 1000});
export const TRANSFORM_FIELDS = Object.freeze(['pos','pos_rel','scale','scale_rel','scale_ref','bounds','bounds_rel','rot','align','bounds_type','bounds_align','bounds_crop','crop_left','crop_top','crop_right','crop_bottom']);
const EDITABLE = new Set(['color_source','text_ft2_source']);
const OWNED = new Set(['ffmpeg_source','image_source','slideshow','xshm_input','xcomposite_input','v4l2_input','pulse_input_capture','pulse_output_capture','alsa_input_capture','pipewire-screen-capture-source']);
const MAIN_CANVAS_UUID='6c69626f-6273-4c00-9d88-c5136d61696e';
const TRANSITIONS = new Set(['fade_transition','cut_transition','swipe_transition','slide_transition','fade_to_color_transition','wipe_transition','obs_stinger_transition']);
const SOURCE_KEYS = new Set(['settings','uuid','name','id','versioned_id']);
const ITEM_KEYS = new Set(['id','source_uuid','name','visible','locked',...TRANSFORM_FIELDS]);
const UI_KEYS = new Set(['name','sources','scene_order','current_scene','current_program_scene','preview_locked','scaling_enabled','scaling_level','scaling_off_x','scaling_off_y']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const clone = value => value === undefined ? undefined : structuredClone(value);
export const canonical = value => value === undefined ? '@undefined' : value === null || typeof value !== 'object' ? JSON.stringify(value) : Array.isArray(value) ? '['+value.map(canonical).join(',')+']' : '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
const equal = (a,b) => canonical(a) === canonical(b);
const pick = (obj, keys) => Object.fromEntries(keys.filter(k=>Object.hasOwn(obj,k)).map(k=>[k,clone(obj[k])]));
const rest = (obj, keys) => Object.fromEntries(Object.keys(obj).filter(k=>!keys.has(k)).map(k=>[k,clone(obj[k])]));
const assert = (ok,code,detail='') => {if(!ok) throw new Error(`${code}${detail ? ': '+detail : ''}`);};
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function safeTree(value,depth=0){
  assert(depth<=60,'DEPTH_LIMIT');
  if(typeof value==='number') assert(Number.isFinite(value),'NONFINITE_NUMBER');
  if(value && typeof value==='object') for(const [key,child] of Object.entries(value)){
    assert(!['__proto__','constructor','prototype'].includes(key),'UNSAFE_KEY',key); safeTree(child,depth+1);
  }
}
function rejectDuplicateKeys(text){
  let offset=0;
  const ws=()=>{while(/\s/.test(text[offset]||'x'))offset++;};
  function string(){const start=offset++;while(offset<text.length){if(text[offset]==='\\'){offset+=2;continue;}if(text[offset++]==='"')break;}return JSON.parse(text.slice(start,offset));}
  function value(){ws();const token=text[offset];if(token==='{'||token==='['){const obj=token==='{',end=obj?'}':']',keys=new Set();offset++;ws();if(text[offset]===end){offset++;return;}while(offset<text.length){if(obj){ws();const key=string();assert(!keys.has(key),'DUPLICATE_JSON_KEY',key);keys.add(key);ws();offset++;}value();ws();if(text[offset++]===end)break;}return;}if(token==='"'){string();return;}while(offset<text.length&&!/[\s,}\]]/.test(text[offset]))offset++;}
  value();
}
export function parseCollection(text){
  assert(typeof text==='string','TEXT_REQUIRED');
  assert(new TextEncoder().encode(text).length <= LIMITS.bytes,'FILE_TOO_LARGE','10 MiB maximum');
  const jsonText=text.charCodeAt(0)===0xFEFF?text.slice(1):text;
  let doc; try{doc=JSON.parse(jsonText);}catch{throw new Error('INVALID_JSON');}
  rejectDuplicateKeys(jsonText); validateCollection(doc); return doc;
}
function sourceMap(doc){return new Map(doc.sources.map(s=>[s.uuid,s]));}
function membership(source){return source.settings.items.map(x=>({id:x.id,source_uuid:x.source_uuid,name:x.name}));}
function itemMap(source){return new Map(source.settings.items.map(x=>[`${x.id}:${x.source_uuid}`,x]));}
const itemKey = x => `${x.id}:${x.source_uuid}`;
function transform(item){return pick(item,TRANSFORM_FIELDS);}
function setFields(obj,keys,value){for(const key of keys) delete obj[key]; Object.assign(obj,clone(value));}
function validVector(value){return object(value) && Object.keys(value).length===2 && Object.keys(value).every(k=>k==='x'||k==='y') && typeof value.x==='number' && typeof value.y==='number' && Number.isFinite(value.x) && Number.isFinite(value.y);}
function validateKind(source){
  if(Object.hasOwn(source,'canvas_uuid'))assert(source.canvas_uuid===MAIN_CANVAS_UUID,'CANVAS_REFERENCE_UNSUPPORTED',source.name||source.id);
  assert(source.id==='scene'||EDITABLE.has(source.id)||OWNED.has(source.id)||TRANSITIONS.has(source.id),'SOURCE_KIND_UNSUPPORTED',String(source.id));
  const allowed=source.id==='color_source'?['color_source','color_source_v3']:source.id==='text_ft2_source'?['text_ft2_source','text_ft2_source_v2']:[source.id];
  assert(allowed.includes(source.versioned_id),'SOURCE_VERSION_UNSUPPORTED',`${source.name||source.id}/${source.versioned_id}`);
}
function validateEmbeddedSources(value){
  if(!value||typeof value!=='object')return;
  if(object(value)&&(typeof value.id==='string'||Object.hasOwn(value,'versioned_id'))){
    assert(object(value.settings),'EMBEDDED_SOURCE_SETTINGS_REQUIRED',value.name||value.id);
    validateKind(value);assert(!value.filters||(Array.isArray(value.filters)&&value.filters.length===0),'FILTERS_UNSUPPORTED',value.name||value.id);
    if(value.id==='text_ft2_source')assert(!value.settings.from_file,'TEXT_FILE_UNSUPPORTED',value.name);
  }
  for(const child of Object.values(value))validateEmbeddedSources(child);
}
function validateSettings(source){
  assert(object(source.settings),'SETTINGS_REQUIRED',source.name);
  if(source.id==='text_ft2_source') assert(!source.settings.from_file,'TEXT_FILE_UNSUPPORTED',source.name);
  const keys=source.id==='color_source'?new Set(['color','width','height']):source.id==='text_ft2_source'?new Set(['font','text','color1','color2','custom_width','word_wrap','from_file','text_file','log_mode','log_lines','antialiasing','drop_shadow','outline']):null;
  if(keys)for(const key of Object.keys(source.settings))assert(keys.has(key),'SOURCE_SETTING_UNSUPPORTED',`${source.name}/${key}`);
  if(source.id==='text_ft2_source'&&source.settings.font)for(const key of Object.keys(source.settings.font))assert(['face','style','size','flags'].includes(key),'FONT_SETTING_UNSUPPORTED',key);
  const range=(value,min,max)=>Number.isSafeInteger(value)&&value>=min&&value<=max;
  const settings=source.settings;
  if(source.id==='color_source'){
    for(const key of ['width','height'])if(Object.hasOwn(settings,key))assert(range(settings[key],1,4096),'COLOR_DIMENSION_RANGE',`${source.name}/${key}`);
    if(Object.hasOwn(settings,'color'))assert(range(settings.color,0,0xffffffff),'COLOR_VALUE_RANGE',source.name);
  }
  if(source.id==='text_ft2_source'){
    for(const key of ['text','text_file'])if(Object.hasOwn(settings,key))assert(typeof settings[key]==='string','TEXT_SETTING_TYPE',key);
    for(const key of ['from_file','log_mode','word_wrap','antialiasing','drop_shadow','outline'])if(Object.hasOwn(settings,key))assert(typeof settings[key]==='boolean','TEXT_SETTING_TYPE',key);
    for(const key of ['color1','color2'])if(Object.hasOwn(settings,key))assert(range(settings[key],0,0xffffffff),'COLOR_VALUE_RANGE',key);
    if(Object.hasOwn(settings,'custom_width'))assert(range(settings.custom_width,0,4096),'TEXT_WIDTH_RANGE');
    if(Object.hasOwn(settings,'log_lines'))assert(range(settings.log_lines,1,1000),'TEXT_LOG_RANGE');
    if(Object.hasOwn(settings,'font')){
      assert(object(settings.font),'FONT_SETTING_TYPE');
      for(const key of ['face','style'])if(Object.hasOwn(settings.font,key))assert(typeof settings.font[key]==='string','FONT_SETTING_TYPE',key);
      if(Object.hasOwn(settings.font,'size'))assert(range(settings.font.size,1,65535),'FONT_SIZE_RANGE');
      if(Object.hasOwn(settings.font,'flags'))assert(range(settings.font.flags,0,15),'FONT_FLAGS_RANGE');
    }
  }
  assert(!source.filters || (Array.isArray(source.filters)&&source.filters.length===0),'FILTERS_UNSUPPORTED',source.name);
}
export function validateCollection(doc){
  safeTree(doc); assert(object(doc),'COLLECTION_REQUIRED'); validateEmbeddedSources(doc);
  assert(typeof doc.name==='string' && doc.name.trim().length>0 && doc.name.length<=255,'COLLECTION_NAME');
  assert(doc.version===1 || doc.version===2,'COORDINATE_VERSION','supported native coordinate versions: 1, 2');
  assert(object(doc.resolution) && validVector(doc.resolution) && doc.resolution.x>0 && doc.resolution.y>0,'RESOLUTION_REQUIRED');
  if(doc.migration_resolution!==undefined)assert(validVector(doc.migration_resolution)&&doc.migration_resolution.x>0&&doc.migration_resolution.y>0,'MIGRATION_RESOLUTION');
  if(doc.transitions!==undefined){assert(Array.isArray(doc.transitions),'TRANSITIONS_REQUIRED');for(const transition of doc.transitions){assert(object(transition)&&typeof transition.id==='string'&&object(transition.settings),'TRANSITION_SOURCE_REQUIRED');validateKind(transition);}}
  for(const key of ['groups','canvases']) assert(doc[key]===undefined || (Array.isArray(doc[key])&&doc[key].length===0),key.toUpperCase()+'_UNSUPPORTED');
  if(doc.modules) for(const [key,value] of Object.entries(doc.modules)) if(!['output-timer','auto-scene-switcher'].includes(key)) assert(value===null || (Array.isArray(value)&&!value.length) || (object(value)&&!Object.keys(value).length),/script/i.test(key)?'SCRIPTS_UNSUPPORTED':'MODULES_UNSUPPORTED',key);
  assert(Array.isArray(doc.sources) && doc.sources.length>0 && doc.sources.length<=LIMITS.sources,'SOURCE_LIMIT');
  const names=new Set(),ids=new Set(); let sceneCount=0,itemCount=0;
  for(const source of doc.sources){
    assert(object(source)&&typeof source.uuid==='string'&&UUID.test(source.uuid),'SOURCE_UUID');
    assert(!ids.has(source.uuid),'DUPLICATE_UUID',source.uuid); ids.add(source.uuid);
    assert(typeof source.name==='string'&&source.name.trim().length>0&&source.name.length<=255,'SOURCE_NAME');
    assert(!names.has(source.name),'DUPLICATE_NAME',source.name); names.add(source.name);
    assert(source.id==='scene'||EDITABLE.has(source.id)||OWNED.has(source.id),'SOURCE_KIND_UNSUPPORTED',String(source.id)); validateKind(source);
    validateSettings(source);
    if(source.id==='scene'){
      sceneCount++; assert(!source.settings.custom_size,'CUSTOM_CANVAS_UNSUPPORTED',source.name);
      assert(Array.isArray(source.settings.items),'ITEMS_REQUIRED',source.name); itemCount+=source.settings.items.length;
      const itemIds=new Set();
      for(const item of source.settings.items){
        assert(object(item)&&Number.isSafeInteger(item.id)&&item.id>0&&!itemIds.has(item.id),'ITEM_ID',source.name); itemIds.add(item.id);
        assert(typeof item.source_uuid==='string'&&UUID.test(item.source_uuid),'ITEM_UUID',source.name);
        assert(typeof item.visible==='boolean'&&typeof item.locked==='boolean','ITEM_FLAGS',source.name);
        assert(!item.group_item_backup,'GROUP_UNSUPPORTED',source.name);
        assert(typeof item.bounds_crop==='boolean','BOUNDS_CROP_FLAG',source.name);
        for(const edge of ['crop_left','crop_top','crop_right','crop_bottom']) assert(Number.isSafeInteger(item[edge])&&item[edge]>=0,'CROP_RANGE',edge);
        for(const key of ['align','bounds_align']) assert([0,1,2,4,5,6,8,9,10].includes(item[key]),'ALIGNMENT_RANGE',key);
        assert(Number.isInteger(item.bounds_type)&&item.bounds_type>=0&&item.bounds_type<=6,'BOUNDS_TYPE_RANGE');
        for(const key of ['pos','scale','bounds']) assert(validVector(item[key]),'TRANSFORM_VECTOR',`${source.name}/${item.id}/${key}`);
        for(const key of ['pos_rel','scale_rel','scale_ref','bounds_rel']) if(Object.hasOwn(item,key)) assert(validVector(item[key]),'TRANSFORM_VECTOR',key);
        for(const key of ['rot','align','bounds_type','bounds_align','crop_left','crop_top','crop_right','crop_bottom']) assert(typeof item[key]==='number'&&Number.isFinite(item[key]),'TRANSFORM_FIELD',`${source.name}/${item.id}/${key}`);
        if(doc.version===2) for(const key of ['pos_rel','scale_rel','scale_ref','bounds_rel']) assert(validVector(item[key]),'RELATIVE_TRANSFORM_REQUIRED',`${source.name}/${item.id}/${key}`);
        if(doc.version===1) assert(!['pos_rel','scale_rel','bounds_rel'].some(k=>Object.hasOwn(item,k)),'MIXED_COORDINATES',source.name);
      }
      assert(Number.isSafeInteger(source.settings.id_counter)&&source.settings.id_counter>=Math.max(0,...itemIds),'ITEM_COUNTER',source.name);
    }
  }
  assert(sceneCount>0&&sceneCount<=LIMITS.scenes,'SCENE_LIMIT'); assert(itemCount<=LIMITS.items,'ITEM_LIMIT');
  const map=sourceMap(doc);
  for(const source of doc.sources) if(source.id==='scene') for(const item of source.settings.items){
    assert(map.has(item.source_uuid),'MISSING_REFERENCE',`${source.name}/${item.id}`);
    assert(map.get(item.source_uuid).name===item.name,'REFERENCE_NAME_MISMATCH',`${source.name}/${item.id}`);
  }
  const visited=new Set(),active=new Set();
  function visit(id){if(visited.has(id))return; assert(!active.has(id),'NESTING_CYCLE',map.get(id).name); active.add(id); const s=map.get(id); if(s.id==='scene')for(const x of s.settings.items)if(map.get(x.source_uuid).id==='scene')visit(x.source_uuid);active.delete(id);visited.add(id);}
  for(const s of doc.sources)if(s.id==='scene')visit(s.uuid);
  const scenes=doc.sources.filter(s=>s.id==='scene').map(s=>s.name);
  assert(Array.isArray(doc.scene_order),'SCENE_ORDER_REQUIRED');
  assert(equal([...doc.scene_order.map(x=>x.name)].sort(),[...scenes].sort()),'SCENE_ORDER_MEMBERSHIP');
  for(const key of ['current_scene','current_program_scene']) if(doc[key]!==undefined)assert(scenes.includes(doc[key]),'CURRENT_SCENE_MISSING',key);
  return {sources:doc.sources.length,scenes:sceneCount,items:itemCount};
}
export function prepareCollection(doc,{name=doc.name}={}){
  validateCollection(doc); assert(typeof name==='string'&&name.trim().length>0&&name.length<=210,'COLLECTION_NAME');
  return Object.fromEntries(['baseline','operator','incoming'].map(role=>{const next=clone(doc);next.name=`${name.trim()} · ${role}`;return[role,next];}));
}
export function affectedScenes(doc,uuid){
  const parents=new Map(); for(const scene of doc.sources.filter(s=>s.id==='scene'))for(const item of scene.settings.items){if(!parents.has(item.source_uuid))parents.set(item.source_uuid,new Set());parents.get(item.source_uuid).add(scene.uuid);}
  const map=sourceMap(doc),seen=new Set(),queue=[uuid]; if(map.get(uuid)?.id==='scene')seen.add(uuid);
  while(queue.length) for(const parent of parents.get(queue.shift())||[])if(!seen.has(parent)){seen.add(parent);queue.push(parent);}
  return [...seen].map(id=>map.get(id).name).sort();
}
function status(b,o,i){if(equal(o,i))return equal(b,o)?'unchanged':'equal';if(equal(b,i))return'operator';if(equal(b,o))return'incoming';return'conflict';}
function validateAddedItem(item){
  const defaults={group_item_backup:false,scale_filter:'disable',blend_method:'default',blend_type:'normal',private_settings:{}};
  for(const [key,value] of Object.entries(rest(item,ITEM_KEYS))){
    if(['show_transition','hide_transition'].includes(key)){assert(object(value)&&Object.keys(value).every(k=>k==='duration')&&(!Object.hasOwn(value,'duration')||value.duration===0),'ADDED_ITEM_METADATA_UNSUPPORTED',key);continue;}
    assert(Object.hasOwn(defaults,key)&&equal(value,defaults[key]),'ADDED_ITEM_METADATA_UNSUPPORTED',key);
  }
}
function validateAddedSource(source,baseline){
  const defaults={mixers:[0,63,255],sync:0,flags:0,volume:1,balance:0.5,enabled:true,muted:false,'push-to-mute':false,'push-to-mute-delay':0,'push-to-talk':false,'push-to-talk-delay':0,deinterlace_mode:0,deinterlace_field_order:0,monitoring_type:0,private_settings:{},filters:[]};
  const templates=baseline.sources.filter(s=>s.id===source.id);
  for(const [key,value] of Object.entries(rest(source,SOURCE_KEYS))){
    if(['prev_ver','canvas_uuid'].includes(key)){assert(templates.some(t=>equal(t[key],value)),'ADDED_SOURCE_METADATA_UNSUPPORTED',key);continue;}
    if(key==='hotkeys'){assert(object(value)&&Object.values(value).every(v=>Array.isArray(v)&&v.length===0),'ADDED_SOURCE_METADATA_UNSUPPORTED',key);continue;}
    assert(Object.hasOwn(defaults,key)&&(key==='mixers'?defaults.mixers.includes(value):equal(defaults[key],value)),'ADDED_SOURCE_METADATA_UNSUPPORTED',key);
  }
  if(source.id==='scene'){
    for(const key of Object.keys(source.settings))assert(['items','id_counter','custom_size'].includes(key),'ADDED_SCENE_SETTING_UNSUPPORTED',key);
    source.settings.items.forEach(validateAddedItem);
  }
}
function pathLabel(source,kind,item){return `${source?.name||'Collection'}${item ? ' / item '+item.id : ''} / ${kind}`;}
export function analyze(baseline,operator,incoming){
  const errors=[]; let stats;
  try{for(const doc of [baseline,operator,incoming])validateCollection(doc); stats=validateCollection(operator);
    for(const key of ['version','resolution','migration_resolution']) assert(equal(baseline[key],operator[key])&&equal(baseline[key],incoming[key]),'PROFILE_MISMATCH',key);
    const b=sourceMap(baseline),o=sourceMap(operator),i=sourceMap(incoming);
    for(const [uuid,s] of b){assert(o.has(uuid)&&i.has(uuid),'ANCESTRY_OR_DELETION',s.name);for(const branch of [o,i])for(const key of ['name','id','versioned_id'])assert(equal(s[key],branch.get(uuid)[key]),'IDENTITY_OR_RENAME',`${s.name}/${key}`);}
  }catch(error){return{units:[],errors:[error.message],stats:stats||{sources:0,scenes:0,items:0}};}
  const b=sourceMap(baseline),o=sourceMap(operator),i=sourceMap(incoming),units=[];
  const plan={baseline:clone(baseline),operator:clone(operator),incoming:clone(incoming),units,errors,stats};
  function add(id,kind,source,bv,ov,iv,target,unsupported=false,forceConflict=false){
    let state=status(bv,ov,iv); if(unsupported&&!equal(bv,iv)&&!equal(ov,iv))state='unsupported'; else if(forceConflict)state='conflict';
    if(state==='unchanged')return;
    units.push({id,kind,sourceName:source?.name||null,label:pathLabel(source,kind,target?.item),status:state,baseline:clone(bv),operator:clone(ov),incoming:clone(iv),allowedChoices:state==='unsupported'?['exclude']:state==='conflict'?['operator','incoming']:[],affectedScenes:source?[...new Set([...affectedScenes(operator,source.uuid),...affectedScenes(incoming,source.uuid)])].sort():[],target});
  }
  // Outside the supported semantics, preserve the operator and require explicit exclusion of incoming changes.
  const extraKeys=new Set([...Object.keys(baseline),...Object.keys(operator),...Object.keys(incoming)].filter(k=>!UI_KEYS.has(k)));
  for(const key of extraKeys)add(`collection:${key}`,'collection-metadata',null,baseline[key],operator[key],incoming[key],{type:'top',key},true);
  const opAdded=operator.sources.filter(s=>!b.has(s.uuid)),inAdded=incoming.sources.filter(s=>!b.has(s.uuid));
  for(const s of [...opAdded,...inAdded])try{assert(s.id==='scene'||EDITABLE.has(s.id),'ADDED_SOURCE_KIND_UNSUPPORTED',s.name);validateAddedSource(s,baseline);}catch(error){errors.push(error.message);}
  for(const branch of [operator,incoming])for(const scene of branch.sources.filter(s=>s.id==='scene'&&b.has(s.uuid))){const original=itemMap(b.get(scene.uuid));for(const item of scene.settings.items)if(!original.has(itemKey(item)))try{validateAddedItem(item);}catch(error){errors.push(`${error.message}: ${scene.name}/${item.id}`);}}
  const collision=inAdded.some(s=>o.has(s.uuid)&&!equal(o.get(s.uuid),s));
  if(inAdded.length || opAdded.length){add('sources:added','added-source-closure',null,[],opAdded,inAdded,{type:'additions'},false,collision); if(!collision){const added=units.at(-1);added.status=inAdded.length?'incoming':'operator';added.allowedChoices=[];}}
  for(const [uuid,bs] of b){
    const os=o.get(uuid),is=i.get(uuid);
    add(`source:${uuid}:metadata`,'source-metadata',bs,rest(bs,SOURCE_KEYS),rest(os,SOURCE_KEYS),rest(is,SOURCE_KEYS),{type:'source-extras',uuid},true);
    if(bs.id!=='scene'){
      add(`source:${uuid}:settings`,'source-settings',bs,bs.settings,os.settings,is.settings,{type:'source-settings',uuid},!EDITABLE.has(bs.id)); continue;
    }
    add(`scene:${uuid}:settings`,'scene-metadata',bs,rest(bs.settings,new Set(['items','id_counter'])),rest(os.settings,new Set(['items','id_counter'])),rest(is.settings,new Set(['items','id_counter'])),{type:'scene-settings',uuid},true);
    const bm=itemMap(bs),om=itemMap(os),im=itemMap(is);
    // Remove-vs-edit must be decided as a complete scene; otherwise accepting deletion silently loses the edit.
    const removalEdit=[...bm].some(([key,x])=>(!om.has(key)&&im.has(key)&&!equal(x,im.get(key)))||(!im.has(key)&&om.has(key)&&!equal(x,om.get(key))));
    if(removalEdit){
      add(`scene:${uuid}:structure`,'scene-removal-edit',bs,pick(bs.settings,['items','id_counter']),pick(os.settings,['items','id_counter']),pick(is.settings,['items','id_counter']),{type:'whole-scene-settings',uuid},false,true);
      for(const [key,bi] of bm){const oi=om.get(key),ii=im.get(key);if(!ii)continue;
        if(!oi){if(!equal(rest(bi,ITEM_KEYS),rest(ii,ITEM_KEYS)))errors.push(`REMOVED_ITEM_METADATA_UNSUPPORTED: ${bs.name}/${bi.id}`);continue;}
        add(`item:${uuid}:${bi.id}:metadata`,'item-metadata',bs,rest(bi,ITEM_KEYS),rest(oi,ITEM_KEYS),rest(ii,ITEM_KEYS),{uuid,item:{id:bi.id,source_uuid:bi.source_uuid},type:'item-extras'},true);
      }
      continue;
    }
    // IDs allocated independently on branches only match when their source reference also matches.
    const parallelCollision=os.settings.items.some(x=>!bm.has(itemKey(x))&&is.settings.items.some(y=>y.id===x.id&&!bm.has(itemKey(y))&&!equal(x,y)));
    add(`scene:${uuid}:membership`,'membership-order',bs,membership(bs),membership(os),membership(is),{type:'membership',uuid},false,parallelCollision);
    for(const [key,bi] of bm){const oi=om.get(key),ii=im.get(key);if(!oi||!ii)continue;
      const target={uuid,item:{id:bi.id,source_uuid:bi.source_uuid}};
      add(`item:${uuid}:${bi.id}:transform`,'item-transform',bs,transform(bi),transform(oi),transform(ii),{...target,type:'transform'});
      for(const flag of ['visible','locked'])add(`item:${uuid}:${bi.id}:${flag}`,'item-'+flag,bs,bi[flag],oi[flag],ii[flag],{...target,type:'flag',key:flag});
      add(`item:${uuid}:${bi.id}:metadata`,'item-metadata',bs,rest(bi,ITEM_KEYS),rest(oi,ITEM_KEYS),rest(ii,ITEM_KEYS),{...target,type:'item-extras'},true);
    }
  }
  // Frontend scene order is significant but new scene presence is finalized from the selected source closure.
  add('collection:scene_order','scene-order',null,baseline.scene_order,operator.scene_order,incoming.scene_order,{type:'scene-order'});
  return plan;
}
function choiceFor(unit,decisions){const explicit=decisions[unit.id]; if(unit.status==='conflict'||unit.status==='unsupported'){assert(unit.allowedChoices.includes(explicit),'UNRESOLVED_DECISION',unit.id);return explicit;}return unit.status==='incoming'?'incoming':'operator';}
function chosenValue(unit,choice){return clone(choice==='incoming'?unit.incoming:unit.operator);}
export function resolve(plan,decisions={}, {name='SceneReconcile merged'}={}){
  assert(plan.errors?.length===0,'INVALID_INPUT',plan.errors?.join('; '));
  assert(typeof name==='string'&&name.trim()&&name.length<=255,'COLLECTION_NAME');
  const unresolved=plan.units.filter(u=>u.allowedChoices.length&&!u.allowedChoices.includes(decisions[u.id]));
  assert(!unresolved.length,'UNRESOLVED_DECISION',unresolved.map(u=>u.id).join(', '));
  const result=clone(plan.operator),changes=[],excluded=[]; result.name=name.trim();
  const branchMaps={operator:sourceMap(plan.operator),incoming:sourceMap(plan.incoming)};
  // Merge additions as a union except truly conflicting UUID identity additions, which require one whole-closure choice.
  const additions=plan.units.find(u=>u.target.type==='additions');
  if(additions){const choice=choiceFor(additions,decisions);const present=new Set(result.sources.map(s=>s.uuid));
    if(additions.status==='conflict'){
      if(choice==='incoming'){
        const baselineIds=new Set(plan.baseline.sources.map(s=>s.uuid)); result.sources=result.sources.filter(s=>baselineIds.has(s.uuid)); result.sources.push(...clone(additions.incoming));
      }
    } else for(const s of additions.incoming)if(!present.has(s.uuid)){result.sources.push(clone(s));present.add(s.uuid);}
  }
  let map=sourceMap(result);
  for(const unit of plan.units){
    const choice=choiceFor(unit,decisions),value=chosenValue(unit,choice),t=unit.target;
    if(choice==='exclude')excluded.push({id:unit.id,kind:unit.kind,sourceName:unit.sourceName,reason:'Incoming unsupported change explicitly excluded; operator retained'});
    const change={id:unit.id,kind:unit.kind,sourceName:unit.sourceName,status:unit.status,decision:choice,affectedScenes:[]};changes.push(change);
    if(t.type==='additions'||t.type==='scene-order')continue;
    if(t.type==='top'){if(value===undefined)delete result[t.key];else result[t.key]=value;continue;}
    const source=map.get(t.uuid); assert(source,'SELECTED_SOURCE_MISSING',t.uuid);
    if(t.type==='source-settings'){source.settings=value;continue;}
    if(t.type==='source-extras'){for(const k of Object.keys(source))if(!SOURCE_KEYS.has(k))delete source[k];Object.assign(source,value);continue;}
    if(t.type==='scene-settings'){for(const k of Object.keys(source.settings))if(!['items','id_counter'].includes(k))delete source.settings[k];Object.assign(source.settings,value);continue;}
    if(t.type==='whole-scene-settings'){source.settings.items=value.items;source.settings.id_counter=value.id_counter;continue;}
    if(t.type==='membership'){
      const selected=branchMaps[choice==='incoming'?'incoming':'operator'].get(t.uuid);const selectedItems=itemMap(selected),currentItems=itemMap(source);
      const originalItems=itemMap(sourceMap(plan.baseline).get(t.uuid)); source.settings.items=value.map(x=>clone(originalItems.has(itemKey(x)) ? (currentItems.get(itemKey(x)) || selectedItems.get(itemKey(x))) : selectedItems.get(itemKey(x))));continue;
    }
    const item=source.settings.items.find(x=>x.id===t.item.id&&x.source_uuid===t.item.source_uuid);
    if(!item)continue; // Only a selected membership removal can remove this atom; remove-vs-edit handled above.
    if(t.type==='transform')setFields(item,TRANSFORM_FIELDS,value);
    else if(t.type==='flag')item[t.key]=value;
    else if(t.type==='item-extras'){for(const k of Object.keys(item))if(!ITEM_KEYS.has(k))delete item[k];Object.assign(item,value);}
  }
  const sceneNames=new Set(result.sources.filter(s=>s.id==='scene').map(s=>s.name));
  const order=plan.units.find(u=>u.target.type==='scene-order');let preferred=order?chosenValue(order,choiceFor(order,decisions)):clone(result.scene_order);
  preferred=preferred.filter(x=>sceneNames.has(x.name));const listed=new Set(preferred.map(x=>x.name));
  for(const source of result.sources)if(source.id==='scene'&&!listed.has(source.name)){preferred.push({name:source.name});listed.add(source.name);}
  result.scene_order=preferred;
  for(const key of ['current_scene','current_program_scene'])if(!sceneNames.has(result[key]))result[key]=result.scene_order[0].name;
  for(const s of result.sources)if(s.id==='scene')s.settings.id_counter=Math.max(s.settings.id_counter||0,branchMaps.operator.get(s.uuid)?.settings.id_counter||0,branchMaps.incoming.get(s.uuid)?.settings.id_counter||0,...s.settings.items.map(x=>x.id));
  const stats=validateCollection(result);
  for(const change of changes){const source=result.sources.find(s=>s.name===change.sourceName);change.affectedScenes=source?affectedScenes(result,source.uuid):[];}
  const baselineIds=new Set(plan.baseline.sources.map(s=>s.uuid));
  const addedSources=result.sources.filter(s=>!baselineIds.has(s.uuid)).map(s=>({uuid:s.uuid,name:s.name,kind:s.id,affectedScenes:affectedScenes(result,s.uuid)}));
  return{collection:result,changes,addedSources,excluded,unresolved:[],stats};
}
export async function sha256(text){const bytes=typeof text==='string'?new TextEncoder().encode(text):text;const digest=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function buildReceipt(inputRecords,result,outputText){
  const inputs={};for(const role of ['baseline','operator','incoming']){const record=inputRecords[role];assert(record&&typeof record.text==='string','INPUT_HASH_SOURCE',role);inputs[role]={name:record.name||role,sha256:await sha256(record.text)};}
  return{format:'SceneReconcile decision receipt',version:1,profile:'OBS Studio 32.2.2 Linux / one canvas / prepared UUID-preserving imports',inputs,output:{name:result.collection.name,sha256:await sha256(outputText)},changes:clone(result.changes),addedSources:clone(result.addedSources),excluded:clone(result.excluded),unresolved:[],stats:clone(result.stats),limits:LIMITS,warning:'This receipt records the chosen configuration. It does not bundle assets or prove runtime compatibility for other OBS versions/platforms.'};
}
