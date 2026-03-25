# Portfolio Optimization Quantum

Combined project built by copying and aligning code from:
- enhanced_quantum_portfolio
- crash_analysis_real

This folder keeps both functionalities with one ordered phase methodology and one custom comparison runner for horizon and crash evaluations.

## Main run commands

- Run everything end-to-end in one command:

```powershell
python run_all_end_to_end.py
```

- Run core phase pipeline:

```powershell
python run_portfolio_optimization_quantum.py
```

- Run crash-only flow:

```powershell
python run_crash_analysis_wrapper.py
```

- Run unified train/test + crash comparison:

```powershell
python unified_train_test_compare.py --only all
```

- Run unified comparison with explicit universe mode:

```powershell
python unified_train_test_compare.py --only all --universe-mode full_universe
python unified_train_test_compare.py --only all --universe-mode nifty100_only
```

## Defaults

- Default unified mode is set to `full_universe` in `config/unified_compare_config.json`.
- Override mode per run with `--universe-mode` when needed.

## GitHub-friendly repository hygiene

- Generated artifacts are ignored via `.gitignore` in this folder.
- Source code, configs, and docs remain tracked.
- Reproducible output can be regenerated using the run commands above.

## What is included

- Phase files in order: `phase_01` to `phase_08`
- Shared QUBO selector: `qubo_selector.py`
- Shared optimizer: `quantum/weight_optimizer.py`
- Configs:
  - `config/config.json`
  - `config/enhanced_evaluation_config.json`
  - `config/unified_compare_config.json`
- Full process documentation:
  - `docs/MASTER_PHASES_CALCULATIONS_GUIDE.md`
  - `docs/PROCESS_GUIDE.md`
  - `docs/CALCULATION_A_TO_Z.md`
- Source mapping and references:
  - `references_used/FILE_MAPPING.md`
  - `references_used/REFERENCE_METHOD_NOTES.md`

## Dataset policy

Unified comparison prioritizes the best data from local project paths first:
1. `Dataset/prices_timeseries_complete.csv`
2. fallback files in `data/`

The selected dataset is validated and printed in every run.
