"""
Append-only event store for the baseball scorebook engine.

The EventStore is the single source of truth for a game.  All state is derived
by replaying the events it holds; nothing is ever mutated in place.

Key design decisions
--------------------
- ``append`` is the only way to add events.  The redo stack is cleared on every
  append so that a new action always discards the undone branch.
- ``undo`` / ``redo`` move events between the primary list and a redo stack.
  Neither operation touches external state — callers are responsible for
  rebuilding derived state from ``effective_events`` after each operation.
- ``effective_events`` applies ``EditEvent`` corrections before returning the
  sequence.  The raw append log (``events``) is never rewritten, preserving a
  full audit trail.
"""

from __future__ import annotations

from baseball_scorebook.models.events import EditEvent, GameEvent


class EventStore:
    """Append-only event store with undo/redo and EditEvent correction support.

    The store owns two internal lists:

    ``_events``
        The primary, append-only log.  ``undo`` pops from this list and
        ``redo`` appends back to it.

    ``_redo_stack``
        Holds events removed by ``undo`` so they can be re-appended by
        ``redo``.  The stack is cleared whenever a new event is appended
        so that it only ever contains a single linear branch of undone
        events.

    Consumers that need the "logical" event sequence — with corrections
    applied and ``EditEvent`` entries removed — should call
    ``effective_events`` rather than reading ``events`` directly.
    """

    def __init__(self) -> None:
        self._events: list[GameEvent] = []
        self._redo_stack: list[GameEvent] = []

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def events(self) -> tuple[GameEvent, ...]:
        """All events in append order as an immutable tuple.

        This is the raw audit log.  It includes ``EditEvent`` records and
        every event that has been superseded by a later correction.  Use
        ``effective_events`` when replaying game state.
        """
        return tuple(self._events)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(self, event: GameEvent) -> None:
        """Append *event* to the log and clear the redo stack.

        Clearing the redo stack on every append ensures that the undone
        branch is discarded once a new action is taken, matching the
        standard undo/redo contract.

        Args:
            event: Any ``GameEvent`` subclass instance to record.
        """
        self._events.append(event)
        self._redo_stack.clear()

    def undo(self) -> GameEvent | None:
        """Remove and return the last event, pushing it onto the redo stack.

        Returns:
            The event that was removed, or ``None`` if the log is empty.
        """
        if not self._events:
            return None
        event = self._events.pop()
        self._redo_stack.append(event)
        return event

    def redo(self) -> GameEvent | None:
        """Re-append the last undone event from the redo stack.

        Returns:
            The event that was re-appended, or ``None`` if the redo stack
            is empty.
        """
        if not self._redo_stack:
            return None
        event = self._redo_stack.pop()
        self._events.append(event)
        return event

    def clear(self) -> None:
        """Clear all events and the redo stack, resetting the store to empty."""
        self._events.clear()
        self._redo_stack.clear()

    # ------------------------------------------------------------------
    # Effective event sequence
    # ------------------------------------------------------------------

    def effective_events(self) -> tuple[GameEvent, ...]:
        """Return the event list with ``EditEvent`` corrections applied.

        The algorithm makes a single pass to build a correction map and a
        second pass to emit the effective sequence:

        1. Scan ``_events`` for every ``EditEvent`` and record the mapping
           ``target_event_id -> corrected_event``.  When multiple
           ``EditEvent`` entries target the same ``event_id``, the last
           one wins.

        2. Walk ``_events`` again, skipping ``EditEvent`` records entirely.
           For any event whose ``event_id`` appears in the correction map,
           emit the corrected replacement instead of the original.

        The original events are never modified; the raw log remains intact.

        Returns:
            An immutable tuple of ``GameEvent`` instances representing the
            logical game state ready for replay by the state engine.
        """
        corrections: dict[str, GameEvent] = {}
        for event in self._events:
            if isinstance(event, EditEvent):
                corrections[event.target_event_id] = event.corrected_event

        result: list[GameEvent] = []
        for event in self._events:
            if isinstance(event, EditEvent):
                continue
            corrected = corrections.get(event.event_id)
            result.append(corrected if corrected is not None else event)

        return tuple(result)

    # ------------------------------------------------------------------
    # Sequence protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Return the number of events in the primary log."""
        return len(self._events)

    def __bool__(self) -> bool:
        """Return ``True`` when the primary log contains at least one event."""
        return bool(self._events)
