import os
import unittest
from unittest.mock import patch

from modules.config_manager import ConfigManager
from modules.ui_controller import UIController


class TestUIToolLaunchPaths(unittest.TestCase):
    def setUp(self):
        cm = ConfigManager()
        self.ui = UIController(cm.get_interface_settings(), cm)

    def tearDown(self):
        self.ui.cleanup()

    @patch('subprocess.Popen')
    def test_open_xbox_debugger_path(self, mock_popen):
        self.ui.open_xbox_debugger()
        self.assertTrue(mock_popen.called)
        args = mock_popen.call_args[0][0]
        # First element is 'python', second is the path
        self.assertTrue(args[0].lower().endswith('python'))
        self.assertTrue(args[1].replace('/', '\\').endswith(os.path.join('tools', 'utilities', 'xbox_debugger.py')))

    @patch('subprocess.Popen')
    def test_open_controller_visualizer_path(self, mock_popen):
        self.ui.open_controller_visualizer()
        self.assertTrue(mock_popen.called)
        args = mock_popen.call_args[0][0]
        self.assertTrue(
            args[1].replace('/', '\\').endswith(os.path.join('tools', 'visualizers', 'controller_visualizer.py')))

    @patch('subprocess.Popen')
    def test_open_controller_mapping_editor_path(self, mock_popen):
        self.ui.open_controller_mapping_editor()
        self.assertTrue(mock_popen.called)
        args = mock_popen.call_args[0][0]
        self.assertTrue(args[1].replace('/', '\\').endswith(
            os.path.join('tools', 'config_editors', 'controller_mapping_editor.py')))


if __name__ == '__main__':
    unittest.main()
