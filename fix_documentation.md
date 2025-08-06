# Controller Mapping Editor Fix

## Issue Description

When running the controller_mapping_editor.py script, the following error occurred:

```
成功从 curve.json 加载电机参数
运行弹窗出错
```

This indicates that the script successfully loaded motor parameters from curve.json but encountered an error when trying
to run a popup window.

## Root Cause

The issue was related to the initialization order of pygame and PyQt5. In the original code:

1. The pygame library was initialized in the ControllerMappingEditor.__init__ method
2. The QApplication was created later in the main function

This order is problematic because both pygame and PyQt5 interact with the system's event loop and window management.
Initializing pygame before QApplication can cause conflicts that prevent popup windows from working correctly.

## Fix Applied

The fix involved changing the initialization order:

1. Removed pygame initialization from the ControllerMappingEditor.__init__ method
2. Moved pygame initialization to the main function, after creating QApplication but before creating the
   ControllerMappingEditor window

### Code Changes

From ControllerMappingEditor.__init__:

```python
# Removed:
# 初始化pygame
# pygame.init()
# pygame.joystick.init()
```

Added to main function:

```python
def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 初始化pygame
    pygame.init()
    pygame.joystick.init()

    window = ControllerMappingEditor()
    window.show()
    sys.exit(app.exec_())
```

## Expected Result

This change ensures that PyQt5's QApplication is initialized first, establishing its control over the application's
event loop, and then pygame is initialized afterward. This order should prevent conflicts between the two libraries and
fix the popup window error.

## Testing

To test this fix, run the controller_mapping_editor.py script again. The popup window should now work correctly without
errors.