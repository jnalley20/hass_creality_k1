# Creality K1 Helpers Module
#
# Copyright (C) 2025 Joshua Wherrett <thejoshw.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from typing import Any
import logging

_LOGGER = logging.getLogger(__name__)

def to_float_or_none(data: Any, key: str) -> float | None:
    """Attempts to convert a value to float, returns None if conversion fails."""
    value = None
    if isinstance(data, dict):
        value = data.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        _LOGGER.debug(f"Could not convert value '{value}' to float.")
        return None