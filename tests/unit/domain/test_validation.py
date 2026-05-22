"""
tests/unit/domain/test_validation.py — TASK 1.5: 10 validation unit tests.
"""
import pytest
from src.domain.validation import validate_hostname


class TestValidateHostname:
    def test_valid_simple(self):
        ok, msg = validate_hostname("PC-001")
        assert ok and msg == ""

    def test_too_long(self):
        ok, msg = validate_hostname("A" * 16)
        assert not ok and "15" in msg

    def test_leading_hyphen(self):
        ok, msg = validate_hostname("-BADNAME")
        assert not ok

    def test_trailing_hyphen(self):
        ok, msg = validate_hostname("BADNAME-")
        assert not ok

    def test_reserved_name_con(self):
        ok, msg = validate_hostname("CON")
        assert not ok and "სისტემური" in msg

    def test_reserved_name_com1(self):
        ok, msg = validate_hostname("COM1")
        assert not ok

    def test_empty(self):
        ok, msg = validate_hostname("")
        assert not ok

    def test_georgian_chars_rejected(self):
        ok, msg = validate_hostname("PC-კომპი")
        assert not ok

    def test_exactly_15_chars(self):
        ok, msg = validate_hostname("A" * 14 + "1")  # 15 chars
        assert ok

    def test_single_char(self):
        ok, msg = validate_hostname("A")
        assert ok

    def test_valid_with_numbers(self):
        ok, msg = validate_hostname("DESKTOP-2024")
        assert ok

    def test_all_reserved_nul(self):
        ok, msg = validate_hostname("NUL")
        assert not ok

    def test_lpt_reserved(self):
        ok, msg = validate_hostname("LPT1")
        assert not ok

    def test_spaces_rejected(self):
        ok, msg = validate_hostname("PC NAME")
        assert not ok

    def test_underscore_rejected(self):
        ok, msg = validate_hostname("PC_NAME")
        assert not ok
