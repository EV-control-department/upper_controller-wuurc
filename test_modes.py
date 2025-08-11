from modules.config_manager import ConfigManager


def test_modes():
    cm = ConfigManager()
    modes = cm.get_catch_modes()
    print("Loaded modes:")
    for i, mode in enumerate(modes):
        print(f"Mode {i + 1}:")
        print(f"  Name: {mode['name']}")
        print(f"  ServoX: {mode['servoX']}")
        print(f"  ServoY: {mode['servoY']}")
        print(f"  Color: {mode['color']}")
        print()


if __name__ == "__main__":
    test_modes()
