# Utilities: checking, collecting, and analyzing simulation output

This directory contains small command-line utilities for inspecting and post-processing CRONOS simulation output.

## Typical workflow

### 0) Keep a record of input parameters

When preparing a run via `prepare_simulations.py`, CRONOS copies the user parameter file (`--user_config_path`) into the chosen run directory (`--run_dir`). This makes it easier to relate results to the input parameters later.

### 1) Validate per-event output files

CRONOS produces one HDF5 file per event, e.g.:

- `run/job_0/event_0.h5`
- `run/job_0/event_1.h5`

To check which events are complete (contain all required datasets), use:

```bash
python utilities/results_validate.py run/ --pattern 'run/job_*/event_*.h5'
```

Notes:
- Exit code `0`: all checked events are OK
- Exit code `2`: one or more events are missing required datasets
- You can override the required dataset list via `--required ...`

### 2) Inspect a single event file (optional)

To list datasets/attributes inside an event file (or extract a dataset), use:

```bash
python utilities/h5_extractor.py run/job_0/event_0.h5 --list
```

### 3) Collect many per-event files into one merged "database" HDF5

For analysis on large runs it's often convenient to store all events in a single file.

Build a merged database (recommended: validate first):

```bash
python utilities/event_database.py build \
  --pattern 'run/job_*/event_*.h5' \
  --out merged_events.h5 \
  --validate
```

To save disk space, you can delete per-event files after they were successfully copied:

```bash
python utilities/event_database.py build \
  --pattern 'run/job_*/event_*.h5' \
  --out merged_events.h5 \
  --validate \
  --delete-source
```

Database layout:
- `/job_<N>/event_<M>/<dataset_name>`

### 4) Prune unstable/broken events inside a merged database

If you already have a merged file and want to remove event groups missing required datasets:

```bash
python utilities/event_database.py prune merged_events.h5
```

Dry-run mode (no changes):

```bash
python utilities/event_database.py prune merged_events.h5 --dry-run
```

### 5) Combine multiple merged databases

To combine multiple merged files into one:

```bash
python utilities/event_database.py combine --out combined.h5 db1.h5 db2.h5
```

By default, name conflicts are resolved by renaming (suffix `__N`).

### 6) Optionally compute Qn vectors and basic yields

From per-event files:

```bash
python utilities/flow_qn_vectors.py run/ --pattern 'run/job_*/event_*.h5'
```

From a merged database:

```bash
# One event group
python utilities/flow_qn_vectors.py --db merged_events.h5 --group /job_0/event_0

# All event groups
python utilities/flow_qn_vectors.py --db merged_events.h5 --all-events
```

Outputs are written to `extracted_data/` by default:
- `Qn_vectors_<label>.dat`
- `particle_yield_and_meanpT_<label>.dat`

### 7) Optional centrality binning (event list generation)

This bins events by a multiplicity proxy (default: `Q0_real` at `n=0` from `particle_9999_vndata_eta_-0.5_0.5.dat`) and writes one list file per centrality bin:

```bash
python utilities/centrality_binning.py run/ \
  --pattern 'run/job_*/event_*.h5' \
  --cuts 0 5 10 20 30 40 50 60 70 80 90 100 \
  --out-dir centrality_bins
```

Optional: create per-bin folders containing symlinks or copies of the event files:

```bash
python utilities/centrality_binning.py run/ \
  --pattern 'run/job_*/event_*.h5' \
  --out-dir centrality_bins \
  --link symlink
```
