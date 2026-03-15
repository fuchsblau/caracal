"""News sources and data types."""

from caracal.news.protocol import NewsItem, NewsSource
from caracal.news.reuters import ReutersRSSSource

__all__ = ["NewsItem", "NewsSource", "ReutersRSSSource"]
