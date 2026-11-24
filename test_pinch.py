import unittest
from unittest.mock import MagicMock, patch

from core.gestures.right_hand import RightHandProcessor
from core.tracker import Landmark


class PinchClickTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actuator = MagicMock()
        self._map_patch = patch(
            "core.gestures.right_hand.map_to_desktop",
            return_value=(0, 0),
        )
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)

        self.processor = RightHandProcessor(
            self.actuator,
            MagicMock(),
            MagicMock(),
        )

    def _process(self, pinching: bool) -> None:
        landmarks = [Landmark(0.5, 0.5, 0.0) for _ in range(21)]
        landmarks[4] = Landmark(0.4, 0.4, 0.0)
        landmarks[8] = Landmark(0.4 if pinching else 0.6, 0.4, 0.0)
        landmarks[12] = Landmark(0.8, 0.8, 0.0)
        self.processor.process(landmarks, (1280, 720))

    def test_clicks_after_five_frames_and_only_once_while_held(self) -> None:
        for _ in range(4):
            self._process(pinching=True)
        self.actuator.left_click.assert_not_called()

        self._process(pinching=True)
        self.actuator.left_click.assert_called_once_with()

        for _ in range(30):
            self._process(pinching=True)

        self.actuator.left_click.assert_called_once_with()
        self.actuator.drag_start.assert_not_called()
        self.actuator.drag_end.assert_not_called()

    def test_a_non_pinch_frame_resets_confirmation(self) -> None:
        for _ in range(4):
            self._process(pinching=True)

        self._process(pinching=False)
        for _ in range(4):
            self._process(pinching=True)
        self.actuator.left_click.assert_not_called()

        self._process(pinching=True)
        self.actuator.left_click.assert_called_once_with()

    def test_cooldown_suppresses_a_second_pinch(self) -> None:
        for _ in range(5):
            self._process(pinching=True)
        self.actuator.left_click.assert_called_once_with()

        for _ in range(3):
            self._process(pinching=False)
        for _ in range(5):
            self._process(pinching=True)
        self.actuator.left_click.assert_called_once_with()

        for _ in range(3):
            self._process(pinching=False)
        for _ in range(5):
            self._process(pinching=True)
        self.actuator.left_click.assert_called_once_with()

        for _ in range(3):
            self._process(pinching=False)
        self._process(pinching=False)
        for _ in range(5):
            self._process(pinching=True)
        self.assertEqual(self.actuator.left_click.call_count, 2)


if __name__ == "__main__":
    unittest.main()
