# Portfolio Optimization Quantum

Portfolio optimization system using QUBO formulation with quantum-inspired (simulated annealing) and classical methods for stock selection and weight optimization.

## Main run commands

- Run complete phase pipeline:

```powershell
python run_portfolio_optimization_quantum.py
```

- Run everything end-to-end:

```powershell
python run_all_end_to_end.py
```

## GitHub-friendly repository hygiene

- Generated artifacts are ignored via `.gitignore` in this folder.
- Source code, configs, and docs remain tracked.
- Reproducible output can be regenerated using the run commands above.

## What is included

- Phase files in order: `phase_01` to `phase_07`
- Shared QUBO selector: `qubo_selector.py`
- Shared optimizer: `quantum/weight_optimizer.py`
- Configs:
  - `config/config.json`
  - `config/nifty100_sectors.json`
- Full process documentation in `docs/` folder
