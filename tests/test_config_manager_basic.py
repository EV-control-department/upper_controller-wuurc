import os
import unittest

from modules.config_manager import ConfigManager


class TestConfigManagerBasic(unittest.TestCase):
    def setUp(self):
        # Ensure project root is current working dir (important for relative paths in ConfigManager)
        self.cwd = os.getcwd()
        # Instantiate normally; ConfigManager uses absolute joins internally
        self.cm = ConfigManager()

    def test_rtsp_url_composition(self):
        url = self.cm.get_rtsp_url()
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith("rtsp://"), f"RTSP URL should start with rtsp://, got: {url}")
        self.assertIn("@", url, "RTSP URL should contain credentials and host separator '@'")

    def test_camera_dimensions(self):
        w, h = self.cm.get_camera_dimensions()
        self.assertIsInstance(w, int)
        self.assertIsInstance(h, int)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_server_and_ports(self):
        host, remote = self.cm.get_server_address()
        local = self.cm.get_local_port()
        self.assertIsInstance(host, str)
        self.assertIsInstance(remote, int)
        self.assertIsInstance(local, int)
        self.assertGreater(remote, 0)
        self.assertGreater(local, 0)

    def test_keyboard_bindings_present(self):
        kb = self.cm.get_keyboard_bindings()
        required_keys = [
            'quit_key', 'xbox_debugger_key', 'toggle_rotation_key', 'toggle_undistorted_key',
            'toggle_fullscreen_key', 'capture_frame_key', 'controller_visualizer_key',
            'controller_mapping_key', 'deploy_thrust_curves_key', 'toggle_joystick_correction_key'
        ]
        for k in required_keys:
            self.assertIn(k, kb, f"Missing keyboard binding: {k}")

    def test_curve_json_loaded_or_default(self):
        # ConfigManager ensures motor_params set to loaded or default fallback with required keys
        mp = self.cm.motor_params
        self.assertIsInstance(mp, dict)
        self.assertGreaterEqual(len(mp), 1)
        required = ["np_mid", "np_ini", "pp_ini", "pp_mid", "nt_end", "nt_mid", "pt_mid", "pt_end"]
        # Check at least for m0
        first_key = sorted(mp.keys())[0]
        for rk in required:
            self.assertIn(rk, mp[first_key], f"Missing curve key {rk} in {first_key}")


if __name__ == '__main__':
    unittest.main()
