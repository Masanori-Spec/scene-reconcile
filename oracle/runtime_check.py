"""Check real OBS API observations against the pre-authored semantic manifest."""
import argparse, hashlib, json
from pathlib import Path
from check import EXPECTED, ROOT, by_name, near, read

def check_observation(observation, baseline, incoming):
    assert observation['observationVersion'] == 1
    version = observation['obsVersion'].get('obsVersion', '')
    assert version == '32.2.2', f'unexpected consumer {version}'
    video = observation['video']
    assert video['baseWidth'] == EXPECTED['canvas']['width']
    assert video['baseHeight'] == EXPECTED['canvas']['height']
    b, i = by_name(baseline), by_name(incoming)
    uuid = {name: b[name]['uuid'] for name in EXPECTED['baselineSourceNames']}
    uuid.update({name: i[name]['uuid'] for name in EXPECTED['addedSourceNames']})
    sources = {}
    for item in observation['inputs']:
        assert item['inputName'] not in sources
        sources[item['inputName']] = item['inputUuid']
        assert item['inputUuid'] == uuid[item['inputName']]
        for key, value in EXPECTED['sourceSettings'].get(item['inputName'], {}).items():
            assert item['settings'].get(key) == value, (item['inputName'], key, item['settings'].get(key), value)
    scenes = observation['scenes']
    assert {s['sceneName'] for s in scenes} == set(EXPECTED['sceneItems'])
    for scene in scenes:
        name = scene['sceneName']
        sources[name] = scene['sceneUuid']
        assert scene['sceneUuid'] == uuid[name]
        assert scene['activeProgramSceneVerified'] is True
        actual = sorted(scene['items'], key=lambda x: x['sceneItemIndex'])
        expected = EXPECTED['sceneItems'][name]
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert a['sceneItemId'] == e['id'], (name, 'id', a['sceneItemId'], e['id'])
            assert a['sourceName'] == e['source'], (name, 'source', a['sourceName'], e['source'])
            assert a['sourceUuid'] == uuid[e['source']], (name, 'uuid')
            assert a['sceneItemEnabled'] is e['visible'], (name, 'visible')
            assert a['sceneItemLocked'] is e['locked'], (name, 'locked')
            transform = a['sceneItemTransform']
            near(transform['positionX'], e['x'], name+'/positionX')
            near(transform['positionY'], e['y'], name+'/positionY')
            for key, value in EXPECTED['unchangedTransformDefaults'].items():
                if isinstance(value, (int, float)):
                    near(transform[key], value, name+'/'+key)
                else:
                    assert transform[key] == value, (name,key,transform[key],value)
    assert sources == uuid, ('exact runtime source set', sources, uuid)
    for kind in ['stream','record','virtualcam']:
        assert observation['outputs'][kind]['outputActive'] is False, f'{kind} was unexpectedly active'
    return {'phase': observation['phase'], 'obsVersion': version, 'sourceCount': len(sources), 'sceneCount': len(scenes), 'runtimeManifest': 'pass', 'outputsInactive': True}

def main():
    p=argparse.ArgumentParser();p.add_argument('observation');p.add_argument('baseline');p.add_argument('incoming');p.add_argument('--report');a=p.parse_args()
    assert hashlib.sha256((ROOT/'expected.json').read_bytes()).hexdigest()==(ROOT/'expected.sha256').read_text().split()[0]
    report=check_observation(read(a.observation),read(a.baseline),read(a.incoming))
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
