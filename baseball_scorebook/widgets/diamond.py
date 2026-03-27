"""Diamond widget — renders a per-at-bat baseball diamond using Rich text."""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from baseball_scorebook.models.at_bat import DiamondState
from baseball_scorebook.models.constants import BaseCode, RunnerFinalState, SegmentState

# Segment keys: (from_base, to_base) that form each leg of the diamond path.
_SEG_HOME_FIRST = (BaseCode.HOME, BaseCode.FIRST)
_SEG_FIRST_SECOND = (BaseCode.FIRST, BaseCode.SECOND)
_SEG_SECOND_THIRD = (BaseCode.SECOND, BaseCode.THIRD)
_SEG_THIRD_HOME = (BaseCode.THIRD, BaseCode.HOME)

_STYLE_DIM = "dim white"
_STYLE_LIT = "bold white"
_STYLE_SCORED = "bold green"

_MARKER_SCORED = "◆"
_MARKER_LOB = "●"
_MARKER_OUT = "✕"
_MARKER_HOME = "◇"


def _segment_style(state: SegmentState) -> str:
    """Return the Rich style string for a given segment state."""
    if state is SegmentState.SCORED:
        return _STYLE_SCORED
    if state is SegmentState.LIT:
        return _STYLE_LIT
    return _STYLE_DIM


def _get_seg(diamond: DiamondState, key: tuple[BaseCode, BaseCode]) -> SegmentState:
    """Return the segment state for a base-path leg, defaulting to DIM."""
    return diamond.segments.get(key, SegmentState.DIM)


def _home_marker(diamond: DiamondState) -> tuple[str, str]:
    """Return (glyph, style) for the home plate marker based on final state."""
    if diamond.final_base is BaseCode.HOME:
        if diamond.final_state is RunnerFinalState.SCORED:
            return _MARKER_SCORED, _STYLE_SCORED
        if diamond.final_state is RunnerFinalState.OUT:
            return _MARKER_OUT, "bold red"
    return _MARKER_HOME, _STYLE_DIM


def _base_marker(diamond: DiamondState, base: BaseCode) -> tuple[str, str] | None:
    """
    Return (glyph, style) if the runner's final position is this base,
    or None if no marker should be placed here.
    """
    if diamond.final_base is not base:
        return None
    if diamond.final_state is RunnerFinalState.LEFT_ON_BASE:
        return _MARKER_LOB, "bold yellow"
    if diamond.final_state is RunnerFinalState.OUT:
        return _MARKER_OUT, "bold red"
    if diamond.final_state is RunnerFinalState.RUNNING:
        return _MARKER_LOB, "bold cyan"
    return None


def _render_empty() -> Text:
    """Render a blank diamond when no state is available."""
    lines = [
        "      2B      ",
        "     ╱  ╲     ",
        "   3B    1B   ",
        "     ╲  ╱     ",
        "      ◇       ",
        "              ",
        "              ",
        "              ",
    ]
    text = Text()
    for line in lines:
        text.append(line + "\n", style=_STYLE_DIM)
    return text


def _render_diamond(diamond: DiamondState) -> Text:  # noqa: C901
    """Build the full Rich Text for a populated diamond state."""
    seg_h1 = _get_seg(diamond, _SEG_HOME_FIRST)
    seg_12 = _get_seg(diamond, _SEG_FIRST_SECOND)
    seg_23 = _get_seg(diamond, _SEG_SECOND_THIRD)
    seg_3h = _get_seg(diamond, _SEG_THIRD_HOME)

    style_h1 = _segment_style(seg_h1)
    style_12 = _segment_style(seg_12)
    style_23 = _segment_style(seg_23)
    style_3h = _segment_style(seg_3h)

    # ---- Derive second base label / marker ----
    second_marker = _base_marker(diamond, BaseCode.SECOND)
    if second_marker:
        second_glyph, second_style = second_marker
    else:
        second_glyph, second_style = "2B", _STYLE_DIM

    # ---- Derive third base label / marker ----
    third_marker = _base_marker(diamond, BaseCode.THIRD)
    if third_marker:
        third_glyph, third_style = third_marker
    else:
        third_glyph, third_style = "3B", _STYLE_DIM

    # ---- Derive first base label / marker ----
    first_marker = _base_marker(diamond, BaseCode.FIRST)
    if first_marker:
        first_glyph, first_style = first_marker
    else:
        first_glyph, first_style = "1B", _STYLE_DIM

    # ---- Derive home plate marker ----
    home_glyph, home_style = _home_marker(diamond)

    text = Text()

    # Line 0: "      2B      "
    text.append("      ", style=_STYLE_DIM)
    text.append(second_glyph, style=second_style)
    text.append("      \n", style=_STYLE_DIM)

    # Line 1: "     ╱  ╲     " — left slash = 2B→3B side, right slash = 2B→1B side
    text.append("     ", style=_STYLE_DIM)
    text.append("╱", style=style_23)
    text.append("  ", style=_STYLE_DIM)
    text.append("╲", style=style_12)
    text.append("     \n", style=_STYLE_DIM)

    # Line 2: "   3B    1B   "
    text.append("   ", style=_STYLE_DIM)
    text.append(third_glyph, style=third_style)
    text.append("    ", style=_STYLE_DIM)
    text.append(first_glyph, style=first_style)
    text.append("   \n", style=_STYLE_DIM)

    # Line 3: "     ╲  ╱     " — left backslash = 3B→HOME, right slash = HOME→1B
    text.append("     ", style=_STYLE_DIM)
    text.append("╲", style=style_3h)
    text.append("  ", style=_STYLE_DIM)
    text.append("╱", style=style_h1)
    text.append("     \n", style=_STYLE_DIM)

    # Line 4: "      ◇       " (or scored marker)
    text.append("      ", style=_STYLE_DIM)
    text.append(home_glyph, style=home_style)
    text.append("       \n", style=_STYLE_DIM)

    # Line 5: result label and fielder notation
    result_display = diamond.result_type.display
    fielders = diamond.fielders
    label = f"{fielders}  {result_display}" if fielders else result_display
    label_line = label[:14].center(14)
    text.append(label_line + "\n", style="bold white")

    # Line 6: annotations (SB, CS, etc.) if any
    if diamond.annotations:
        ann_line = " ".join(diamond.annotations)[:14].center(14)
        text.append(ann_line + "\n", style="italic yellow")
    else:
        text.append("              \n", style=_STYLE_DIM)

    # Line 7: blank padding
    text.append("              \n", style=_STYLE_DIM)

    return text


class DiamondWidget(Widget):
    """Renders a miniature baseball diamond showing a runner's journey.

    The diamond has 4 path segments: HOME->1B, 1B->2B, 2B->3B, 3B->HOME.
    Each segment can be DIM (not reached), LIT (passed through), or SCORED.

    Layout (8 lines, 14 chars wide):
          2B
         / \\
       3B    1B
         \\ /
          ◇
       6-3  GB
    """

    DEFAULT_CSS = """
    DiamondWidget {
        width: 16;
        height: 8;
        padding: 0;
    }
    """

    diamond_state: reactive[DiamondState | None] = reactive(None)

    def render(self) -> Text:
        """Render the diamond with colored segments based on state."""
        if self.diamond_state is None:
            return _render_empty()
        return _render_diamond(self.diamond_state)
