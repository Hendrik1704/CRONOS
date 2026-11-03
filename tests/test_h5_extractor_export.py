"""Tests for h5_extractor with real HDF5 files (native export, CLI input)."""

import importlib.util
import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import h5py
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _import_extractor():
    mod_path = PROJECT_ROOT / "utilities" / "h5_extractor.py"
    spec = importlib.util.spec_from_file_location("h5_extractor_real", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _store_like_cronos(group, name: str, text: str, dtype) -> np.ndarray:
    """Store a text table the way src/handle_results.py zip_into_hdf5 does."""
    data = np.genfromtxt(io.StringIO(text), dtype=dtype)
    dset = group.create_dataset(name, data=data)
    first_line = text.splitlines()[0].strip()
    if first_line.startswith("#"):
        dset.attrs["header"] = np.bytes_(first_line)
    return data


def _make_event(tmp_path: Path, tables: dict, dtype=np.float32) -> Path:
    path = tmp_path / "event_0.h5"
    with h5py.File(path, "w") as f:
        g = f.create_group("event_0")
        for name, text in tables.items():
            _store_like_cronos(g, name, text, dtype)
    return path


def _extract_all(mod, h5_path: Path, out_dir: Path) -> list:
    ex = mod.HDF5Extractor(str(h5_path), str(out_dir), "WARNING")
    ex.scan_h5_file()
    return ex.extract_multiple_datasets(list(range(len(ex.datasets_info))))


@pytest.mark.unit
@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_native_export_keeps_header_and_precision(tmp_path: Path, dtype):
    mod = _import_extractor()
    name = "particle_9999_vndata_eta_-0.5_0.5.dat"
    text = (
        "# n  Qn_real  Qn_real_err\n"
        "0  1.23456789e+02  3.14159265e-05\n"
        "1  2.71828183e-01  1.41421356e-07\n"
    )
    h5_path = _make_event(tmp_path, {name: text}, dtype)
    files = _extract_all(mod, h5_path, tmp_path / "out")
    assert len(files) == 1
    out = Path(files[0])
    assert out.name == f"event_0_{name}"

    lines = out.read_text().splitlines()
    assert lines[0] == "# n  Qn_real  Qn_real_err"
    restored = np.loadtxt(out, dtype=dtype)
    expected = np.genfromtxt(io.StringIO(text), dtype=dtype)
    np.testing.assert_array_equal(restored, expected)


@pytest.mark.unit
def test_native_export_single_row_table_is_not_transposed(tmp_path: Path):
    mod = _import_extractor()
    name = "particle_211_Cn4_eta_-0.5_0.5.dat"
    text = "# n  Cn4  Cn4_err\n0  1.5  0.25\n"
    h5_path = _make_event(tmp_path, {name: text})
    out = Path(_extract_all(mod, h5_path, tmp_path / "out")[0])
    restored = np.loadtxt(out, ndmin=2)
    assert restored.shape == (1, 3)
    np.testing.assert_array_equal(restored[0], [0.0, 1.5, 0.25])


@pytest.mark.unit
def test_native_export_single_column_table(tmp_path: Path):
    mod = _import_extractor()
    name = "check_211_values.dat"
    text = "# value\n1.0\n2.0\n3.0\n"
    h5_path = _make_event(tmp_path, {name: text})
    out = Path(_extract_all(mod, h5_path, tmp_path / "out")[0])
    restored = np.loadtxt(out, ndmin=2)
    assert restored.shape == (3, 1)


@pytest.mark.unit
def test_get_user_selection_stops_on_eof(tmp_path: Path):
    mod = _import_extractor()
    h5_path = _make_event(tmp_path, {"a.dat": "# x y\n1 2\n3 4\n"})
    ex = mod.HDF5Extractor(str(h5_path), str(tmp_path / "out"), "WARNING")
    ex.scan_h5_file()

    calls = []

    def fake_input(prompt=""):
        calls.append(prompt)
        if len(calls) > 3:  # guard against the former endless loop
            raise KeyboardInterrupt
        raise EOFError

    with patch("builtins.input", side_effect=fake_input):
        assert ex.get_user_selection() == []
    assert len(calls) == 1


@pytest.mark.unit
def test_main_without_extract_does_not_prompt_on_non_tty(tmp_path: Path):
    mod = _import_extractor()
    h5_path = _make_event(tmp_path, {"a.dat": "# x y\n1 2\n3 4\n"})
    argv = ["h5_extractor.py", str(h5_path), "-o", str(tmp_path / "out")]
    calls = []

    def fake_input(prompt=""):
        calls.append(prompt)
        raise KeyboardInterrupt  # ends the prompt loop of older versions

    with patch("sys.argv", argv), patch.object(
        mod.sys.stdin, "isatty", return_value=False
    ), patch("builtins.input", side_effect=fake_input):
        assert mod.main() == 0
    assert calls == []


@pytest.mark.unit
def test_help_epilog_lists_only_existing_options():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "utilities" / "h5_extractor.py")]
        + ["--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--format" not in result.stdout
