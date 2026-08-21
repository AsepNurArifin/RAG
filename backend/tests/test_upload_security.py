"""Tests keamanan upload — path traversal, sanitasi filename, canonical storage name."""

import pytest

from app.api.upload import _sanitize_display_filename


class TestFilenameSanitization:
    def test_normal_filename_ok(self):
        assert _sanitize_display_filename("laporan.pdf") == "laporan.pdf"

    def test_filename_with_spaces_ok(self):
        assert _sanitize_display_filename("laporan akhir 2026.pdf") == "laporan akhir 2026.pdf"

    def test_unicode_filename_ok(self):
        assert _sanitize_display_filename("réport 2026.pdf") == "réport 2026.pdf"

    def test_forward_slash_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("../../etc/passwd")

    def test_backslash_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("..\\outside.txt")

    def test_absolute_windows_path_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("C:\\outside.txt")

    def test_absolute_unix_path_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("/tmp/outside.txt")

    def test_control_character_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("file\u0000evil.pdf")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("a" * 500 + ".pdf")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("")

    def test_null_byte_in_name_rejected(self):
        with pytest.raises(ValueError):
            _sanitize_display_filename("file\x00.pdf")
