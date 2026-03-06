"""WatchlistPanel -- main container for tabbed watchlists and detail view."""

from __future__ import annotations

from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import TabPane, TabbedContent

from caracal.tui.widgets.asset_detail_view import AssetDetailView
from caracal.tui.widgets.watchlist_table import WatchlistTable


class WatchlistPanel(Widget):
    """Container managing TabbedContent with WatchlistTables and drill-down."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._watchlist_data: dict[str, list[dict]] = {}
        self._in_detail: bool = False

    @property
    def tab_count(self) -> int:
        """Return the number of tabs in the TabbedContent."""
        try:
            return self.query_one(TabbedContent).tab_count
        except NoMatches:
            return 0

    def compose(self):
        yield TabbedContent(id="watchlist-tabs")
        yield AssetDetailView(id="detail-view")

    def on_mount(self) -> None:
        self.query_one("#detail-view", AssetDetailView).display = False

    async def load_watchlists(self, data: dict[str, list[dict]]) -> None:
        """Load all watchlists into tabs."""
        self._watchlist_data = data
        tc = self.query_one("#watchlist-tabs", TabbedContent)

        # Clear existing tabs
        await tc.clear_panes()

        # Create new tabs
        for name, rows in data.items():
            table = WatchlistTable(id=f"wt-{name}")
            pane = TabPane(name, table, id=f"tab-{name}")
            await tc.add_pane(pane)
            table.load_data(rows)

    def refresh_watchlist(self, name: str, rows: list[dict]) -> None:
        """Refresh data for a single watchlist tab."""
        self._watchlist_data[name] = rows
        try:
            table = self.query_one(f"#wt-{name}", WatchlistTable)
            table.load_data(rows)
        except NoMatches:
            pass

    def show_detail(self, detail: dict) -> None:
        """Show the drill-down detail view, hide tabs."""
        self._in_detail = True
        self.query_one("#watchlist-tabs", TabbedContent).display = False
        detail_view = self.query_one("#detail-view", AssetDetailView)
        detail_view.display = True
        detail_view.load_detail(detail)

    def hide_detail(self) -> None:
        """Hide detail view, restore tabs."""
        self._in_detail = False
        self.query_one("#detail-view", AssetDetailView).display = False
        self.query_one("#watchlist-tabs", TabbedContent).display = True

    @property
    def in_detail(self) -> bool:
        """Return whether the detail view is currently showing."""
        return self._in_detail

    def get_active_table(self) -> WatchlistTable | None:
        """Return the WatchlistTable in the currently active tab."""
        tc = self.query_one("#watchlist-tabs", TabbedContent)
        active = tc.active
        if not active:
            return None
        try:
            pane = tc.query_one(f"#{active}", TabPane)
            return pane.query_one(WatchlistTable)
        except NoMatches:
            return None
