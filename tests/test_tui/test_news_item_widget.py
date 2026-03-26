"""Tests for NewsItemWidget URL scheme validation."""

from caracal.tui.widgets.news_item import is_safe_url


class TestIsSafeUrl:
    def test_https_is_safe(self):
        assert is_safe_url("https://example.com/news") is True

    def test_http_is_safe(self):
        assert is_safe_url("http://example.com/news") is True

    def test_file_scheme_rejected(self):
        assert is_safe_url("file:///etc/passwd") is False

    def test_javascript_scheme_rejected(self):
        assert is_safe_url("javascript:alert(1)") is False

    def test_data_scheme_rejected(self):
        assert is_safe_url("data:text/html,<h1>hi</h1>") is False

    def test_ftp_rejected(self):
        assert is_safe_url("ftp://example.com/file") is False

    def test_none_is_not_safe(self):
        assert is_safe_url(None) is False

    def test_empty_string_is_not_safe(self):
        assert is_safe_url("") is False

    def test_no_scheme_rejected(self):
        assert is_safe_url("example.com/news") is False
