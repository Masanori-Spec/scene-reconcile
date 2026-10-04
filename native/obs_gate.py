#!/usr/bin/env python3
"""Disposable GitHub Actions OBS 32.2.2 native-consumer gate.

The UI Import route is mandatory. websocket only creates native fixtures, edits
fixture scenes and reads runtime state. No generated JSON is passed off as an OBS
export. No application merge implementation is imported into this controller.
"""
from __future__ import annotations
import argparse
import base64
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

OBS_VERSION = '32.2.2'
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def progress(event, **fields):
    print(json.dumps({'nativeGate': event, 'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **fields}), flush=True)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_ci():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_OS') != 'Linux':
        raise RuntimeError('Native OBS execution is CI-only. Run this gate in GitHub Actions ubuntu-24.04.')
    release = Path('/etc/os-release').read_text()
    if 'VERSION_ID="24.04"' not in release or not os.environ.get('DISPLAY'):
        raise RuntimeError('Ubuntu 24.04 and an Xvfb DISPLAY are required.')
    for command in ('obs', 'xdotool', 'import', 'tesseract'):
        if not shutil.which(command):
            raise RuntimeError(f'Missing native-gate dependency: {command}')


SEMANTIC_FAILURES = (
    r"\[scene_load_item\].*(?:not found|Could not add)",
    r"Source ID '.+' not found",
    r"Failed to create source",
    r"obs_source_create failed",
    r"Failed to load source",
    r"duplicate UUID",
    r"Not all sources were cleared",
    r"Missing Files",
)
# These are optional-hardware/renderer diagnostics, never source-load errors.
# Everything else remains explicitly listed for artifact review.
ENVIRONMENT_DIAGNOSTICS = (
    r"Failed to initialize module '(?:aja|decklink)\.so'",
    r"Failed to load module '(?:aja|decklink)\.so'",
    r"Failed to open VDPAU backend",
    r"libEGL warning: DRI2: failed to authenticate",
    r"Failed to create avahi client",
)


def inspect_log(text):
    lines = text.splitlines()
    semantic = [line for line in lines if any(re.search(p, line, re.I) for p in SEMANTIC_FAILURES)]
    environmental = [line for line in lines if any(re.search(p, line, re.I) for p in ENVIRONMENT_DIAGNOSTICS)]
    diagnostic = [line for line in lines if re.search(r'warning|error|failed|not found|not available|not loaded', line, re.I)]
    return {'semanticFailures': semantic, 'toleratedEnvironmentDiagnostics': environmental,
            'otherDiagnosticsForReview': [line for line in diagnostic if line not in semantic and line not in environmental]}


def check_fixture_file(path):
    """Prevent an accidental app regression from loading device/script sources."""
    value = json.loads(Path(path).read_text())
    allowed = {'scene', 'color_source', 'text_ft2_source'}
    if any(key.startswith(('DesktopAudioDevice', 'AuxAudioDevice')) for key in value):
        raise AssertionError('The native fixture gate cannot import global audio devices')
    if value.get('groups') or value.get('canvases'):
        raise AssertionError('The native fixture gate expects no groups or extra canvases')
    scripts = value.get('modules', {}).get('scripts-tool', [])
    if scripts:
        raise AssertionError('The native fixture gate cannot import executable OBS scripts')
    permitted_names = {'Main', 'Break', 'LowerThird', 'Background', 'Banner', 'Title', 'Thanks', 'ThanksText'}
    if any(source.get('name') not in permitted_names for source in value['sources']):
        raise AssertionError('Unexpected source name outside this fixed native fixture')
    for source in value['sources']:
        native_kind = re.sub(r'_v\d+$', '', source.get('versioned_id', source['id']))
        if source['id'] not in allowed or native_kind != source['id'] or source.get('filters'):
            raise AssertionError(f'Unexpected source kind/filter in native fixture: {source.get("name")}')
        if source['id'] == 'text_ft2_source' and source.get('settings', {}).get('from_file'):
            raise AssertionError('File-backed text is outside the native fixture gate')
    return value


def runtime_semantics(observation):
    """Comparable native readings only, excluding phase and UI-current-scene state."""
    return {
        'video': observation['video'],
        'inputs': sorted(observation['inputs'], key=lambda x: x['inputUuid']),
        'scenes': sorted([{'sceneName': scene['sceneName'], 'sceneUuid': scene['sceneUuid'],
            'items': sorted(scene['items'], key=lambda x: x['sceneItemIndex'])}
            for scene in observation['scenes']], key=lambda x: x['sceneUuid'])}


class RPC:
    def __init__(self, port, password):
        # Ubuntu's python3-websocket package, loaded only in hosted native runs.
        import websocket
        self.ws = websocket.create_connection(f'ws://127.0.0.1:{port}', timeout=12,
                                                http_proxy_host=None, suppress_origin=True)
        hello = json.loads(self.ws.recv())
        assert hello['op'] == 0, hello
        identify = {'rpcVersion': 1, 'eventSubscriptions': 0}
        auth = hello['d'].get('authentication')
        if not auth:
            raise RuntimeError('OBS websocket unexpectedly lacks required authentication')
        secret = base64.b64encode(hashlib.sha256((password + auth['salt']).encode()).digest()).decode()
        identify['authentication'] = base64.b64encode(hashlib.sha256((secret + auth['challenge']).encode()).digest()).decode()
        self.ws.send(json.dumps({'op': 1, 'd': identify}))
        response = json.loads(self.ws.recv())
        assert response['op'] == 2, response
        self.counter = 0

    def call(self, method, **data):
        self.counter += 1
        request_id = str(self.counter)
        self.ws.send(json.dumps({'op': 6, 'd': {'requestType': method, 'requestId': request_id, 'requestData': data}}))
        while True:
            response = json.loads(self.ws.recv())
            if response['op'] != 7 or response['d']['requestId'] != request_id:
                continue
            payload = response['d']
            if not payload['requestStatus']['result']:
                raise RuntimeError(f'{method}: {payload["requestStatus"]}')
            return payload.get('responseData', {})

    def close(self):
        self.ws.close()


class NativeOBS:
    def __init__(self, evidence, label):
        self.evidence = Path(evidence).resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.label = label
        self.temp = tempfile.TemporaryDirectory(prefix='scene-reconcile-native-')
        self.home = Path(self.temp.name)
        self.config = self.home / '.config' / 'obs-studio'
        self.scenes_dir = self.config / 'basic' / 'scenes'
        self.scenes_dir.mkdir(parents=True)
        profile = self.config / 'basic' / 'profiles' / 'Fixture'
        profile.mkdir(parents=True)
        self.password = secrets.token_urlsafe(32)
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        # This seed only bootstraps an empty collection without default audio
        # capture devices. All six baseline sources are created in running OBS.
        write_json(self.scenes_dir / 'Bootstrap.json', {
            'name': 'SceneReconcileBaseline', 'current_scene': 'Bootstrap',
            'current_program_scene': 'Bootstrap', 'scene_order': [{'name': 'Bootstrap'}],
            'sources': [{'name': 'Bootstrap', 'id': 'scene', 'settings': {'items': []}}],
            'groups': [], 'transitions': [], 'quick_transitions': [],
            'current_transition': 'Fade', 'transition_duration': 300,
            'preview_locked': False, 'scaling_enabled': False,
            'modules': {}, 'version': 2,
            'resolution': {'x': 1280, 'y': 720},
            # Version 2 deliberately uses OBS's native relative-coordinate mode.
            # Native API setters/readers still expose absolute canvas pixels.
        })
        (self.config / 'global.ini').write_text(
            '[General]\nLanguage=en-US\nLastVersion=537001986\nEnableAutoUpdates=false\n'
        )
        (self.config / 'user.ini').write_text(
            '[General]\nLanguage=en-US\nFirstRun=true\nAutoSearchPrompt=true\nAutomaticCollectionSearch=false\n'
            '[Basic]\nProfile=Fixture\nProfileDir=Fixture\nSceneCollection=SceneReconcileBaseline\nSceneCollectionFile=Bootstrap\n'
            '[BasicWindow]\nStudioMode=false\nPreviewEnabled=true\nWarnBeforeStartingStream=true\n'
        )
        (profile / 'basic.ini').write_text(
            '[General]\nName=Fixture\n'
            '[Video]\nBaseCX=1280\nBaseCY=720\nOutputCX=1280\nOutputCY=720\nFPSType=0\nFPSCommon=30\n'
            '[Audio]\nSampleRate=48000\nChannelSetup=Stereo\nDesktopDevice1=disabled\nDesktopDevice2=disabled\nAuxDevice1=disabled\nAuxDevice2=disabled\nAuxDevice3=disabled\n'
            '[Output]\nMode=Simple\n'
        )
        plugin_config = self.config / 'plugin_config' / 'obs-websocket' / 'config.json'
        write_json(plugin_config, {'first_load': False, 'server_enabled': True,
            'server_port': self.port, 'alerts_enabled': False, 'auth_required': True,
            'server_password': self.password})
        plugin_config.chmod(0o600)
        runtime = self.home / '.runtime'
        runtime.mkdir(mode=0o700)
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / '.config'),
            XDG_DATA_HOME=str(self.home / '.local' / 'share'), XDG_CACHE_HOME=str(self.home / '.cache'),
            XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM='xcb', QT_SCALE_FACTOR='1',
            LIBGL_ALWAYS_SOFTWARE='1', PULSE_SERVER='unix:/nonexistent-scene-reconcile-audio',
            LC_ALL='C.UTF-8', LANG='C.UTF-8')
        self.proc = None
        self.rpc = None
        self.launch_count = 0

    def cmd(self, *args, check=True, timeout=10):
        progress('command-start', command=args[0], action=args[1] if len(args) > 1 else '', timeoutSeconds=timeout)
        try:
            result = subprocess.run(args, env=self.env, check=check, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            progress('command-timeout', command=args[0], action=args[1] if len(args) > 1 else '', timeoutSeconds=timeout)
            raise
        return result.stdout.strip()

    def start(self):
        self.launch_count += 1
        progress('obs-start', label=self.label, launch=self.launch_count)
        log = self.evidence / f'{self.label}-{self.launch_count}-process.log'
        self.process_log = log
        self.log_handle = log.open('w')
        self.proc = subprocess.Popen(['obs', '--multi', '--disable-updater',
            '--websocket_ipv4_only'], env=self.env, stdout=self.log_handle, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 80
        last_error = None
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f'OBS exited with {self.proc.returncode}; inspect {log}')
            try:
                self.rpc = RPC(self.port, self.password)
                # Identify can succeed before OBS FINISHED_LOADING. An actual
                # request is the readiness probe; NotReady is retried boundedly.
                version = self.rpc.call('GetVersion')
                break
            except Exception as exc:
                last_error = str(exc)
                if self.rpc is not None:
                    self.rpc.close()
                    self.rpc = None
                time.sleep(1)
        else:
            self.desktop(f'{self.label}-{self.launch_count}-startup-failure')
            raise RuntimeError(f'OBS websocket not ready: {last_error}; inspect {log}')
        if version['obsVersion'] != OBS_VERSION:
            raise AssertionError(f'Expected official OBS {OBS_VERSION}; got {version}')
        special = self.rpc.call('GetSpecialInputs')
        if any(value is not None for value in special.values()):
            raise AssertionError(f'Unexpected audio capture source(s): {special}')
        self.assert_outputs_off()
        progress('obs-ready', label=self.label, launch=self.launch_count, obsVersion=version['obsVersion'])
        self.desktop(f'{self.label}-{self.launch_count}-started')

    def assert_outputs_off(self):
        outputs = {key: self.rpc.call(method) for key, method in [
            ('stream', 'GetStreamStatus'), ('record', 'GetRecordStatus'), ('virtualcam', 'GetVirtualCamStatus')]}
        if any(o['outputActive'] for o in outputs.values()):
            raise AssertionError('Unexpected active stream/record/virtual camera output')
        return outputs

    def desktop(self, label, timeout=10):
        path = self.evidence / f'{label}.png'
        self.cmd('import', '-window', 'root', str(path), timeout=timeout)
        if not path.read_bytes().startswith(PNG_MAGIC):
            raise AssertionError(f'Invalid desktop screenshot: {path}')
        return path

    def windows(self, title):
        result = subprocess.run(['xdotool', 'search', '--all', '--onlyvisible', '--pid', str(self.proc.pid),
            '--name', title], env=self.env, capture_output=True, text=True, timeout=5)
        return result.stdout.split()

    def wait_window(self, title, timeout=12):
        progress('window-wait', title=title, timeoutSeconds=timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            windows = self.windows(title)
            if windows:
                return windows[-1]
            time.sleep(.2)
        self.desktop(f'{self.label}-missing-window')
        raise RuntimeError(f'Native UI window not found: {title}')

    def focus(self, window):
        self.cmd('xdotool', 'windowactivate', '--sync', window)
        time.sleep(.15)

    def click_text(self, text, label):
        """Bounded, screenshot-driven polling; click at most once after finding it."""
        progress('native-button-wait', text=text, label=label, timeoutSeconds=15)
        deadline = time.monotonic() + 15
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            screenshot = self.desktop(f'{label}-{attempt}', timeout=max(.2, min(5, deadline - time.monotonic())))
            result = self.cmd('tesseract', str(screenshot), 'stdout', '--psm', '11', 'tsv',
                              timeout=max(.2, min(8, deadline - time.monotonic())))
            rows = list(csv.DictReader(io.StringIO(result), delimiter='\t'))
            candidates = [r for r in rows if r.get('text', '').rstrip('.…').lower() == text.lower()
                          and float(r.get('conf', '-1')) >= 35]
            if candidates:
                # Dialog buttons are below title words with the same spelling.
                word = max(candidates, key=lambda r: int(r['top']))
                x = int(word['left']) + int(word['width']) // 2
                y = int(word['top']) + int(word['height']) // 2
                self.cmd('xdotool', 'mousemove', '--sync', str(x), str(y), 'click', '1')
                progress('native-button-clicked', text=text, label=label)
                time.sleep(.3)
                return
            time.sleep(.3)
        raise RuntimeError(f'Native UI button {text!r} not found within 15 seconds; inspect {label} screenshots')

    def wait_window_closed(self, title, timeout=12):
        progress('window-close-wait', title=title, timeoutSeconds=timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.windows(title):
                return
            time.sleep(.2)
        self.desktop(f'{self.label}-window-did-not-close')
        raise RuntimeError(f'Native UI window did not close: {title}')

    def import_collection(self, path, label):
        path = Path(path).resolve()
        progress('native-import-start', label=label, file=path.name)
        before_hash = digest(path)
        original = check_fixture_file(path)
        before = set(self.rpc.call('GetSceneCollectionList')['sceneCollections'])
        main = self.wait_window('^OBS ')
        self.focus(main)
        # Source-pinned mnemonic. Locate Import by rendered text, because Qt
        # skips disabled menu entries (Remove is disabled for one collection).
        self.cmd('xdotool', 'key', '--clearmodifiers', 'alt+s')
        time.sleep(.2)
        self.click_text('Import', f'{label}-collection-menu')
        dialog = self.wait_window('^Import Scene Collection$')
        self.focus(dialog)
        self.click_text('Browse', f'{label}-import-dialog')
        picker = self.wait_window('^Select a Scene Collection$')
        self.focus(picker)
        self.cmd('xdotool', 'key', '--clearmodifiers', 'ctrl+l')
        self.cmd('xdotool', 'type', '--clearmodifiers', '--delay', '1', str(path))
        self.desktop(f'{label}-file-selected')
        self.cmd('xdotool', 'key', 'Return')
        self.wait_window_closed('^Select a Scene Collection$')
        self.focus(dialog)
        self.click_text('Import', f'{label}-ready-to-import')
        deadline = time.monotonic() + 12
        added = set()
        while time.monotonic() < deadline:
            after = set(self.rpc.call('GetSceneCollectionList')['sceneCollections'])
            added = after - before
            if added:
                break
            time.sleep(.3)
        if len(added) != 1:
            self.desktop(f'{label}-import-failure')
            raise AssertionError(f'UI Import did not add exactly one collection: {added}')
        collection = added.pop()
        self.rpc.call('SetCurrentSceneCollection', sceneCollectionName=collection)
        time.sleep(.7)
        self.desktop(f'{label}-imported')
        if digest(path) != before_hash:
            raise AssertionError('Native import mutated its supplied file')
        imported_uuids = self.source_identities()
        expected_uuids = {s['name']: s['uuid'] for s in original['sources']}
        if imported_uuids != expected_uuids:
            raise AssertionError(f'Native UI Import changed sources/UUIDs: {imported_uuids} != {expected_uuids}')
        write_json(self.evidence / f'{label}-import-proof.json', {'route': 'native UI Scene Collection > Import',
            'inputFile': path.name, 'inputSha256': before_hash, 'collection': collection,
            'sourceUuidsPreserved': True, 'sourceIdentities': imported_uuids})
        progress('native-import-verified', label=label, collection=collection, sources=len(imported_uuids))
        return collection

    def source_identities(self):
        scenes = self.rpc.call('GetSceneList')['scenes']
        inputs = self.rpc.call('GetInputList')['inputs']
        result = {s['sceneName']: s['sceneUuid'] for s in scenes}
        result.update({s['inputName']: s['inputUuid'] for s in inputs})
        if len(set(result.values())) != len(result):
            raise AssertionError('Duplicate source UUIDs in native runtime')
        return result

    def observe(self, label):
        progress('observation-start', label=label)
        folder = self.evidence / label
        folder.mkdir(parents=True, exist_ok=True)
        result = {'observationVersion': 1, 'phase': label, 'obsVersion': self.rpc.call('GetVersion'),
            'video': self.rpc.call('GetVideoSettings'),
            'sceneCollection': self.rpc.call('GetSceneCollectionList'), 'inputs': [], 'scenes': [],
            'outputs': self.assert_outputs_off()}
        for source in self.rpc.call('GetInputList')['inputs']:
            value = dict(source)
            value['settings'] = self.rpc.call('GetInputSettings', inputUuid=source['inputUuid'])['inputSettings']
            result['inputs'].append(value)
        for scene in self.rpc.call('GetSceneList')['scenes']:
            value = dict(scene)
            name, uuid = scene['sceneName'], scene['sceneUuid']
            progress('scene-observe', label=label, scene=name)
            self.rpc.call('SetCurrentProgramScene', sceneUuid=uuid)
            time.sleep(.45)
            active = self.rpc.call('GetCurrentProgramScene')
            if active['sceneUuid'] != uuid:
                raise AssertionError(f'Failed to activate native scene {name}: {active}')
            value['activeProgramSceneVerified'] = True
            value['items'] = []
            for item in self.rpc.call('GetSceneItemList', sceneUuid=uuid)['sceneItems']:
                entry = dict(item)
                args = {'sceneUuid': uuid, 'sceneItemId': item['sceneItemId']}
                entry.update(self.rpc.call('GetSceneItemSource', **args))
                entry.update(self.rpc.call('GetSceneItemTransform', **args))
                entry.update(self.rpc.call('GetSceneItemEnabled', **args))
                entry.update(self.rpc.call('GetSceneItemLocked', **args))
                value['items'].append(entry)
            screenshot = self.rpc.call('GetSourceScreenshot', sourceUuid=uuid, imageFormat='png',
                imageWidth=1280, imageHeight=720)['imageData']
            png = base64.b64decode(screenshot.partition(',')[2], validate=True)
            if not png.startswith(PNG_MAGIC):
                raise AssertionError('OBS returned an invalid native preview PNG')
            relative = f'previews/{name}.png'
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png)
            value['screenshot'] = f'{label}/{relative}'
            self.desktop(f'{label}-{name}-native-preview')
            result['scenes'].append(value)
        write_json(self.evidence / f'{label}.json', result)
        progress('observation-complete', label=label, scenes=len(result['scenes']), inputs=len(result['inputs']))
        return result

    def export_saved(self, target):
        # Only called after a graceful native close. This is OBS's own serializer.
        if self.proc and self.proc.poll() is None:
            raise AssertionError('Export requires graceful native close first')
        active = None
        for line in (self.config / 'user.ini').read_text().splitlines():
            if line.startswith('SceneCollection='):
                active = line.partition('=')[2]
        collections = [p for p in self.scenes_dir.glob('*.json') if json.loads(p.read_text()).get('name') == active]
        if len(collections) != 1:
            raise AssertionError(f'Cannot identify native-saved active collection: {active}')
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(collections[0], target)
        return json.loads(target.read_text())

    def stop(self):
        if not self.proc or self.proc.poll() is not None:
            return
        progress('obs-close-start', label=self.label, launch=self.launch_count)
        self.assert_outputs_off()
        self.rpc.close()
        self.rpc = None
        main = self.wait_window('^OBS ')
        self.focus(main)
        self.cmd('xdotool', 'key', '--clearmodifiers', 'alt+f')
        self.cmd('xdotool', 'key', 'x')
        try:
            self.proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            self.desktop(f'{self.label}-close-failure')
            raise RuntimeError('OBS failed to close gracefully; refusing to count an unsaved roundtrip')
        self.log_handle.close()
        if self.proc.returncode != 0:
            raise RuntimeError(f'OBS exited nonzero: {self.proc.returncode}')
        diagnostics = inspect_log(self.process_log.read_text(errors='replace'))
        write_json(self.evidence / f'{self.label}-{self.launch_count}-diagnostics.json', diagnostics)
        progress('obs-closed', label=self.label, launch=self.launch_count, semanticFailures=len(diagnostics['semanticFailures']))
        if diagnostics['semanticFailures']:
            raise AssertionError(f'Native source/load diagnostics: {diagnostics["semanticFailures"]}')

    def cleanup(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        # Only copy the consumer logs. Ephemeral websocket credentials/config are
        # deleted and never included in published artifacts.
        logs = self.config / 'logs'
        if logs.exists():
            dest = self.evidence / f'{self.label}-obs-logs'
            dest.mkdir(exist_ok=True)
            for log in logs.glob('*.txt'):
                text = log.read_text(errors='replace').replace(self.password, '[redacted]')
                (dest / log.name).write_text(text)
        self.temp.cleanup()


@contextlib.contextmanager
def obs_session(evidence, label):
    app = NativeOBS(evidence, label)
    try:
        app.start()
        yield app
    except BaseException as exc:
        progress('gate-failure', label=label, errorType=type(exc).__name__, error=str(exc))
        try:
            app.desktop(f'{label}-exception', timeout=5)
        except Exception as screenshot_error:
            progress('failure-screenshot-unavailable', label=label, error=str(screenshot_error))
        raise
    finally:
        app.cleanup()


def set_item(app, scene, item_id, x, y, visible=True):
    app.rpc.call('SetSceneItemTransform', sceneName=scene, sceneItemId=item_id,
        sceneItemTransform={'positionX': x, 'positionY': y, 'scaleX': 1, 'scaleY': 1,
            'rotation': 0, 'alignment': 5, 'boundsType': 'OBS_BOUNDS_NONE', 'boundsAlignment': 0,
            'cropLeft': 0, 'cropTop': 0, 'cropRight': 0, 'cropBottom': 0, 'cropToBounds': False})
    # OBS creates zero-sized NONE bounds, but websocket rejects explicitly setting
    # a bounds dimension below 1. Preserve and verify its native zero default.
    actual = app.rpc.call('GetSceneItemTransform', sceneName=scene, sceneItemId=item_id)['sceneItemTransform']
    if actual['boundsWidth'] != 0 or actual['boundsHeight'] != 0:
        raise AssertionError(f'Unexpected native NONE bounds: {actual}')
    app.rpc.call('SetSceneItemEnabled', sceneName=scene, sceneItemId=item_id, sceneItemEnabled=visible)
    app.rpc.call('SetSceneItemLocked', sceneName=scene, sceneItemId=item_id, sceneItemLocked=False)


def kind(app, name):
    kinds = app.rpc.call('GetInputKindList')['inputKinds']
    matches = [k for k in kinds if k == name or re.fullmatch(re.escape(name) + r'_v\d+', k)]
    if not matches:
        raise AssertionError(f'Official OBS package lacks source {name}: {kinds}')
    return sorted(matches, key=lambda k: int(k.rsplit('_v', 1)[1]) if '_v' in k else 1)[-1]


def add_item(app, scene, source, item_id, x=0, y=0, settings=None, input_kind=None):
    if input_kind:
        created = app.rpc.call('CreateInput', sceneName=scene, inputName=source,
            inputKind=kind(app, input_kind), inputSettings=settings, sceneItemEnabled=True)
    else:
        created = app.rpc.call('CreateSceneItem', sceneName=scene, sourceName=source, sceneItemEnabled=True)
    if created['sceneItemId'] != item_id:
        raise AssertionError(f'Native item ID mismatch for {scene}/{source}: {created}')
    set_item(app, scene, item_id, x, y)


def baseline(app):
    for scene in ('Main', 'Break', 'LowerThird'):
        app.rpc.call('CreateScene', sceneName=scene)
    app.rpc.call('SetCurrentProgramScene', sceneName='Main')
    app.rpc.call('RemoveScene', sceneName='Bootstrap')
    app.rpc.call('SetVideoSettings', baseWidth=1280, baseHeight=720, outputWidth=1280,
                 outputHeight=720, fpsNumerator=30, fpsDenominator=1)
    add_item(app, 'LowerThird', 'Banner', 1, settings={'color': 4291669810, 'width': 650, 'height': 110}, input_kind='color_source')
    text_settings = {'text': 'Workshop begins at 18:00', 'font': {'face': 'DejaVu Sans', 'style': 'Book', 'size': 36, 'flags': 0},
                     'color1': 4294967295, 'color2': 4294967295, 'outline': False, 'drop_shadow': False, 'from_file': False}
    add_item(app, 'LowerThird', 'Title', 2, 24, 30, text_settings, 'text_ft2_source')
    add_item(app, 'Main', 'Background', 1, settings={'color': 4278190080, 'width': 1280, 'height': 720}, input_kind='color_source')
    add_item(app, 'Main', 'LowerThird', 2, 100, 100)
    add_item(app, 'Break', 'Background', 1)
    add_item(app, 'Break', 'LowerThird', 2, 20, 20)
    return app.source_identities()


def branch_edits(app, variant):
    if variant == 'operator':
        set_item(app, 'Main', 2, 240, 80)
        set_item(app, 'Break', 2, 20, 20, False)
        app.rpc.call('SetInputSettings', inputName='Background', inputSettings={'color': 4281541135}, overlay=True)
    elif variant == 'incoming':
        app.rpc.call('SetInputSettings', inputName='Title', inputSettings={'text': 'Workshop begins at 18:30'}, overlay=True)
        set_item(app, 'Break', 2, 40, 30)
        app.rpc.call('CreateScene', sceneName='Thanks')
        add_item(app, 'Thanks', 'LowerThird', 1, 100, 100)
        add_item(app, 'Thanks', 'ThanksText', 2, 100, 280, {'text': 'Thanks for joining',
            'font': {'face': 'DejaVu Sans', 'style': 'Book', 'size': 40, 'flags': 0},
            'color1': 4294967295, 'color2': 4294967295, 'outline': False, 'drop_shadow': False, 'from_file': False}, 'text_ft2_source')
    elif variant == 'incoming-conflict':
        set_item(app, 'Main', 2, 120, 140)
    else:
        raise ValueError(variant)


def prepare(args):
    out, fixtures = Path(args.out).resolve(), Path(args.fixtures).resolve()
    out.mkdir(parents=True, exist_ok=True)
    fixtures.mkdir(parents=True, exist_ok=True)
    with obs_session(out, 'baseline') as app:
        identities = {'baseline': baseline(app)}
        app.observe('baseline-created')
        app.stop()
        app.start()
        app.observe('baseline-reopened')
        if app.source_identities() != identities['baseline']:
            raise AssertionError('Native baseline UUIDs changed on reopening')
        app.stop()
        app.export_saved(fixtures / 'baseline.json')
    for variant in ('operator', 'incoming', 'incoming-conflict'):
        # Preparation is deliberately only a collection-name change. Product
        # preparation will be exercised separately with the actual browser file.
        source = fixtures / ('incoming.json' if variant == 'incoming-conflict' else 'baseline.json')
        prepared = json.loads(source.read_text())
        prepared['name'] = 'SceneReconcile-' + variant
        prepared_path = out / ('prepared-' + variant + '.json')
        write_json(prepared_path, prepared)
        with obs_session(out, variant) as app:
            app.import_collection(prepared_path, variant)
            app.observe(f'{variant}-imported')
            branch_edits(app, variant)
            app.observe(f'{variant}-edited')
            variant_ids = app.source_identities()
            for name, uuid in identities['baseline'].items():
                if variant_ids.get(name) != uuid:
                    raise AssertionError(f'Branch changed baseline UUID {name}')
            app.stop()
            app.start()
            app.observe(f'{variant}-reopened')
            if app.source_identities() != variant_ids:
                raise AssertionError('Branch UUIDs changed on native reopen')
            app.stop()
            app.export_saved(fixtures / f'{variant}.json')
            if variant == 'incoming':
                identities['incoming'] = variant_ids
    write_json(out / 'identities.json', identities)
    write_json(fixtures / 'identities.json', identities)
    write_json(out / 'prepare-result.json', {'status': 'passed', 'obsVersion': OBS_VERSION,
        'nativeUiImport': True, 'baselineCreatedViaNativeApi': True, 'allBranchesSavedAndReopened': True,
        'fixtures': {p.name: digest(p) for p in fixtures.glob('*.json')}})


def consume(args):
    out = Path(args.out).resolve()
    source = Path(args.input).resolve()
    input_hash = digest(source)
    with obs_session(out, 'consumer') as app:
        app.import_collection(source, 'consumer')
        app.observe('first-load')
        app.stop()
        app.export_saved(out / 'native-saved-first.json')
        app.start()
        app.observe('reopened')
        app.stop()
        app.export_saved(out / 'native-saved.json')
    if digest(source) != input_hash:
        raise AssertionError('Browser-downloaded input changed during native verification')
    write_json(out / 'consumer-result.json', {'status': 'runtime-observed', 'obsVersion': OBS_VERSION,
        'inputSha256': input_hash, 'nativeUiImport': True, 'savedAndReopened': True,
        'semanticValidation': 'separate independent oracle required; no semantic pass asserted here'})


def prepared(args):
    """Verify a real application-prepared download without modifying fixtures."""
    source = Path(args.input).resolve()
    original_path = Path(args.original).resolve()
    reference_path = Path(args.reference_observation).resolve()
    downloaded = check_fixture_file(source)
    original = check_fixture_file(original_path)
    name = downloaded.pop('name')
    original_name = original.pop('name')
    if downloaded != original:
        raise AssertionError('Prepared download changed native data beyond the collection name')
    if not name or name == original_name:
        raise AssertionError('Prepared working-copy collection requires a distinct name')
    reference = runtime_semantics(json.loads(reference_path.read_text()))
    out = Path(args.out).resolve()
    input_hash = digest(source)
    with obs_session(out, 'prepared') as app:
        app.import_collection(source, 'prepared')
        first = app.observe('first-load')
        if runtime_semantics(first) != reference:
            raise AssertionError('Prepared native first-load semantics differ from original native fixture')
        app.stop()
        app.export_saved(out / 'native-saved-first.json')
        app.start()
        reopened = app.observe('reopened')
        if runtime_semantics(reopened) != reference:
            raise AssertionError('Prepared native reopened semantics differ from original native fixture')
        app.stop()
        app.export_saved(out / 'native-saved.json')
    if digest(source) != input_hash:
        raise AssertionError('Prepared input changed during native verification')
    write_json(out / 'prepared-result.json', {'status': 'passed', 'obsVersion': OBS_VERSION,
        'inputSha256': input_hash, 'originalSha256': digest(original_path),
        'referenceObservationSha256': digest(reference_path), 'onlyCollectionNameChanged': True,
        'nativeUiImport': True, 'savedAndReopened': True, 'nativeRuntimeUnchanged': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--out', default='evidence/native-prepare')
    p.add_argument('--fixtures', default='tests/fixtures/native')
    p = commands.add_parser('consume')
    p.add_argument('--out', default='evidence/native-consumer')
    p.add_argument('--input', required=True)
    p = commands.add_parser('prepared')
    p.add_argument('--out', required=True)
    p.add_argument('--input', required=True)
    p.add_argument('--original', required=True)
    p.add_argument('--reference-observation', required=True)
    args = parser.parse_args()
    check_ci()
    {'prepare': prepare, 'consume': consume, 'prepared': prepared}[args.command](args)


if __name__ == '__main__':
    main()
