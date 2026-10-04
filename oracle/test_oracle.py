"""Mutation tests proving that the independent readers reject wrong results."""
import copy, json, unittest
from pathlib import Path
from check import EXPECTED, check_collection
from runtime_check import check_observation
ROOT = Path(__file__).resolve().parents[1]
def load(name): return json.loads((ROOT/'generated'/('synthetic-'+name+'.json')).read_text())
def source(doc,name): return next(s for s in doc['sources'] if s['name']==name)
class OracleTests(unittest.TestCase):
 def setUp(self):self.b,self.o,self.i,self.out=[load(n) for n in ['baseline','operator','incoming','merged']]
 def check(self):return check_collection(self.out,self.b,self.o,self.i)
 def test_expected(self):self.assertEqual(self.check()['semanticManifest'],'pass')
 def test_wrong_count(self):self.out['sources'].pop();self.assertRaises(AssertionError,self.check)
 def test_wrong_uuid(self):source(self.out,'Title')['uuid']='wrong';self.assertRaises(AssertionError,self.check)
 def test_wrong_title(self):source(self.out,'Title')['settings']['text']='18:00';self.assertRaises(AssertionError,self.check)
 def test_wrong_background(self):source(self.out,'Background')['settings']['color']=0;self.assertRaises(AssertionError,self.check)
 def test_wrong_transform(self):source(self.out,'Main')['settings']['items'][1]['pos']['x']=120;self.assertRaises(AssertionError,self.check)
 def test_dropped_relative_atom(self):source(self.out,'Main')['settings']['items'][1]['scale_ref']={'x':1,'y':1};self.assertRaises(AssertionError,self.check)
 def test_hidden_became_visible(self):source(self.out,'Break')['settings']['items'][1]['visible']=True;self.assertRaises(AssertionError,self.check)
 def test_stack_changed(self):source(self.out,'Main')['settings']['items'].reverse();self.assertRaises(AssertionError,self.check)
 def test_reference_changed(self):source(self.out,'Thanks')['settings']['items'][0]['source_uuid']=source(self.out,'Main')['uuid'];self.assertRaises(AssertionError,self.check)
 def test_duplicate_settings(self):source(self.out,'Title')['settings']['extra']='silently inserted';self.assertRaises(AssertionError,self.check)
 def observation(self):
  uuid={s['name']:s['uuid'] for s in self.out['sources']}
  return {'observationVersion':1,'phase':'synthetic-oracle-test','obsVersion':{'obsVersion':'32.2.2'},'video':{'baseWidth':1280,'baseHeight':720},'inputs':[{'inputName':name,'inputUuid':uuid[name],'settings':settings} for name,settings in EXPECTED['sourceSettings'].items()], 'scenes':[{'sceneName':name,'sceneUuid':uuid[name],'activeProgramSceneVerified':True,'items':[{'sourceName':e['source'],'sourceUuid':uuid[e['source']],'sceneItemId':e['id'],'sceneItemIndex':idx,'sceneItemEnabled':e['visible'],'sceneItemLocked':e['locked'],'sceneItemTransform':dict(EXPECTED['unchangedTransformDefaults'],positionX=e['x'],positionY=e['y'])} for idx,e in enumerate(items)]} for name,items in EXPECTED['sceneItems'].items()], 'outputs':{k:{'outputActive':False} for k in ['stream','record','virtualcam']}}
 def test_runtime_expected(self):self.assertEqual(check_observation(self.observation(),self.b,self.i)['runtimeManifest'],'pass')
 def test_runtime_wrong_scale(self):o=self.observation();o['scenes'][0]['items'][0]['sceneItemTransform']['scaleX']=2;self.assertRaises(AssertionError,check_observation,o,self.b,self.i)
 def test_runtime_active_output(self):o=self.observation();o['outputs']['stream']['outputActive']=True;self.assertRaises(AssertionError,check_observation,o,self.b,self.i)
 def test_runtime_wrong_consumer(self):o=self.observation();o['obsVersion']['obsVersion']='31.0.0';self.assertRaises(AssertionError,check_observation,o,self.b,self.i)
 def test_runtime_missing_scene(self):o=self.observation();o['scenes'].pop();self.assertRaises(AssertionError,check_observation,o,self.b,self.i)
if __name__=='__main__':unittest.main()
