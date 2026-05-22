"""
shared/ldap_utils.py — Single authoritative LDAP DN validator.
FIX: config.py and ad_repository.py previously maintained two different regexes.
     All code now imports from here (DRY + security consistency).
"""
import re

# Stricter than ad_repository.py's original, matches config.py's version:
# rejects control characters, special LDAP chars in the RDN value.
_LDAP_DN_RE = re.compile(
    r'^(?:(?:CN|OU|DC)=[^,\\<>;"=+*?\x00-\x1f]+,?)+$',
    re.IGNORECASE,
)


def validate_ldap_dn(value: str) -> str:
    """
    Validate and return a clean LDAP DN string.
    Raises ValueError if the value is invalid.
    Returns empty string if value is empty (search base may be empty = forest root).
    """
    if not value:
        return ""
    if not _LDAP_DN_RE.match(value):
        raise ValueError(f"Invalid LDAP DN: {value!r}")
    return value
