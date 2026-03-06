"""CaracalHeader — non-collapsible header with fixed height."""

from __future__ import annotations

from textual.widgets import Header


class CaracalHeader(Header):
    """Header that cannot be collapsed by clicking."""

    def _on_click(self) -> None:
        """Disable the default click-to-toggle behavior."""
