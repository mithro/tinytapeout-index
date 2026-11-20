# SPDX-License-Identifier: Apache-2.0
# Reads a shuttle's optional projects/demo.yaml: the projects to include in
# the demo board firmware's demo mode, with optional per-project settings
# (named as in the firmware's /demo.json entries).
#
#   tt_um_vga_example:              # include, with default settings
#   tt_um_rebeccargb_colorbars:
#     clock_hz: 25175000            # project clock to use for the demo
#     duration_ms: 30000            # how long to show it
#     ui_in: 0                      # input values to set (0-255)
#     uio_oe_pico: 0
#     uio_in: 0
#   tt_um_RoyTr16:
#     ui_in: 7
#     keys:                         # inputs to play while it is shown
#       via: ui                     # "ui" or "gamepad"
#       steps: [{set: 5}, {wait_ms: 40}, {set: 7}, {wait_ms: 250}]

import urllib.error
import urllib.request
from pathlib import Path

import yaml

_BYTE_KEYS = ("ui_in", "uio_oe_pico", "uio_in")
_MAX_CLOCK_HZ = 1_000_000_000
_VIA_MAX_SET = {"ui": 0xFF, "gamepad": 0xFFF}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_keys(macro, keys):
    if not isinstance(keys, dict) or set(keys) != {"via", "steps"}:
        raise ValueError(f"demo.yaml: {macro}: keys must have exactly 'via' and 'steps', got {keys!r}")
    via = keys["via"]
    if via not in _VIA_MAX_SET:
        raise ValueError(f"demo.yaml: {macro}: keys via must be 'ui' or 'gamepad', got {via!r}")
    steps = keys["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"demo.yaml: {macro}: keys steps must be a non-empty list")
    total_wait = 0
    for step in steps:
        if not isinstance(step, dict) or len(step) != 1:
            raise ValueError(f"demo.yaml: {macro}: each keys step needs exactly one key, got {step!r}")
        (kind, value), = step.items()
        if kind == "set":
            if not _is_int(value) or not 0 <= value <= _VIA_MAX_SET[via]:
                raise ValueError(f"demo.yaml: {macro}: set must be an integer 0..{_VIA_MAX_SET[via]}, got {value!r}")
        elif kind == "wait_ms":
            if not _is_int(value) or value < 0:
                raise ValueError(f"demo.yaml: {macro}: wait_ms must be an integer >= 0, got {value!r}")
            total_wait += value
        else:
            raise ValueError(f"demo.yaml: {macro}: unknown keys step {kind!r}")
    if total_wait <= 0:
        raise ValueError(f"demo.yaml: {macro}: keys steps must wait for some time")
    return {"via": via, "steps": [dict(s) for s in steps]}


def _check_settings(macro, settings):
    if settings is None:
        return {}
    if not isinstance(settings, dict):
        raise ValueError(f"demo.yaml: {macro}: settings must be a mapping, got {settings!r}")
    result = {}
    for key, value in settings.items():
        if key == "duration_ms":
            if not _is_int(value) or value <= 0:
                raise ValueError(f"demo.yaml: {macro}: duration_ms must be a positive integer, got {value!r}")
        elif key == "clock_hz":
            if not _is_int(value) or not 0 < value <= _MAX_CLOCK_HZ:
                raise ValueError(f"demo.yaml: {macro}: clock_hz must be an integer 1..{_MAX_CLOCK_HZ}, got {value!r}")
        elif key in _BYTE_KEYS:
            if not _is_int(value) or not 0 <= value <= 0xFF:
                raise ValueError(f"demo.yaml: {macro}: {key} must be an integer 0..255, got {value!r}")
        elif key == "keys":
            value = _check_keys(macro, value)
        else:
            raise ValueError(f"demo.yaml: {macro}: unknown setting {key!r}")
        result[key] = value
    return result


def parse_demo_info(data):
    """Validate parsed demo.yaml content; return {macro: settings}."""
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("demo.yaml must be a mapping of project macro to settings")
    return {str(macro): _check_settings(macro, settings) for macro, settings in data.items()}


def load_demo_info(url=None, local_path=None):
    """Load demo.yaml from a local path or URL; a missing file means no demo projects."""
    if local_path is not None:
        path = Path(local_path)
        if not path.exists():
            return {}
        return parse_demo_info(yaml.safe_load(path.read_text()))
    try:
        with urllib.request.urlopen(url) as f:
            return parse_demo_info(yaml.safe_load(f))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise
