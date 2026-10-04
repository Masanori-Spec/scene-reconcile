"""Independent reader: no imports from product code and no expected values derived from output."""
import argparse, hashlib, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = json.loads((ROOT / 'expected.json').read_text())
TRANSFORM = EXPECTED['transformAtomFields']

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def by_name(doc):
    result = {}
    uuids = set()
    for source in doc['sources']:
        name = source['name']
        assert name not in result, f'duplicate name: {name}'
        assert source['uuid'] not in uuids, 'duplicate UUID'
        uuids.add(source['uuid'])
        result[name] = source
    return result

def atom(item):
    return {key: item[key] for key in TRANSFORM if key in item}

def near(actual, expected, path):
    assert isinstance(actual, (int, float)) and math.isfinite(actual), f'{path}: not finite'
    assert abs(actual - expected) <= 0.03, f'{path}: {actual} != {expected}'

def check_collection(output, baseline, operator, incoming):
    b, o, i, out = map(by_name, (baseline, operator, incoming, output))
    required = EXPECTED['baselineSourceNames'] + EXPECTED['addedSourceNames']
    assert set(out) == set(required), ('source names', sorted(out))
    assert len(out) == EXPECTED['expectedSourceCount']
    expected_uuid = {name: b[name]['uuid'] for name in EXPECTED['baselineSourceNames']}
    expected_uuid.update({name: i[name]['uuid'] for name in EXPECTED['addedSourceNames']})
    assert {name: source['uuid'] for name, source in out.items()} == expected_uuid, 'identity mismatch'
    for name, settings in EXPECTED['sourceSettings'].items():
        for key, value in settings.items():
            assert out[name]['settings'].get(key) == value, (name, key, value, out[name]['settings'].get(key))
    for name, source_name in [('Background', 'operator'), ('Banner', 'baseline'), ('Title', 'incoming'), ('ThanksText', 'incoming')]:
        branch = {'operator': o, 'baseline': b, 'incoming': i}[source_name]
        assert out[name]['settings'] == branch[name]['settings'], f'{name}: entire source-settings atom changed'
    for scene, expected_items in EXPECTED['sceneItems'].items():
        actual = out[scene]['settings']['items']
        assert len(actual) == len(expected_items), f'{scene}: membership count'
        assert [(x['id'], x['source_uuid']) for x in actual] == [(x['id'], expected_uuid[x['source']]) for x in expected_items], f'{scene}: ordered membership/references'
        for item, expected in zip(actual, expected_items):
            assert item['name'] == expected['source'], f'{scene}: wrong name fallback'
            assert item['visible'] is expected['visible'], f'{scene}: visibility'
            assert item['locked'] is expected['locked'], f'{scene}: lock'
            near(item['pos']['x'], expected['x'], f'{scene}/{item["id"]}/x')
            near(item['pos']['y'], expected['y'], f'{scene}/{item["id"]}/y')
            branch = o if scene == 'Main' else i if scene in ['Break', 'Thanks'] else b
            reference = next(x for x in branch[scene]['settings']['items'] if x['id'] == item['id'])
            assert atom(item) == atom(reference), f'{scene}/{item["id"]}: complete transform atom differs'
    return {'sourceCount': len(out), 'sceneCount': len(EXPECTED['sceneItems']), 'uuidIdentity': 'exact', 'orderedMembership': 'exact', 'transformAtoms': 'exact', 'semanticManifest': 'pass'}

def check_receipt(receipt, input_paths, output_path):
    for role, path in zip(('baseline', 'operator', 'incoming'), input_paths):
        assert receipt['inputs'][role]['sha256'] == hashlib.sha256(Path(path).read_bytes()).hexdigest(), f'{role}: input hash'
    assert receipt['output']['sha256'] == hashlib.sha256(Path(output_path).read_bytes()).hexdigest(), 'output hash'
    impacts = [x for x in receipt['changes'] if x.get('sourceName') == 'Title' and x.get('kind') == 'source-settings']
    assert len(impacts) == 1, 'Title change record'
    assert sorted(impacts[0]['affectedScenes']) == EXPECTED['titleAffectedScenes'], 'Title transitive impact / hidden use'
    assert any(x.get('name') == 'ThanksText' for x in receipt['addedSources']), 'added dependency receipt'
    assert not receipt.get('unresolved'), 'unresolved decisions exported'
    return {'hashes': 'pass', 'hiddenTransitiveImpact': 'pass', 'addedDependencyReceipt': 'pass'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('output'); p.add_argument('baseline'); p.add_argument('operator'); p.add_argument('incoming')
    p.add_argument('--receipt'); p.add_argument('--report')
    a = p.parse_args()
    assert hashlib.sha256((ROOT/'expected.json').read_bytes()).hexdigest() == (ROOT/'expected.sha256').read_text().split()[0], 'handwritten manifest changed'
    report = check_collection(*map(read, [a.output, a.baseline, a.operator, a.incoming]))
    if a.receipt: report.update(check_receipt(read(a.receipt), [a.baseline, a.operator, a.incoming], a.output))
    if a.report: Path(a.report).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
if __name__ == '__main__': main()
