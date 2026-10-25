"""Generate a ULA once and let callers persist the resulting project input."""

import secrets
from ipaddress import IPv6Network

from adresplan.core.ipv6 import ula_from_global_id


def generate_ula() -> IPv6Network:
    return ula_from_global_id(secrets.token_bytes(5))
