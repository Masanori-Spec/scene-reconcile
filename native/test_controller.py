"""Lightweight controller checks. These do not install/start/prove OBS."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import obs_gate as gate


class ControllerTests(unittest.TestCase):
    def test_non_ci_is_refused_before_any_native_action(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'CI-only'):
                gate.check_ci()

    def test_official_duplicate_uuid_diagnostic_is_fatal(self):
        line = '20:00:00: Attempted to insert context with duplicate UUID "abc"!'
        self.assertEqual(gate.inspect_log(line)['semanticFailures'], [line])

    def test_missing_scene_reference_and_source_type_are_fatal(self):
        lines = ["[scene_load_item] Source Title not found!", "Source ID 'typo' not found", "Failed to create source 'Title'!"]
        self.assertEqual(gate.inspect_log('\n'.join(lines))['semanticFailures'], lines)

    def test_optional_hardware_failure_is_explicit_not_source_suppression(self):
        line = "Failed to initialize module 'aja.so'"
        report = gate.inspect_log(line + "\nFailed to create source 'Title'!")
        self.assertEqual(report['toleratedEnvironmentDiagnostics'], [line])
        self.assertEqual(report['semanticFailures'], ["Failed to create source 'Title'!"])

    def test_unknown_warning_is_kept_for_review(self):
        line = 'warning: unexpected future diagnostic'
        self.assertEqual(gate.inspect_log(line)['otherDiagnosticsForReview'], [line])

    def test_fixture_preflight_rejects_device_source_and_versioned_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            value = {'sources': [{'name': 'Title', 'id': 'text_ft2_source', 'versioned_id': 'text_ft2_source_v2'}]}
            path.write_text(json.dumps(value))
            self.assertEqual(gate.check_fixture_file(path), value)
            value['sources'][0]['versioned_id'] = 'v4l2_input'
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(AssertionError, 'source kind'):
                gate.check_fixture_file(path)
            value['sources'][0]['id'] = 'v4l2_input'
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(AssertionError, 'source kind'):
                gate.check_fixture_file(path)

    def test_fixture_preflight_rejects_scripts_audio_and_file_text(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            samples = [
                {'sources': [], 'modules': {'scripts-tool': [{'path': 'bad.lua'}]}},
                {'sources': [], 'DesktopAudioDevice1': {}},
                {'sources': [{'id': 'text_ft2_source', 'name': 'Title', 'settings': {'from_file': True}}]},
            ]
            for value in samples:
                path.write_text(json.dumps(value))
                with self.assertRaises(AssertionError):
                    gate.check_fixture_file(path)

    def test_runtime_comparison_ignores_ui_state_but_not_semantics(self):
        base = {'phase': 'a', 'sceneCollection': {'currentSceneCollectionName': 'a'}, 'video': {'baseWidth': 1280},
                'inputs': [{'inputUuid': 't', 'settings': {'text': 'Hello'}}],
                'scenes': [{'sceneName': 'Main', 'sceneUuid': 'm', 'screenshot': 'a.png',
                            'items': [{'sceneItemIndex': 0, 'sourceUuid': 't'}]}]}
        other = copy.deepcopy(base)
        other['phase'] = 'b'
        other['sceneCollection']['currentSceneCollectionName'] = 'b'
        other['scenes'][0]['screenshot'] = 'b.png'
        self.assertEqual(gate.runtime_semantics(base), gate.runtime_semantics(other))
        other['inputs'][0]['settings']['text'] = 'Changed'
        self.assertNotEqual(gate.runtime_semantics(base), gate.runtime_semantics(other))

    def test_window_search_requires_both_pid_and_title(self):
        from types import SimpleNamespace
        app = gate.NativeOBS.__new__(gate.NativeOBS)
        app.proc = SimpleNamespace(pid=123)
        app.env = {}
        with patch.object(gate.subprocess, 'run', return_value=SimpleNamespace(stdout='99\n')) as run:
            self.assertEqual(app.windows('^Import Scene Collection$'), ['99'])
            self.assertIn('--all', run.call_args.args[0])

    def test_identify_is_not_treated_as_obs_readiness(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as folder:
            app = gate.NativeOBS(folder, 'unit-test')
            proc = MagicMock()
            proc.poll.return_value = None
            first = MagicMock()
            first.call.side_effect = RuntimeError('NotReady')
            second = MagicMock()
            def ready(method, **kwargs):
                if method == 'GetVersion': return {'obsVersion': gate.OBS_VERSION}
                if method == 'GetSpecialInputs': return {'mic1': None, 'desktop1': None}
                return {'outputActive': False}
            second.call.side_effect = ready
            with patch.object(gate.subprocess, 'Popen', return_value=proc), \
                 patch.object(gate, 'RPC', side_effect=[first, second]) as rpc, \
                 patch.object(gate.time, 'sleep'), patch.object(app, 'desktop'):
                app.start()
                self.assertEqual(rpc.call_count, 2)
                first.close.assert_called_once()
                self.assertIs(app.rpc, second)
            app.log_handle.close()
            proc.poll.return_value = 0
            app.cleanup()

    def test_external_commands_always_have_a_timeout(self):
        from types import SimpleNamespace
        app = gate.NativeOBS.__new__(gate.NativeOBS)
        app.env = {}
        with patch.object(gate.subprocess, 'run', return_value=SimpleNamespace(stdout='ok')) as run, patch.object(gate, 'progress'):
            self.assertEqual(app.cmd('xdotool', 'windowactivate', '--sync', '99'), 'ok')
            self.assertEqual(run.call_args.kwargs['timeout'], 10)
            app.cmd('tesseract', 'input.png', 'stdout', timeout=3)
            self.assertEqual(run.call_args.kwargs['timeout'], 3)
        with patch.object(gate.subprocess, 'run', side_effect=gate.subprocess.TimeoutExpired('xdotool', 10)), patch.object(gate, 'progress'):
            with self.assertRaises(gate.subprocess.TimeoutExpired):
                app.cmd('xdotool', 'windowactivate', '--sync', '99')

    def test_failure_screenshot_does_not_replace_original_error(self):
        from unittest.mock import MagicMock
        app = MagicMock()
        app.start.side_effect = ValueError('original native failure')
        app.desktop.side_effect = RuntimeError('screenshot timeout')
        with patch.object(gate, 'NativeOBS', return_value=app), patch.object(gate, 'progress'):
            with self.assertRaisesRegex(ValueError, 'original native failure'):
                with gate.obs_session('unused', 'test'):
                    self.fail('Session must not yield after failed startup')
        app.cleanup.assert_called_once()
        app.desktop.assert_called_once_with('test-exception', timeout=5)

    def test_native_menu_hover_and_activation_are_separate(self):
        app = gate.NativeOBS.__new__(gate.NativeOBS)
        calls = []
        tsv = 'text\tconf\tleft\ttop\twidth\theight\nImport...\t95\t416\t176\t50\t14\n'
        def command(*args, **kwargs):
            calls.append(args)
            return tsv if args[0] == 'tesseract' else ''
        with patch.object(app, 'cmd', side_effect=command), \
             patch.object(app, 'desktop', return_value=Path('observed.png')) as screenshot, \
             patch.object(gate.time, 'sleep', side_effect=lambda seconds: calls.append(('settle', seconds))), patch.object(gate, 'progress'):
            app.click_text('Import', 'collection-menu', activation='return')
        self.assertIn(('xdotool', 'mousemove', '--sync', '441', '183'), calls)
        self.assertIn(('xdotool', 'key', '--clearmodifiers', 'Return'), calls)
        self.assertFalse(any('click' in call for call in calls))
        self.assertLess(calls.index(('xdotool', 'mousemove', '--sync', '441', '183')), calls.index(('settle', .3)))
        self.assertLess(calls.index(('settle', .3)), calls.index(('xdotool', 'key', '--clearmodifiers', 'Return')))
        screenshot.assert_any_call('collection-menu-target-hover')

    def test_graceful_stop_observes_file_then_exit_before_waiting(self):
        from unittest.mock import MagicMock, call
        with tempfile.TemporaryDirectory() as folder:
            app = gate.NativeOBS.__new__(gate.NativeOBS)
            app.label, app.launch_count = 'consumer', 1
            app.evidence = Path(folder)
            app.process_log = Path(folder) / 'process.log'
            app.process_log.write_text('info: clean shutdown\n')
            app.log_handle = MagicMock()
            app.proc = MagicMock()
            app.proc.poll.return_value = None
            app.proc.returncode = 0
            app.rpc = MagicMock()
            with patch.object(app, 'assert_outputs_off'), patch.object(app, 'wait_window', return_value='99'), \
                 patch.object(app, 'focus'), patch.object(app, 'click_text') as activate, patch.object(gate, 'progress'):
                app.stop()
            self.assertEqual(activate.call_args_list, [
                call('File', 'consumer-1-file-menubar'),
                call('Exit', 'consumer-1-exit-menu', activation='return')])
            app.proc.wait.assert_called_once_with(timeout=25)
            app.proc.terminate.assert_not_called()
            app.proc.kill.assert_not_called()
            self.assertTrue((Path(folder) / 'consumer-1-diagnostics.json').is_file())

    def test_graceful_stop_timeout_remains_failure_without_force_success(self):
        from unittest.mock import MagicMock
        app = gate.NativeOBS.__new__(gate.NativeOBS)
        app.label, app.launch_count = 'consumer', 1
        app.proc = MagicMock()
        app.proc.poll.return_value = None
        app.proc.wait.side_effect = gate.subprocess.TimeoutExpired('obs', 25)
        app.rpc = MagicMock()
        with patch.object(app, 'assert_outputs_off'), patch.object(app, 'wait_window', return_value='99'), \
             patch.object(app, 'focus'), patch.object(app, 'click_text'), patch.object(app, 'desktop') as screenshot, \
             patch.object(gate, 'progress'):
            with self.assertRaisesRegex(RuntimeError, 'refusing to count an unsaved roundtrip'):
                app.stop()
        app.proc.terminate.assert_not_called()
        app.proc.kill.assert_not_called()
        screenshot.assert_called_once_with('consumer-close-failure')

    def test_zero_bounds_are_observed_instead_of_invalid_setter(self):
        class FakeRPC:
            def __init__(self):
                self.calls = []
            def call(self, method, **kwargs):
                self.calls.append((method, kwargs))
                if method == 'GetSceneItemTransform':
                    return {'sceneItemTransform': {'boundsWidth': 0, 'boundsHeight': 0}}
                return {}
        class FakeApp:
            rpc = FakeRPC()
        app = FakeApp()
        gate.set_item(app, 'Main', 2, 240, 80)
        transform = app.rpc.calls[0][1]['sceneItemTransform']
        self.assertNotIn('boundsWidth', transform)
        self.assertNotIn('boundsHeight', transform)
        self.assertEqual(transform['alignment'], 5)
        self.assertEqual(transform['boundsAlignment'], 0)


if __name__ == '__main__':
    unittest.main()
