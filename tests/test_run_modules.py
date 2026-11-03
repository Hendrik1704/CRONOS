"""Tests of the event loop in src.executor.run_modules (checkpointing,
failure handling, result handling, seeds, locking) with fake modules."""

import argparse
import fcntl
import json
import os
import re
import sys
from unittest.mock import patch

import h5py
import pytest

from src.checkpoint_manager import CheckpointManager
from src.configuration import Configuration
from src.executor import (
    check_force_restart_possible,
    prepare_modules,
    run_modules,
)
from src.module_base import BaseModule

# Calls of the fake modules: (module name, event_id, random_seed)
CALLS = []
# Behaviour switches of the fake modules: {(module name, event_id): action}
FAILURES = {}


class FakeModule(BaseModule):
    name = None

    def prepare_environment(self, event_dir):
        os.makedirs(os.path.join(event_dir, self.name), exist_ok=True)

    def prepare_input(self, event_dir):
        pass

    def run(self, event_dir):
        CALLS.append(
            (self.name, self.event_id, self.full_config.general.random_seed)
        )
        action = FAILURES.get((self.name, self.event_id))
        if action == "raise":
            raise RuntimeError(f"{self.name} failed")
        if action == "exit":
            exit(1)

    def fetch_output(self, event_dir):
        index = self.full_config.general.modules.index(self.name)
        with open(
            os.path.join(event_dir, "results", f"output_{index}.dat"), "w"
        ) as f:
            f.write(f"{index} 1000010020\n")
        os.rmdir(os.path.join(event_dir, self.name))


class ModuleA(FakeModule):
    name = "ModuleA"


class ModuleB(FakeModule):
    name = "ModuleB"


REGISTRY = {"ModuleA": ModuleA, "ModuleB": ModuleB}


@pytest.fixture(autouse=True)
def reset_fakes():
    CALLS.clear()
    FAILURES.clear()
    yield
    CALLS.clear()
    FAILURES.clear()


def _config(random_seed=42, number_of_jobs=2, number_events_per_job=2):
    return Configuration(
        {
            "general": {
                "modules": ["ModuleA", "ModuleB"],
                "number_of_jobs": number_of_jobs,
                "number_events_per_job": number_events_per_job,
                "keep_intermediate_results": False,
                "keep_particle_files": False,
                "random_seed": random_seed,
                "cleanup_checkpoints": True,
            },
            "ModuleA": {},
            "ModuleB": {},
        }
    )


def _prepare(tmp_path, config=None, cluster="local"):
    config = config or _config()
    main_config = tmp_path / "main.py"
    user_config = tmp_path / "user.py"
    main_config.write_text("general = {}\n")
    user_config.write_text("general = {'random_seed': 42}\n")
    args = argparse.Namespace(
        run_dir=str(tmp_path / "run"),
        cluster=cluster,
        main_config_path=str(main_config),
        user_config_path=str(user_config),
    )
    prepare_modules(args, config, REGISTRY, str(tmp_path))
    return tmp_path / "run"


def _checkpoint(job_dir):
    with open(job_dir / ".cronos_checkpoint.json") as f:
        return json.load(f)


def test_successful_job(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_1"
    run_modules(_config(), REGISTRY, str(job_dir), str(tmp_path))

    for event in ("event_0", "event_1"):
        assert not (job_dir / event).exists()
        with h5py.File(job_dir / f"{event}.h5", "r") as f:
            group = f[event]
            # the last output file is kept without afterburner_toolkit
            assert list(group["output_1.dat"][()]) == [1, 1000010020]
            assert "configuration.py" in group
    # job completed -> checkpoint removed
    assert not (job_dir / ".cronos_checkpoint.json").exists()


def test_failing_event_does_not_stop_the_job(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    config = _config()
    FAILURES[("ModuleB", "0")] = "raise"

    with pytest.raises(RuntimeError, match="event_0"):
        run_modules(config, REGISTRY, str(job_dir), str(tmp_path))

    # the other event was still processed
    assert (job_dir / "event_1.h5").exists()
    checkpoint = _checkpoint(job_dir)
    assert checkpoint["job_completed"] is False
    assert checkpoint["events"]["event_0"]["failed"] is True
    assert checkpoint["events"]["event_0"]["current_module"] == "ModuleB"

    # resubmission retries only the failed module of the failed event
    FAILURES.clear()
    CALLS.clear()
    run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert [(name, ev) for name, ev, _ in CALLS] == [("ModuleB", "0")]
    assert (job_dir / "event_0.h5").exists()
    assert not (job_dir / ".cronos_checkpoint.json").exists()


def test_module_calling_exit_is_recorded_as_failure(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    FAILURES[("ModuleA", "1")] = "exit"

    with pytest.raises(RuntimeError, match="event_1"):
        run_modules(_config(), REGISTRY, str(job_dir), str(tmp_path))

    checkpoint = _checkpoint(job_dir)
    assert checkpoint["events"]["event_1"]["failed"] is True
    assert checkpoint["events"]["event_1"]["current_module"] == "ModuleA"
    assert (job_dir / "event_0.h5").exists()


def test_failed_result_handling_is_retried(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    config = _config()

    import src.handle_results as hr

    real_zip = hr.zip_into_hdf5
    with patch(
        "src.handle_results.zip_into_hdf5",
        side_effect=RuntimeError("disk full"),
    ):
        with pytest.raises(RuntimeError):
            run_modules(config, REGISTRY, str(job_dir), str(tmp_path))

    checkpoint = _checkpoint(job_dir)
    assert checkpoint["job_completed"] is False
    for event in ("event_0", "event_1"):
        assert checkpoint["events"][event]["completed"] is False
        assert not (job_dir / f"{event}.h5").exists()

    # resume: no module is rerun, only the result handling
    CALLS.clear()
    with patch("src.handle_results.zip_into_hdf5", side_effect=real_zip):
        run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert CALLS == []
    for event in ("event_0", "event_1"):
        with h5py.File(job_dir / f"{event}.h5", "r") as f:
            assert "output_1.dat" in f[event]
    assert not (job_dir / ".cronos_checkpoint.json").exists()


def test_killed_during_result_handling_is_resumed(tmp_path):
    """All modules completed but the event not: result handling is run."""
    run_dir = _prepare(tmp_path, _config(number_events_per_job=1))
    job_dir = run_dir / "job_0"
    config = _config(number_events_per_job=1)
    with patch("src.executor.handle_results", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            run_modules(config, REGISTRY, str(job_dir), str(tmp_path))

    manager = CheckpointManager(str(job_dir))
    assert manager.get_event_status("event_0")["completed_modules"] == [
        "ModuleA",
        "ModuleB",
    ]
    CALLS.clear()
    run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert CALLS == []
    assert (job_dir / "event_0.h5").exists()



def test_killed_after_fetch_output_is_resumed(tmp_path):
    """Output moved and directory removed, but no checkpoint saved."""
    run_dir = _prepare(tmp_path, _config(number_events_per_job=1))
    job_dir = run_dir / "job_0"
    config = _config(number_events_per_job=1)
    original = CheckpointManager.mark_module_completed

    def killed_after_module_a(self, event_id, module_name):
        if module_name == "ModuleA":
            raise KeyboardInterrupt
        original(self, event_id, module_name)

    with patch.object(
        CheckpointManager, "mark_module_completed", killed_after_module_a
    ):
        with pytest.raises(KeyboardInterrupt):
            run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert not (job_dir / "event_0" / "ModuleA").exists()

    CALLS.clear()
    run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    # ModuleA is not run again, ModuleB runs on its output
    assert [call[0] for call in CALLS] == ["ModuleB"]
    assert (job_dir / "event_0.h5").exists()


def test_module_directory_is_set_up_again_after_interrupted_cleanup(tmp_path):
    """Directory removed before the output was written: run it again."""
    run_dir = _prepare(tmp_path, _config(number_events_per_job=1))
    job_dir = run_dir / "job_0"
    config = _config(number_events_per_job=1)

    def interrupted_fetch_output(self, event_dir):
        os.rmdir(os.path.join(event_dir, self.name))
        raise KeyboardInterrupt

    with patch.object(ModuleB, "fetch_output", interrupted_fetch_output):
        with pytest.raises(KeyboardInterrupt):
            run_modules(config, REGISTRY, str(job_dir), str(tmp_path))

    CALLS.clear()
    run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert [call[0] for call in CALLS] == ["ModuleB"]
    assert (job_dir / "event_0.h5").exists()

def test_bad_event_is_marked_and_not_retried(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    config = _config()
    config.general.cleanup_checkpoints = False

    def fake_handle_results(config, results_path, event_id):
        if event_id == "0":  # event_0 fails the quality check
            return False
        open(os.path.join(results_path, f"event_{event_id}.h5"), "w").close()
        return True

    with patch("src.executor.handle_results", fake_handle_results):
        run_modules(config, REGISTRY, str(job_dir), str(tmp_path))

    assert not (job_dir / "event_0").exists()
    assert not (job_dir / "event_0.h5").exists()
    checkpoint = _checkpoint(job_dir)
    assert checkpoint["job_completed"] is True
    assert checkpoint["events"]["event_0"]["bad"] is True
    assert checkpoint["bad_events"] == ["event_0"]

    # rerunning the job does not retry the bad event
    CALLS.clear()
    run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert CALLS == []


def test_bad_event_with_afterburner_quality_check(tmp_path):
    """Real handle_results: a failed quality check is not an error."""
    run_dir = _prepare(tmp_path, _config(number_events_per_job=1))
    job_dir = run_dir / "job_0"
    config = _config(number_events_per_job=1)
    with patch("src.handle_results.check_if_event_is_good", return_value=False):
        run_modules(config, REGISTRY, str(job_dir), str(tmp_path))
    assert not (job_dir / "event_0").exists()
    assert not (job_dir / "event_0.h5").exists()


@pytest.mark.parametrize("random_seed", [42, -1])
def test_seeds_per_event(tmp_path, random_seed):
    config = _config(random_seed=random_seed)
    run_dir = _prepare(tmp_path, config)
    seeds = {}
    for job in ("job_0", "job_1"):
        run_modules(config, REGISTRY, str(run_dir / job), str(tmp_path))
        assert config.general.random_seed == random_seed
    for name, event_id, seed in CALLS:
        seeds.setdefault(seed, set()).add(event_id)

    used = sorted(seeds)
    if random_seed == -1:
        assert used == [-1]
    else:
        # job_index * number_events_per_job + event_index
        assert used == [42, 43, 44, 45]
    # the per-event seed is stored in the packaged configuration
    with h5py.File(run_dir / "job_1" / "event_1.h5", "r") as f:
        text = f["event_1/configuration.py"][()].decode()
    expected = 45 if random_seed != -1 else -1
    assert re.search(rf"'random_seed': {expected}\b", text)


def test_job_dir_lock(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    with open(job_dir / ".cronos.lock", "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="already being run"):
            run_modules(_config(), REGISTRY, str(job_dir), str(tmp_path))
    assert CALLS == []
    # after the lock is released the job runs
    run_modules(_config(), REGISTRY, str(job_dir), str(tmp_path))
    assert (job_dir / "event_0.h5").exists()


def test_force_restart_check(tmp_path):
    run_dir = _prepare(tmp_path)
    job_dir = run_dir / "job_0"
    modules = ["ModuleA", "ModuleB"]
    assert check_force_restart_possible(str(job_dir), modules) == []

    FAILURES[("ModuleB", "0")] = "raise"
    with pytest.raises(RuntimeError):
        run_modules(_config(), REGISTRY, str(job_dir), str(tmp_path))
    problems = check_force_restart_possible(str(job_dir), modules)
    # event_1 finished, ModuleA of event_0 removed its directory
    assert any("event_1.h5" in p for p in problems)
    assert any("event_0/ModuleA" in p for p in problems)


def test_force_restart_reruns_from_first_module(tmp_path):
    run_dir = _prepare(tmp_path, _config(number_events_per_job=1))
    job_dir = run_dir / "job_0"
    config = _config(number_events_per_job=1)
    manager = CheckpointManager(str(job_dir))
    manager.mark_module_completed("event_0", "ModuleA")
    run_modules(
        config, REGISTRY, str(job_dir), str(tmp_path), force_restart=True
    )
    assert [name for name, _, _ in CALLS] == ["ModuleA", "ModuleB"]


def test_prepare_snapshots_configs_and_creates_log_dir(tmp_path):
    run_dir = _prepare(tmp_path)
    assert (run_dir / "main_config.py").read_text() == "general = {}\n"
    assert (run_dir / "user_config.py").read_text() == (
        "general = {'random_seed': 42}\n"
    )
    assert (run_dir / "log").is_dir()


def test_prepare_refuses_zero_jobs(tmp_path):
    with pytest.raises(SystemExit):
        _prepare(tmp_path, _config(number_of_jobs=0))
    assert not (tmp_path / "run" / "job_0").exists()


def test_noctua2_script_uses_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = _config()
    main_config = tmp_path / "main.py"
    user_config = tmp_path / "user.py"
    main_config.write_text("general = {}\n")
    user_config.write_text("general = {}\n")
    args = argparse.Namespace(
        run_dir="nested/run/",
        cluster="noctua2",
        main_config_path="main.py",
        user_config_path="user.py",
    )
    prepare_modules(args, config, REGISTRY, str(tmp_path))
    run_dir = tmp_path / "nested" / "run"
    script = (run_dir / "submit_job.sh").read_text()
    assert f"#SBATCH -o {run_dir}/log/output_%A_%a.log" in script
    assert "#SBATCH --array=0-1" in script
    assert f'--main_config_path "{run_dir}/main_config.py"' in script
    assert f'--user_config_path "{run_dir}/user_config.py"' in script
    assert f'--job_dir "{run_dir}/job_$SLURM_ARRAY_TASK_ID/"' in script
    assert "../" not in script
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert f'python "{repo_root}/run_simulations.py"' in script


def test_wsu_script_host_paths(tmp_path):
    run_dir = _prepare(tmp_path, cluster="wsu")
    script = (run_dir / "submit_job.sh").read_text()
    assert f"#SBATCH -o {run_dir}/log/output_%A_%a.log" in script
    assert f'--job_dir "{run_dir}/${{JOB_DIR}}"' in script
    assert f'--main_config_path "{run_dir}/main_config.py"' in script
    assert f'--bind "{run_dir}"' in script
    # The repository may be the container's /app, which is not on the host
    assert ":/work" not in script


def test_wsu_script_container_paths(tmp_path):
    from src.cluster_submission import create_wsu_submission_script

    run_dir = tmp_path / "run"
    (run_dir / "job_0").mkdir(parents=True)
    args = argparse.Namespace(run_dir="/work/runs/run_wsu/")
    with patch("src.cluster_submission.os.path.abspath") as abspath, patch(
        "src.cluster_submission.Path.iterdir",
        return_value=iter([run_dir / "job_0"]),
    ), patch("builtins.open") as mock_open, patch(
        "src.cluster_submission.os.chmod"
    ):
        abspath.side_effect = lambda p: os.path.normpath(p)
        create_wsu_submission_script(args, _config())
    written = "".join(
        call.args[0]
        for call in mock_open.return_value.__enter__.return_value.write.call_args_list
    )
    assert '--job_dir "/work/runs/run_wsu/${JOB_DIR}"' in written
    assert '--main_config_path "/work/runs/run_wsu/main_config.py"' in written
    assert 'REPO_DIR=$(realpath "$SLURM_SUBMIT_DIR/../../")' in written
    assert "#SBATCH -o log/output_%A_%a.log" in written


def test_run_simulations_defaults_to_config_snapshots(tmp_path, monkeypatch):
    import run_simulations

    run_dir = tmp_path / "run"
    (run_dir / "job_0").mkdir(parents=True)
    monkeypatch.setattr(
        sys, "argv", ["run_simulations.py", "--job_dir", str(run_dir / "job_0")]
    )
    # snapshots missing -> clear error, exit code 1
    with pytest.raises(SystemExit) as excinfo:
        run_simulations.main()
    assert excinfo.value.code == 1

    (run_dir / "main_config.py").write_text("general = {}\n")
    (run_dir / "user_config.py").write_text("general = {}\n")
    with patch("run_simulations.load_config", return_value=None) as load_config:
        with pytest.raises(SystemExit):
            run_simulations.main()
    load_config.assert_called_once_with(
        str(run_dir / "main_config.py"), str(run_dir / "user_config.py")
    )
