# SPDX-License-Identifier: Apache-2.0
# Tests for demo_info.py. Run from the scripts directory with:
#   python -m pytest test_demo_info.py

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError, validate

from demo_info import load_demo_info, parse_demo_info

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "schemas" / "shuttle.schema.json").read_text()
)


def parse(text):
    return parse_demo_info(yaml.safe_load(text))


def test_empty_file():
    assert parse("") == {}
    assert parse("# just a comment\n") == {}


def test_entry_without_settings():
    assert parse("tt_um_vga_example:\n") == {"tt_um_vga_example": {}}
    assert parse("tt_um_vga_example: {}\n") == {"tt_um_vga_example": {}}


def test_entry_with_settings():
    info = parse(
        "tt_um_rebeccargb_colorbars:\n"
        "  clock_hz: 25175000\n"
        "  seconds: 30\n"
        "  ui_in: 0x12\n"
        "  uio_oe_pico: 0\n"
        "  uio_in: 255\n"
    )
    assert info == {
        "tt_um_rebeccargb_colorbars": {
            "clock_hz": 25175000,
            "seconds": 30,
            "ui_in": 0x12,
            "uio_oe_pico": 0,
            "uio_in": 255,
        }
    }


def test_fractional_seconds():
    assert parse("a:\n  seconds: 7.5\n") == {"a": {"seconds": 7.5}}


@pytest.mark.parametrize(
    "text",
    [
        "- tt_um_a\n",  # a list, not a mapping
        "a: 5\n",  # settings must be a mapping
        "a:\n  colour: red\n",  # unknown key (typo protection)
        "a:\n  seconds: 0\n",
        "a:\n  seconds: fast\n",
        "a:\n  seconds: true\n",
        "a:\n  clock_hz: -1\n",
        "a:\n  clock_hz: 2000000000\n",
        "a:\n  clock_hz: 25.175e6\n",  # YAML float: must be an integer
        "a:\n  ui_in: 256\n",
        "a:\n  uio_in: -1\n",
        "a:\n  uio_oe_pico: yes\n",
    ],
)
def test_invalid(text):
    with pytest.raises(ValueError):
        parse(text)


def test_load_missing_file(tmp_path):
    assert load_demo_info(local_path=tmp_path / "nope.yaml") == {}


def test_load_local_file(tmp_path):
    p = tmp_path / "demo.yaml"
    p.write_text("tt_um_a:\n  seconds: 20\n")
    assert load_demo_info(local_path=p) == {"tt_um_a": {"seconds": 20}}


PROJECT = {
    "macro": "tt_um_a",
    "address": 1,
    "title": "t",
    "author": "a",
    "description": "d",
    "clock_hz": 0,
    "tiles": "1x1",
    "analog_pins": [],
    "repo": "https://github.com/x/y",
    "commit": "",
    "pinout": {},
}


def shuttle_with(project):
    return {
        "version": 3,
        "id": "ttfake",
        "name": "Fake",
        "repo": "https://github.com/TinyTapeout/fake",
        "commit": "0" * 40,
        "projects": [project],
    }


def test_schema_accepts_demo():
    validate(shuttle_with(dict(PROJECT, demo={})), SCHEMA)
    validate(shuttle_with(dict(PROJECT, demo={"clock_hz": 25175000, "seconds": 7.5,
                                              "ui_in": 1, "uio_oe_pico": 0, "uio_in": 0})), SCHEMA)
    validate(shuttle_with(PROJECT), SCHEMA)


def test_schema_rejects_bad_demo():
    with pytest.raises(ValidationError):
        validate(shuttle_with(dict(PROJECT, demo={"colour": "red"})), SCHEMA)
    with pytest.raises(ValidationError):
        validate(shuttle_with(dict(PROJECT, demo={"ui_in": 300})), SCHEMA)
    with pytest.raises(ValidationError):
        validate(shuttle_with(dict(PROJECT, demo=True)), SCHEMA)
