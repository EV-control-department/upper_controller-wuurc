import os
import time
import unittest

# Ensure pygame uses a dummy video driver to avoid opening a real window
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame  # noqa: E402

from modules.config_manager import ConfigManager  # noqa: E402
from modules.ui_controller import UIController  # noqa: E402


class TestUITemperatureLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize pygame once for dummy mode
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        cm = ConfigManager()
        settings = cm.get_interface_settings()
        # Create UIController with config (dummy driver ensures no real window)
        self.ui = UIController(settings, cm)

    def tearDown(self):
        self.ui.cleanup()

    def test_mode_always_returns_defaultish(self):
        self.ui.temp_fooling_mode = 'always'
        # Repeated calls should hover around default_temperature +/- jitter
        vals = []
        for _ in range(5):
            v, is_fake = self.ui.get_display_temperature(depth=1.0, temperature=25.0)
            vals.append(v)
            time.sleep(0.01)
            self.assertTrue(is_fake)
        avg = sum(vals) / len(vals)
        self.assertTrue(27.5 < avg < 29.1, f"unexpected average temp in always mode: {avg}")

    def test_mode_real_valid_and_invalid(self):
        self.ui.temp_fooling_mode = 'real'
        # Valid temperature should be reflected (first call sets directly)
        v1, fake1 = self.ui.get_display_temperature(depth=1.0, temperature=20.0)
        self.assertFalse(fake1)
        self.assertTrue(19.0 <= v1 <= 21.0, f"expected near 20C, got {v1}")
        # Invalid temperature should keep last display value (not fake)
        v2, fake2 = self.ui.get_display_temperature(depth=1.0, temperature=None)
        self.assertFalse(fake2)
        self.assertAlmostEqual(v2, self.ui._temp_display_value)


if __name__ == '__main__':
    unittest.main()
