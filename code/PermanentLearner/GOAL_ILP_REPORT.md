# Hidden-goal ILP experiment

This contribution is separate from the maze reproduction. It uses pure symbolic states and the pinned Popper v3.1.0 toolchain. No maze files were modified, and no counting or numeric goal template was attempted.

## Protocol

- Templates: unary color property and relational same-color adjacency.
- Seeds: 0--9 per template (`n=10`).
- Training pool: 60 shuffled states per seed, with at least 10 positive and 10 negative labels.
- Held-out pool: 100 fresh states from the same seed-specific generator distribution.
- Incremental loop: append one labelled state, check the current hypothesis against all examples seen so far, and re-run Popper only after a classification failure. The first induction waits until both labels are present because the pinned Popper tester cannot construct a task with only one class.
- `examples_to_convergence`: the last example index that triggered a changed hypothesis.
- `held_out_agreement`: fraction of held-out states classified correctly.

## Results

| Template | Convergence mean ± spread | Held-out agreement mean ± spread | Spurious runs | Syntactic matches |
|---|---:|---:|---:|---:|
| Unary property | 5.500 ± 3.905 | 1.000 ± 0.000 | 0/10 | 0/10 |
| Relational same-color adjacency | 3.400 ± 2.375 | 1.000 ± 0.000 | 0/10 | 10/10 |

The unary runs all agreed perfectly on held-out states, but Popper added a redundant typed `object/2` literal to the learned rule. This is semantically equivalent for the generated states, but it is correctly reported as non-identical syntax. The relational runs recovered the intended rule structure up to variable renaming and body-literal ordering.

No template was tuned after seeing the results, and no run was discarded. Both templates were degenerate in held-out accuracy for this generator: every run reached 100% agreement. The convergence episode/example counts still varied across seeds, but this experiment does not provide evidence of a held-out failure mode for either tested template.

## Artifacts

- [Experiment runner](</home/tasin/Documents/For Thesis/Final Thesis/SymbolicRL+Popper/goal_ilp_experiment.py>)
- [Unary summary](</home/tasin/Documents/For Thesis/Final Thesis/SymbolicRL+Popper/goal_results/unary/summary.json>)
- [Unary CSV](</home/tasin/Documents/For Thesis/Final Thesis/SymbolicRL+Popper/goal_results/unary/runs.csv>)
- [Relational summary](</home/tasin/Documents/For Thesis/Final Thesis/SymbolicRL+Popper/goal_results/relational/summary.json>)
- [Relational CSV](</home/tasin/Documents/For Thesis/Final Thesis/SymbolicRL+Popper/goal_results/relational/runs.csv>)

The unary template uses Popper-compatible typed unary color predicates (`red/1`, `blue/1`, etc.) as constants connected to the underlying `color/3` facts, because this Popper version does not directly enumerate constants as arguments of a ternary predicate. Its semantic target remains `color(S,X,target_color)`.
