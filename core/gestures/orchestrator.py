
# core/gestures/orchestrator.py

from core.tracker import HandsResult
from core.actuator import MouseActuator
from core.display import VirtualDesktop, TrackpadZone

from core.gestures.right_hand import RightHandProcessor
from core.gestures.left_hand import LeftHandProcessor
from core.gestures.two_hand import TwoHandProcessor


class GestureOrchestrator:
    """Coordinates gesture processors for both hands."""

    def __init__(
        self,
        actuator: MouseActuator,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
    ) -> None:

        self._right = RightHandProcessor(
            actuator,
            desktop,
            trackpad,
        )

        self._left = LeftHandProcessor(actuator)

        self._two = TwoHandProcessor(actuator)

    @property
    def right_state(self) -> str:
        """Returns the current right-hand gesture state."""
        return self._right._state.name

    def process(
        self,
        hands: HandsResult,
        frame_size: tuple[int, int] | None = None,
    ) -> None:
        """Process one frame. frame_size = (width, height)."""

        self._right.process(
            hands.right,
            frame_size,
        )

        self._left.process(hands.left)

        if hands.left is not None and hands.right is not None:
            self._two.process(
                hands.left,
                hands.right,
            )
