import unittest
from unittest.mock import patch

from modules.hardware_controller import GimbalController


class TestGimbalController(unittest.TestCase):
    @patch("modules.hardware_controller.socket.socket")
    def test_a2_rotate_packet_matches_manual_example(self, socket_factory):
        controller = GimbalController(model="A2_MINI")
        # SIYI manual: rotate 100, 100.
        packet = controller.build_siyi_packet(0x07, bytes((0x64, 0x64)))
        self.assertEqual(packet.hex(" "), "55 66 01 02 00 00 00 07 64 64 3d cf")
        controller.stop()

    @patch("modules.hardware_controller.socket.socket")
    def test_a2_angle_uses_pitch_only_and_tenths_of_degree(self, socket_factory):
        controller = GimbalController(model="a2_mini")
        controller.send_pitch_angle(25)
        packet = socket_factory.return_value.sendto.call_args.args[0]
        self.assertEqual(packet[:8], bytes.fromhex("55 66 01 04 00 00 00 0e"))
        self.assertEqual(packet[8:12], bytes.fromhex("00 00 fa 00"))
        self.assertEqual(
            int.from_bytes(packet[-2:], "little"),
            controller.calculate_siyi_crc(packet[:-2]),
        )
        controller.stop()

    @patch("modules.hardware_controller.socket.socket")
    def test_yunzhuo_angle_packet_uses_gap(self, socket_factory):
        controller = GimbalController(model="yunzhuo")
        controller.send_pitch_angle(-50, 0.5)
        packet = socket_factory.return_value.sendto.call_args.args[0].decode("ascii")
        self.assertTrue(packet.startswith("#TPUG6wGAPEC7839"))
        self.assertEqual(packet[-2:], GimbalController.calculate_crc(packet[:-2]))
        controller.stop()


if __name__ == "__main__":
    unittest.main()
