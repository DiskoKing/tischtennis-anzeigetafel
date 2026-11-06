import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


@unittest.skipUnless(os.name == 'nt', 'Windows platform adapter')
class WindowsLauncherTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('test_launcher', Path(__file__).parent/'platform/windows/launcher.py')
        self.launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.launcher)

    def test_background_browser_has_no_console(self):
        with patch.object(self.launcher.subprocess, 'Popen') as popen:
            self.launcher.launch_browser(['browser.exe'])
            self.assertEqual(popen.call_args.kwargs['creationflags'], self.launcher.subprocess.CREATE_NO_WINDOW)

    def test_fresh_profiles_do_not_restore_previous_windows(self):
        monitor = dict(left=-1920, top=0, width=1920, height=1080, primary=False)
        args = self.launcher.browser_args(Path('msedge.exe'), 'http://localhost', monitor)
        self.assertTrue(any('session-' in value for value in args if value.startswith('--user-data-dir=')))
        self.assertIn('--window-position=-1900,20', args)
        self.assertEqual(self.launcher.choose_monitor([dict(primary=True), monitor]), monitor)

    def test_first_start_opens_exactly_one_display_and_no_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            monitor = dict(left=0, top=0, width=1920, height=1080, primary=True)
            process = Mock()
            process.poll.return_value = 0
            with patch.object(self.launcher, 'BASE', base), patch.object(self.launcher, 'PRIVATE', base/'app/private'), patch.object(self.launcher, 'PROFILE_ROOT', base/'browser-data/session-test'), patch.object(self.launcher, 'monitors', return_value=[monitor]), patch.object(self.launcher, 'browser_path', return_value=Path('msedge.exe')), patch.object(self.launcher, 'place_window'), patch.object(self.launcher, 'launch_browser', return_value=process) as launch, patch.object(self.launcher.logging, 'basicConfig'):
                self.launcher.run(test_seconds=.01)
            launch.assert_called_once()
            self.assertTrue(any('/spiele.html' in arg for arg in launch.call_args.args[0]))
            self.assertFalse(any('/settings.html' in arg for arg in launch.call_args.args[0]))
            self.assertFalse((base/'app/private/portable-session.json').exists())

    def test_existing_settings_window_is_focused_without_second_launch(self):
        launcher = self.launcher
        process = Mock(pid=4321)
        process.poll.return_value = None
        user = Mock()
        def visit_windows(callback, data):
            callback(123, 0)
        def read_pid(hwnd, pointer):
            pointer._obj.value = 4321
        user.EnumWindows.side_effect = visit_windows
        user.GetWindowThreadProcessId.side_effect = read_pid
        user.IsWindowVisible.return_value = True
        with patch.object(launcher, 'USER', user), patch.object(launcher, 'launch_browser') as launch:
            result = launcher.settings_window(process, Path('msedge.exe'), 'http://localhost/settings.html', {})
        self.assertIs(result, process)
        launch.assert_not_called()
        user.SetForegroundWindow.assert_called_once_with(123)


if __name__ == '__main__':
    unittest.main()
