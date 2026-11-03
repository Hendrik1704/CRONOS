"""Tests for the format conversion utilities in utilities/."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _import(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", PROJECT_ROOT / "utilities" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_eos(path: Path):
    # Simple conformal-like table: e, p = e/3, s (unused), T ~ e^(1/4)
    e = np.linspace(0.01, 10.0, 200)
    p = e / 3.0
    T = 0.2 * e**0.25
    np.stack([e, p, np.zeros_like(e), T], axis=1).astype(float).tofile(path)


def _kompost_line(e: float) -> str:
    cols = [0.0, 0.1, 0.2, e, 1.0, 0.0, 0.0, 0.0] + [0.0] * 10
    return " ".join(str(c) for c in cols) + " \n"


@pytest.mark.unit
def test_s_matching_sets_vacuum_below_eos_table(tmp_path: Path):
    k2m = _import("KoMPoST_to_MUSIC")
    eos = tmp_path / "eos.dat"
    _write_eos(eos)
    e_kompost = np.array([0.0, 1e-8, 1e-4, 1.0])
    e_new, bulk = k2m.s_matching(e_kompost, 40.0, str(eos))
    assert np.all(e_new >= 0.0)
    assert e_new[0] == 0.0 and e_new[1] == 0.0
    assert bulk[0] == 0.0 and bulk[1] == 0.0
    assert e_new[3] > 0.0


@pytest.mark.unit
@pytest.mark.parametrize("matching", ["0", "1"])
def test_kompost_to_music_writes_19_columns(tmp_path: Path, matching: str):
    eos = tmp_path / "eos.dat"
    _write_eos(eos)
    f_in = tmp_path / "in.txt"
    f_out = tmp_path / "out.txt"
    f_in.write_text(
        "# tau_in_fm 0.4\n" + _kompost_line(1.0) + _kompost_line(2.0)
    )
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "utilities" / "KoMPoST_to_MUSIC.py"),
        ]
        + [matching, "40", str(eos), str(f_in), str(f_out)],
        check=True,
        capture_output=True,
    )
    data = np.loadtxt(f_out, comments="#")
    assert data.shape == (2, 19)
    if matching == "0":
        assert np.all(data[:, 18] == 0.0)
        np.testing.assert_array_equal(data[:, 3], [1.0, 2.0])


@pytest.mark.unit
def test_kompost_to_music_rejects_unknown_matching(tmp_path: Path):
    f_in = tmp_path / "in.txt"
    f_in.write_text("# header\n" + _kompost_line(1.0))
    res = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "utilities" / "KoMPoST_to_MUSIC.py"),
        ]
        + ["2", "40", "eos.dat", str(f_in), str(tmp_path / "out.txt")],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "NameError" not in res.stderr
    assert not (tmp_path / "out.txt").exists()


@pytest.mark.unit
def test_oscar_conversion_uses_own_event_multiplicity(tmp_path: Path):
    conv = _import("convert_OSCAR1997A_to_OSCAR2013")
    pdg = pd.DataFrame({"PDG_ID": [211], "charge": [1]})

    def particle(i):
        return f"{i} 211 0.1 0.2 0.3 1.0 0.14 1.0 2.0 3.0 4.0\n"

    lines = ["OSC1999A\n", "final_id_p_x\n", "iSS header\n"]
    lines += ["         1           2         0         0\n"]
    lines += [particle(1), particle(2)]
    lines += ["         2           3         0         0\n"]
    lines += [particle(1), particle(2), particle(3)]
    f_in = tmp_path / "OSCAR.DAT"
    f_in.write_text("".join(lines))
    f_out = tmp_path / "out.oscar"

    assert conv.convert_oscar_streaming(f_in, pdg, f_out) == 2
    headers = [ln for ln in f_out.read_text().splitlines() if " out " in ln]
    assert headers == ["# event 1 out 2", "# event 2 out 3"]


@pytest.mark.unit
def test_mcdipper_tau0_regex_stops_at_non_numeric(tmp_path: Path):
    mcd = _import("McDipper_to_MUSIC")
    f = tmp_path / "energy.dat"
    f.write_text("# tau0 = 0.4, grid = 2\n0 0 0 1.5\n")
    tau0, energy = mcd.read_energy_data(f, 2, 1)
    assert tau0 == pytest.approx(0.4)
    assert energy[0, 0, 0] == pytest.approx(1.5)
