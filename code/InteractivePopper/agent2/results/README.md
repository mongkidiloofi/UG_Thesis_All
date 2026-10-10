# Recorded experiments

These are the original Agent 2 development results, bundled with a standalone
refactoring of the implementation. Each public-game run began with an empty
learned theory and used the same agent code. There were no manual resets.

| Run | First level completed at action | Total actions | Completed levels | Final state |
| --- | ---: | ---: | ---: | --- |
| [LS20 seed 0](ls20_seed0/result.json) | **59** | 126 | 1 | Game over in level 2 |
| [LS20 seed 1](ls20_seed1/result.json) | **60** | 127 | 1 | Game over in level 2 |
| [FT09](ft09/result.json) | — | 80 | 0 | Action budget exhausted |
| [CN04](cn04/result.json) | — | 60 | 0 | Action budget exhausted |

[Machine-readable summary](summary.json) · [Watch LS20 level 1](ls20_seed0/level1.gif)

## What was learned

LS20 produced conditional bitmap rotation programs, followed by a candidate
progress predicate after the first successful level transition. The programs
were retained across levels. The bitmap rules were reused in level 2 without
additional pixel-program induction, but the agent did not clear that level.
The explicit learned-progress planning branch selected no actions in the public
LS20 level-2 runs: retaining a goal hypothesis did not establish effective transfer.

An example learned bitmap program, with variable names simplified:

```prolog
nextpixel(E,R,C) :- current(E,D,R), opposite(C,D), entered_has1(E).
nextpixel(E,R,C) :- current(E,R,C), entered_lacks1(E).
```

Given the arithmetic relation `C+D=N-1`, this applies clockwise rotation under
an observed entry condition. Popper was not given a named rotation operator.
The relevant colors co-occur, so these data do not establish which color is
causally necessary.

FT09 yielded a local inversion-and-persistence rule for one discovered region:

```prolog
nextpixel(E,R,C) :- absentpixel(E,R,C), local_click(E).
nextpixel(E,R,C) :- current(E,R,C), no_local_click(E).
```

Only two bitmap regions are modeled concurrently. These results do not establish
learning the complete state of either game.

## Prediction accuracy and coverage

Predictions were recorded before seeing each action's result. A bitmap prediction
is counted correct only when the entire registered region matches.

| Run | Correct position predictions | Correct bitmap predictions | Correct predictions on changing regions |
| --- | ---: | ---: | ---: |
| LS20 seed 0 | 113/119 | 166/168 | 12/14 |
| LS20 seed 1 | 115/120 | 162/164 | 6/8 |
| FT09 | No predictions | 110/113 | 1/2 |
| CN04 | No predictions | 0/1 | 0/1 |

Coverage is limited: LS20 seed 0 had 20 changes across registered regions, of
which 14 were predicted; seed 1 had 14 changes, with 8 predicted. FT09 had four,
with two predicted. Many unchanged regions make aggregate accuracy easier.
CN04's representation was inadequate. Positions include empirical action
displacements and optimistic fallbacks, so these scores do not isolate Popper's
contribution. No RL comparison or Popper ablation was run for Agent 2.

## Assumptions and interpretation

The runtime receives only grids, action IDs, and level counters. No explicit
LS20 rules, goal location, sprite template, or solution are supplied. However,
the developer already knew LS20 and adjusted the implementation while observing
public games. FT09 source was inspected during an earlier separate experiment.
Generic assumptions include connected components, translation, static-terrain
memory, small square bitmap regions, and normalized pattern equality.

Therefore these are **development-informed results**, not a blind or prior-free
evaluation. Earlier agent variants also failed LS20 level 1; the reported final
version was selected after those development failures. The two successful runs
use the same public layout, not two independent unseen games. There was no
competition-mode submission.

One goal example can support several correlated explanations. A learned progress
predicate is a hypothesis, and bounded planning in an incomplete model does not
guarantee an environment-shortest solution. Timers, life loss, and reset causes
remain inadequately modeled.

## Synthetic checks

[Synthetic results](synthetic/summary.json) record two-level corridor worlds in
original and recolored/rotated form. Both variants completed two levels, in 27
and 28 actions, and used the learned-progress planning branch in their second
level. These are integration/transfer fixtures, not ARC benchmark scores.

The test suite also checks rule withdrawal after contradictory evidence,
initially all-negative bitmap observations, learned click inversion, and pattern
normalization. Tests run entirely in temporary directories.

## Provenance and files

Each public-game directory contains:

- `result.json`: original metrics, hypotheses, and induction audits.
- `trace.json`: original action-by-action predictions and outcomes.
- `knowledge.pl`: the final learned programs.
- `learning/`: generated inputs and outputs of the agent's learning calls.
- `original_manifest.json`: hashes/configuration from the original implementation.

The `.pl` files in `learning/` are **experiment-generated facts, examples, bias,
and learned programs**. They are not a vendored copy of Popper. Upstream code,
downloaded game implementations, redundant raw recordings, and machine-specific
solver logs are omitted. The original source hashes identify the development
implementation before packaging; its source paths are historical identifiers.
Artifact folder references were changed to paths relative to each run directory.
Experimental metrics and action traces were preserved.

[environment.json](environment.json) records the experiment's dependency versions
and upstream commits. The local machine was an Intel i3-6100U with approximately
8 GB RAM. Final LS20 runs took about 28 and 27 seconds with concurrent evaluation
processes, so those times are not isolated hardware benchmarks.

## Standalone-package verification

The package was installed without copying the earlier agents or upstream source
trees into this repository. Importing it from outside the development workspace
loaded no `arcpopper` modules. All four tests pass, as do Ruff's lint/format checks.

A fresh local run of the standalone package reproduced **all 126 actions and
their prediction records exactly** from the original LS20 seed-0 trace, including
success at action 59. See [package_verification.json](package_verification.json)
for the recorded check and the source manifest from that run.

Existing installed upstream dependencies were reused for verification. An
editable package build was checked; a clean network installation of all upstream
dependencies was not repeated. Dependency acquisition is documented in the
[repository README](../README.md).
