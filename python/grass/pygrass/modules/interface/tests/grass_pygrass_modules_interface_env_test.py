"""Tests for grass.pygrass.modules.interface.env"""

import gc
import warnings

import pytest

from grass.pygrass.modules.interface.env import G_debug


@pytest.fixture
def debug_session(tmp_path, monkeypatch):
    """Point GISRC to a file which sets the debug level to 3"""
    gisrc = tmp_path / "gisrc"
    gisrc.write_text("DEBUG: 3\n")
    monkeypatch.setenv("GISRC", str(gisrc))
    return tmp_path


def test_g_debug_writes_to_debug_file(debug_session, monkeypatch):
    """Messages at or below the debug level are appended to GRASS_DEBUG_FILE"""
    debug_file = debug_session / "debug.txt"
    monkeypatch.setenv("GRASS_DEBUG_FILE", str(debug_file))
    G_debug(1, "first")
    G_debug(3, "second")
    G_debug(4, "not printed")
    assert debug_file.read_text().splitlines() == ["D1/3:  first", "D3/3:  second"]


def test_g_debug_closes_debug_file(debug_session, monkeypatch):
    """Writing to GRASS_DEBUG_FILE does not leave the file open"""
    monkeypatch.setenv("GRASS_DEBUG_FILE", str(debug_session / "debug.txt"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        G_debug(1, "message")
        gc.collect()
    assert not [w for w in caught if issubclass(w.category, ResourceWarning)]


def test_g_debug_prints_to_stderr_without_debug_file(
    debug_session, monkeypatch, capsys
):
    """Without GRASS_DEBUG_FILE, messages go to stderr"""
    monkeypatch.delenv("GRASS_DEBUG_FILE", raising=False)
    G_debug(2, "message")
    assert capsys.readouterr().err == "D2/3:  message\n"
