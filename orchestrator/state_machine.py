"""State Machine: 6-state pipeline with transition logic.

States: INTAKE → EXTRACTION → COB_REASONING → DOCUMENT_GENERATION → VALIDATION → COMPLETE
The Validation state can loop back to any prior state via the Critic agent.
"""
import logging
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger("duco_agent.state_machine")


class State(Enum):
    """Pipeline states for the DuCO-Agent."""
    INTAKE = auto()
    EXTRACTION = auto()
    COB_REASONING = auto()
    DOCUMENT_GENERATION = auto()
    VALIDATION = auto()
    COMPLETE = auto()


class TransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


# Valid transitions
VALID_TRANSITIONS = {
    State.INTAKE: [State.EXTRACTION],
    State.EXTRACTION: [State.COB_REASONING],
    State.COB_REASONING: [State.DOCUMENT_GENERATION],
    State.DOCUMENT_GENERATION: [State.VALIDATION],
    State.VALIDATION: [
        State.COMPLETE,
        # Validation can loop back to any state for corrections
        State.EXTRACTION,
        State.COB_REASONING,
        State.DOCUMENT_GENERATION,
    ],
    State.COMPLETE: [],
}


class StateMachine:
    """6-state pipeline manager with validation loop-back."""

    def __init__(self):
        self._state = State.INTAKE
        self._history: list[tuple[State, State]] = []
        self._loop_count = 0
        self._max_loops = 3  # Prevent infinite loops

    @property
    def current_state(self) -> State:
        """Get the current state."""
        return self._state

    @property
    def is_complete(self) -> bool:
        """Check if pipeline has completed."""
        return self._state == State.COMPLETE

    @property
    def transition_history(self) -> list[tuple[State, State]]:
        """Get the transition history."""
        return self._history.copy()

    def transition_to(self, new_state: State) -> None:
        """Transition to a new state.

        Validates the transition is allowed before executing.
        Tracks loop-backs from VALIDATION to prevent infinite loops.
        """
        if new_state not in VALID_TRANSITIONS.get(self._state, []):
            raise TransitionError(
                f"Invalid transition: {self._state.name} → {new_state.name}. "
                f"Valid targets: {[s.name for s in VALID_TRANSITIONS[self._state]]}"
            )

        # Track validation loop-backs
        if self._state == State.VALIDATION and new_state != State.COMPLETE:
            self._loop_count += 1
            if self._loop_count > self._max_loops:
                logger.warning(
                    f"Max validation loops ({self._max_loops}) reached. "
                    f"Forcing transition to COMPLETE."
                )
                new_state = State.COMPLETE

        old_state = self._state
        self._state = new_state
        self._history.append((old_state, new_state))
        logger.info(f"State transition: {old_state.name} → {new_state.name}")

    def advance(self) -> None:
        """Advance to the next state in the normal pipeline."""
        next_states = VALID_TRANSITIONS.get(self._state, [])
        if next_states:
            self.transition_to(next_states[0])
        else:
            raise TransitionError(f"Cannot advance from {self._state.name}")

    def loop_back(self, target: State) -> None:
        """Loop back from VALIDATION to a prior state for corrections."""
        if self._state != State.VALIDATION:
            raise TransitionError(
                f"Loop-back only allowed from VALIDATION, currently in {self._state.name}"
            )
        self.transition_to(target)

    def get_summary(self) -> dict:
        """Get a summary of the state machine's execution."""
        return {
            "current_state": self._state.name,
            "is_complete": self.is_complete,
            "total_transitions": len(self._history),
            "validation_loops": self._loop_count,
            "history": [(old.name, new.name) for old, new in self._history]
        }
