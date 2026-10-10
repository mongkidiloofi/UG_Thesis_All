# Interactive hidden-goal induction report

Three deterministic symbolic line-world games were run. The agent received symbolic state facts and action outcomes, but not the true goal rule. Popper induced `goal/1` incrementally, and the learned rule was inserted into a Clingo ASP planner.

| Game | Seeds | Convergence examples | Held-out agreement | Precision | Recall | Planning success |
|---|---:|---:|---:|---:|---:|---:|
| unary | 10 | 2.500 ± 0.500 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |
| relational | 10 | 5.600 ± 4.964 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |
| compositional | 10 | 5.600 ± 4.176 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |

All three games use interaction for data collection and a separate held-out interaction pass for validation. No ARC-AGI-3 perception or API is involved. No counting/numeric goal was attempted.

The planner receives the learned goal rule together with observed symbolic facts and deterministic transition outcomes. The environment's hidden goal predicate is used only for reward/terminal outcomes and final success verification.


## unary

Representative Popper rule: `goal(A):- object(A,C),object_color(A,C,B),red(B).`
Mean training/held-out examples: 25.300 ± 1.792 / 27.300 ± 0.781
Mean induction calls/time: 1.000 ± 0.000 / 0.2334 ± 0.0149 s
Mean planning time/plan length: 0.0451 ± 0.0021 s / 3.000 ± 0.000 actions
Representative executed plan: `right, right, right`
Syntactically identical to the environment rule: 0/10 seeds
Failures: 0/10 (none)

## relational

Representative Popper rule: `goal(A):- adjacent(A,C,B),object_color(A,B,D),object_color(A,C,D).`
Mean training/held-out examples: 26.300 ± 1.952 / 29.900 ± 0.943
Mean induction calls/time: 1.000 ± 0.000 / 0.2288 ± 0.0113 s
Mean planning time/plan length: 0.0442 ± 0.0030 s / 6.000 ± 0.000 actions
Representative executed plan: `right, right, right, right, right, right`
Syntactically identical to the environment rule: 10/10 seeds
Failures: 0/10 (none)

## compositional

Representative Popper rule: `goal(A):- adjacent(A,D,B),object_color(A,B,C),blue(C),adjacent(A,B,D).`
Mean training/held-out examples: 28.900 ± 2.300 / 26.000 ± 0.775
Mean induction calls/time: 1.000 ± 0.000 / 0.2682 ± 0.0130 s
Mean planning time/plan length: 0.0430 ± 0.0012 s / 4.000 ± 0.000 actions
Representative executed plan: `right, right, right, right`
Syntactically identical to the environment rule: 0/10 seeds
Failures: 0/10 (none)

Per-game machine-readable outputs are in `results/hidden_goal/<game>/`; the combined run table is `results/hidden_goal_results.csv`.
