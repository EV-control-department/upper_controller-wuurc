"""
测试控制器映射编辑器
用于验证controller_mapping_editor.py中的修改是否正确
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入PyQt5
from PyQt5.QtWidgets import QApplication

# 创建QApplication实例
app = QApplication(sys.argv)

# 导入需要测试的模块
from tools.config_editors.controller_mapping_editor import ControllerMappingEditor


class TestControllerMappingEditor(unittest.TestCase):
    """测试控制器映射编辑器类"""

    @patch('pygame.joystick.get_count', return_value=0)
    @patch('tools.config_editors.controller_mapping_editor.ConfigManager')
    def test_joystick_correction_button_added(self, mock_config_manager, mock_get_count):
        """测试是否正确添加了手柄辅助修正按钮"""
        # 创建模拟的配置管理器
        mock_config = MagicMock()
        mock_config_manager.return_value = mock_config

        # 创建编辑器实例
        editor = ControllerMappingEditor()

        # 手动调用创建按钮映射组件方法
        editor.create_button_mapping_widgets()

        # 验证是否创建了toggle_joystick_correction_key按钮
        self.assertIn("toggle_joystick_correction_key", editor.button_widgets)

        # 验证按钮的属性
        button_widget = editor.button_widgets["toggle_joystick_correction_key"]
        self.assertEqual(button_widget.section, "keyboard_bindings")
        self.assertEqual(button_widget.key, "toggle_joystick_correction_key")
        self.assertEqual(button_widget.description, "手柄辅助修正切换")


if __name__ == "__main__":
    print("测试控制器映射编辑器...")
    unittest.main()
