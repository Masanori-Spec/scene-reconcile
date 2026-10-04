import test from 'node:test';import assert from 'node:assert/strict';
import {analyze,resolve,validateCollection} from '../src/core.mjs';import {fixtures,source,item} from './fixture.mjs';
test('explicit scene-metadata exclusion survives removal/edit structure choice',()=>{const f=fixtures();source(f.operator,'Break').settings.items.pop();source(f.incoming,'Break').settings.unknown_semantics='incoming';const p=analyze(f.baseline,f.operator,f.incoming);assert.deepEqual(p.errors,[]);const decisions=Object.fromEntries(p.units.filter(x=>x.allowedChoices.length).map(x=>[x.id,x.status==='unsupported'?'exclude':'incoming']));const r=resolve(p,decisions);assert.equal(source(r.collection,'Break').settings.unknown_semantics,undefined);assert.equal(r.excluded.length,1);assert.equal(source(r.collection,'Break').settings.items[1].pos.x,40);});
test('item-metadata exclusion survives complete scene contents choice',()=>{const f=fixtures();source(f.operator,'Break').settings.items.shift();source(f.incoming,'Break').settings.items[0].pos.x=10;source(f.incoming,'Break').settings.items[1].blend_type='multiply';const p=analyze(f.baseline,f.operator,f.incoming);assert.deepEqual(p.errors,[]);const decisions=Object.fromEntries(p.units.filter(x=>x.allowedChoices.length).map(x=>[x.id,x.status==='unsupported'?'exclude':'incoming']));const r=resolve(p,decisions);assert.equal(source(r.collection,'Break').settings.items[1].blend_type,'normal');assert.equal(r.excluded.length,1);});
test('operator-removed item cannot smuggle incoming unsupported metadata via restore',()=>{const f=fixtures();source(f.operator,'Break').settings.items.pop();source(f.incoming,'Break').settings.items[1].blend_type='multiply';assert.match(analyze(f.baseline,f.operator,f.incoming).errors.join(' '),/REMOVED_ITEM_METADATA_UNSUPPORTED/);});
for(const [label,mutate,pattern]of[
 ['unknown new scene setting',f=>source(f.incoming,'Thanks').settings.unknown_semantics=true,/ADDED_SCENE_SETTING_UNSUPPORTED/],
 ['new source monitoring metadata',f=>source(f.incoming,'ThanksText').monitoring_type=2,/ADDED_SOURCE_METADATA_UNSUPPORTED/],
 ['new source unknown metadata',f=>source(f.incoming,'ThanksText').unknown_semantics=true,/ADDED_SOURCE_METADATA_UNSUPPORTED/],
 ['new item blend',f=>{const s=source(f.incoming,'Main');s.settings.items.push({...item(3,'Title'),blend_type:'multiply'});s.settings.id_counter=3;},/ADDED_ITEM_METADATA_UNSUPPORTED/],
 ['new-scene item blend',f=>source(f.incoming,'Thanks').settings.items[0].blend_type='multiply',/ADDED_ITEM_METADATA_UNSUPPORTED/],
 ['new source unknown versioned plugin',f=>source(f.incoming,'ThanksText').versioned_id='unrecognized_plugin',/SOURCE_VERSION_UNSUPPORTED/],
 ['new source unknown native setting',f=>source(f.incoming,'ThanksText').settings.unknown_semantics=true,/SOURCE_SETTING_UNSUPPORTED/]
])test('reject '+label,()=>{const f=fixtures();mutate(f);const p=analyze(f.baseline,f.operator,f.incoming);assert.match(p.errors.join(' '),pattern);assert.throws(()=>resolve(p),/INVALID_INPUT/);});
test('unchanged custom transition/filter rejected throughout collection',()=>{const d=fixtures().baseline;d.transitions=[{name:'Custom',id:'custom_plugin',versioned_id:'custom_plugin',settings:{},filters:[{id:'filter'}]}];assert.throws(()=>validateCollection(d),/SOURCE_KIND_UNSUPPORTED/);});
test('builtin transition with unsupported filter rejected',()=>{const d=fixtures().baseline;d.transitions=[{name:'Fade',id:'fade_transition',versioned_id:'fade_transition',settings:{},filters:[{id:'filter'}]}];assert.throws(()=>validateCollection(d),/FILTERS_UNSUPPORTED/);});
test('custom global audio source rejected',()=>{const d=fixtures().baseline;d.DesktopAudioDevice1={name:'Device',id:'custom_plugin',versioned_id:'custom_plugin',settings:{}};assert.throws(()=>validateCollection(d),/SOURCE_KIND_UNSUPPORTED/);});
test('nonempty custom module rejected while native builtins allowed',()=>{const d=fixtures().baseline;d.modules={'output-timer':{autoStartStreamTimer:false},'auto-scene-switcher':{active:false},'scripts-tool':[]};assert.doesNotThrow(()=>validateCollection(d));d.modules['custom-module']={enabled:true};assert.throws(()=>validateCollection(d),/MODULES_UNSUPPORTED/);});

test('malformed embedded source cannot bypass validation by omitting settings',()=>{const d=fixtures().baseline;d.transitions=[{id:'unrecognized_plugin'}];assert.throws(()=>validateCollection(d),/EMBEDDED_SOURCE_SETTINGS_REQUIRED/);});

for(const [label,edit,pattern]of[
 ['object text',f=>source(f.incoming,'Title').settings.text={unknown_semantics:'payload'},/TEXT_SETTING_TYPE/],
 ['malformed font',f=>source(f.incoming,'Title').settings.font={face:{unknown:'value'},size:-1,flags:'garbage'},/FONT_SETTING_TYPE/],
 ['negative font size',f=>source(f.incoming,'Title').settings.font.size=-1,/FONT_SIZE_RANGE/],
 ['malformed color',f=>source(f.incoming,'Banner').settings={color:'not-a-number',width:-100,height:'bad'},/COLOR_DIMENSION_RANGE/],
 ['vector extra fields',f=>source(f.incoming,'Break').settings.items[1].pos.unknown_semantics={enabled:true},/TRANSFORM_VECTOR/],
 ['missing source kind',f=>f.incoming.transitions=[{name:'Custom',versioned_id:'custom_plugin',settings:{}}],/SOURCE_KIND_UNSUPPORTED/]
])test('typed profile rejects '+label,()=>{const f=fixtures();edit(f);assert.match(analyze(f.baseline,f.operator,f.incoming).errors.join(' '),pattern);});

test('dangling or non-main canvas UUID is rejected before merge',()=>{const f=fixtures();source(f.operator,'Main').canvas_uuid='10000000-0000-4000-8000-000000009999';assert.match(analyze(f.baseline,f.operator,f.incoming).errors.join(' '),/CANVAS_REFERENCE_UNSUPPORTED/);});
