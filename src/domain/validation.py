"""
domain/validation.py — Hostname validation.
Extracted from app.py; RFC 1123 + Windows reserved names.
"""
import re
from typing import Tuple

_RESERVED_HOSTNAMES = frozenset([
    "CON", "PRN", "AUX", "NUL",
    "COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9",
    "LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9",
])
# Single char OK (A-Z0-9), or 2-15 chars: starts/ends with alnum, middle can have hyphen
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-]{0,13}[A-Za-z0-9])?$")


def validate_hostname(name: str) -> Tuple[bool, str]:
    """
    RFC 1123 + Windows reserved names + leading/trailing hyphen.
    Returns (is_valid, error_message).
    """
    if not name:
        return False, "სახელი ცარიელია"
    if len(name) > 15:
        return False, f"სახელი არ უნდა აღემატებოდეს 15 სიმბოლოს (ამჟამად {len(name)})"
    if name.upper() in _RESERVED_HOSTNAMES:
        return False, f"'{name}' Windows-ის სისტემური სახელია"
    if name.startswith("-") or name.endswith("-"):
        return False, "სახელი არ უნდა იწყებოდეს ან მთავრდებოდეს '-'-ით"
    if not _HOSTNAME_RE.match(name):
        return False, "სახელი უნდა შეიცავდეს მხოლოდ ლათინურ ასოებს, ციფრებს და '-'-ს"
    return True, ""
