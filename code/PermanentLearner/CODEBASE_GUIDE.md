# FastLearner Codebase Guide

This guide is for someone opening the repository for the first time.

The repository contains two related experiments:

1. a Popper replacement for the original ILASP(RL) maze system; and
2. a separate hidden-goal benchmark with three small symbolic interactive games.

The original ILASP implementation is kept beside the Popper implementation.

## 1. Directory map

```text
SymbolicRL+Popper/
├── symbolic-rl/                 Original ILP(RL) repository and maze code
│   ├── main.py                  Original no-transfer ILASP loop
│   ├── q_learning.py            Original Q-learning baseline
│   ├── tl.py                    Original transfer-learning path
│   ├── noTL_goal.py             Original known-goal path
│   ├── lib/
│   │   ├── induction.py         ILASP examples, coverage, ILASP invocation
│   │   ├── py_asp.py            Hypothesis conversion and action encoding
│   │   ├── abduction.py         Clingo planner construction and execution
│   │   ├── helper.py            Environment and logging helpers
│   │   └── popper_backend.py    New ILASP-to-Popper transition adapter
│   ├── las_base.las             Original ILASP bias and background rules
│   ├── tl_pos.las               Transfer-task file
│   ├── report.pdf               Original paper/report; historical reference
│   ├── phase2_smoke.py          Popper end-to-end maze smoke test
│   └── README.md                Original project README
├── Popper/                      Pinned Popper checkout
├── run_experiment.py            Maze comparison and transfer CLI
├── hidden_goal_experiment.py    Three-game interactive hidden-goal benchmark
├── goal_ilp_experiment.py       Earlier two-template synthetic goal experiment
├── PHASE1_MAPPING.md            Detailed original data-flow and format mapping
├── PHASE2_REPORT.md              Popper adapter design and smoke-test result
├── PHASE3_REPORT.md              Maze comparison/transfer notes
├── GOAL_ILP_REPORT.md            Earlier two-template goal experiment report
├── results/                     Current hidden-goal CSV and Markdown report
└── phase3_results/              Maze experiment JSON/CSV outputs
```

## 2. Which experiment should I run?

| Goal | Entry point |
|---|---|
| Test Popper on the original maze pipeline | `symbolic-rl/phase2_smoke.py` |
| Compare FastLearner with Q-learning | `run_experiment.py` |
| Run the transfer experiment | `run_experiment.py --experiment transfer` |
| Run the three hidden-goal games | `hidden_goal_experiment.py` |
| Inspect the original ILASP system | `symbolic-rl/main.py`, `symbolic-rl/lib/induction.py`, and `symbolic-rl/las_base.las` |

The old ILASP path is a reference path. It is not silently redirected to Popper.

## 3. Runtime setup

The code depends on old software:

- Python 3;
- the embedded py-vgdl engine;
- OpenAI Gym compatibility behavior;
- Clingo;
- SWI-Prolog for Popper; and
- the pinned Popper checkout.

On the validated machine, the working runtime paths are:

```text
SWI-Prolog: /tmp/swi-root/usr/bin
SWI libraries: /tmp/swi-root/usr/lib/x86_64-linux-gnu
SWI home: /tmp/swi-root/usr/lib/swi-prolog
Popper Python path: /tmp/popper-pkgs
Popper checkout: <project>/Popper
```

The exact paths may differ on another machine. The important point is that `swipl`, its shared library, Clingo, and Popper must all be available together.

## 4. The original maze system

### Environment

The original environment is a small deterministic grid maze. The agent has four actions:

| Action | Meaning |
|---|---|
| `up` | decrease y |
| `down` | increase y |
| `left` | decrease x |
| `right` | increase x |

The original reward convention is:

- `-1` for a non-terminal step;
- `+10` for reaching the goal.

The original time horizon is 250 steps.

### Original files

`symbolic-rl/main.py` is the main no-transfer loop. It collects transitions, asks ILASP to learn, inserts the learned transition model into a Clingo program, and executes planned actions.

`symbolic-rl/lib/induction.py` is the original induction layer. It creates context-dependent examples and invokes ILASP through a subprocess.

`symbolic-rl/lib/py_asp.py` converts the learned transition vocabulary into planner vocabulary.

`symbolic-rl/lib/abduction.py` builds the ASP planning program and parses Clingo's answer set.

`symbolic-rl/q_learning.py` is the baseline. It was intentionally left unchanged by the Popper work.

`symbolic-rl/tl.py` and `symbolic-rl/noTL_goal.py` contain the original transfer and known-goal paths.

### Original ILASP data format

The main input is a sequence of context-dependent partial interpretations:

```prolog
#pos({state_after((2,3))},
     {},
     {state_before((1,3)).
      action(right).
      wall((0,3)).}).
```

The three parts mean:

1. states that should be included;
2. states that should be excluded; and
3. facts that describe this particular context.

Do not merge the contexts into one global example set without reification. That changes the learning problem.

## 5. FastLearner's maze path

The Popper adapter is [`symbolic-rl/lib/popper_backend.py`](symbolic-rl/lib/popper_backend.py).

Its conceptual flow is:

```text
maze transition
  -> ILASP-style CDPI
  -> context-reified Popper facts and pos/neg examples
  -> Popper transition hypothesis
  -> checked planner projection
  -> Clingo ASP plan
  -> maze action
```

The adapter uses private context identifiers such as `c0` and `c1`. It also uses direction-specific background predicates such as `step_right/3`, because the original ILASP mode declarations tie action constants and adjacency directions together more tightly than the ordinary Popper bias does.

The original `not wall(...)` behavior is represented during induction by a finite `open/2` complement and projected back into the planner form. This is why the adapter is a semantic compiler rather than a simple text substitution.

### Important API boundary

```python
learn_transition_hypothesis(
    examples,
    background_knowledge,
    bias,
    *,
    popper_root=None,
    output_dir=None,
    timeout=120,
) -> str

convert_popper_hypothesis_to_planner(hypothesis) -> str
```

The rest of the maze path should depend on these boundaries, not on Popper's internal modules.

## 6. Running the maze smoke test

From the `symbolic-rl` directory:

```bash
cd symbolic-rl
PATH=/tmp/swi-root/usr/bin:$PATH \
LD_LIBRARY_PATH=/tmp/swi-root/usr/lib/x86_64-linux-gnu \
SWI_HOME_DIR=/tmp/swi-root/usr/lib/swi-prolog \
PYTHONPATH=/tmp/popper-pkgs:/home/tasin/Documents/For\ Thesis/Final\ Thesis/SymbolicRL+Popper/Popper \
python3 phase2_smoke.py --output-dir /tmp/symbolic-rl-phase2
```

The smoke test should learn the ordinary four-direction transition model and reach the goal in `aaa_small`.

## 7. Running the maze comparison

From the project root:

```bash
PATH=/tmp/swi-root/usr/bin:$PATH \
LD_LIBRARY_PATH=/tmp/swi-root/usr/lib/x86_64-linux-gnu \
SWI_HOME_DIR=/tmp/swi-root/usr/lib/swi-prolog \
PYTHONPATH=/tmp/popper-pkgs:/home/tasin/Documents/For\ Thesis/Final\ Thesis/SymbolicRL+Popper/Popper \
python3 run_experiment.py \
  --backend popper \
  --experiment baseline \
  --seed 0 \
  --runs 30 \
  --episodes 100 \
  --steps 250 \
  --output-dir phase3_results
```

Run the unchanged Q-learning control with:

```bash
python3 run_experiment.py \
  --backend q_learning \
  --experiment baseline \
  --seed 0 \
  --runs 30 \
  --episodes 100 \
  --steps 250 \
  --output-dir phase3_results
```

Run the available transfer experiment with:

```bash
PATH=/tmp/swi-root/usr/bin:$PATH \
LD_LIBRARY_PATH=/tmp/swi-root/usr/lib/x86_64-linux-gnu \
SWI_HOME_DIR=/tmp/swi-root/usr/lib/swi-prolog \
PYTHONPATH=/tmp/popper-pkgs:/home/tasin/Documents/For\ Thesis/Final\ Thesis/SymbolicRL+Popper/Popper \
python3 run_experiment.py \
  --backend popper \
  --experiment transfer \
  --seed 0 \
  --runs 5 \
  --episodes 100 \
  --steps 250 \
  --output-dir phase3_results
```

The Popper sweep uses isolated child processes. This is intentional: SWI-Prolog can retain consulted predicates globally, so running multiple Popper tasks in one process can cause predicate redefinition problems.

### Maze output files

Each run writes a JSON file such as:

```text
phase3_results/baseline/popper/seed_0/result.json
```

The important fields include:

- `training_by_episode`: reward, success, and step count for every training episode;
- `episodes_to_convergence`: the last episode that triggered Popper re-induction;
- `induction_calls`: number of Popper calls;
- `induction_seconds`: total induction time;
- `planner_plan_steps`: final plan length;
- `evaluation_success_rate`: final greedy/fixed-plan success; and
- `contextual_hypothesis` and `planner_hypothesis`: the learned and projected programs.

Q-learning has the analogous `training_by_episode` and `episodes_to_optimal_policy` fields. The two episode metrics should not be described as identical measurements: one measures hypothesis stability, while the other measures a final-policy match.

## 8. The hidden-goal benchmark

The current three-game benchmark is [`hidden_goal_experiment.py`](hidden_goal_experiment.py).

It defines exactly three games:

```python
GAME_TYPES = {
    "unary": UnaryGoalGame,
    "relational": RelationalGoalGame,
    "compositional": CompositionalGoalGame,
}
```

Each game is deterministic. The random seed controls the exploration order, not the state-transition mechanics.

### What the agent sees

The agent observes symbolic facts, including:

```prolog
object(State, Object).
object_color(State, Object, Color).
adjacent(State, Object1, Object2).
```

The agent also receives the result of `left` or `right`. It is not given the private `_hidden_goal` function or the reporting-only `true_rule` string.

### Training and induction loop

The runner:

1. interacts with training variants;
2. stores unique labelled states;
3. shuffles the examples using the seed;
4. waits until both positive and negative examples exist;
5. checks whether the current Popper rule still classifies every example seen so far;
6. reruns Popper only when coverage fails;
7. checks agreement on held-out variants;
8. builds a fresh transition graph for planning; and
9. inserts the learned `goal/1` rule into a Clingo planner and executes the plan.

The environment's hidden check is used for reward and final success verification. It is not inserted into the Popper task or planner.

The planner in this script is a small generic symbolic-state ASP planner. The original maze planner is specialized to coordinate transitions, so this benchmark supplies a matching symbolic-state planner rather than changing the maze planner.

### Run all three games

From the project root:

```bash
PATH=/tmp/swi-root/usr/bin:$PATH \
LD_LIBRARY_PATH=/tmp/swi-root/usr/lib/x86_64-linux-gnu \
SWI_HOME_DIR=/tmp/swi-root/usr/lib/swi-prolog \
PYTHONPATH=/tmp/popper-pkgs:/home/tasin/Documents/For\ Thesis/Final\ Thesis/SymbolicRL+Popper/Popper \
python3 hidden_goal_experiment.py --seeds 10 --output-dir results
```

### Hidden-goal output files

The combined files are:

- [`results/hidden_goal_results.csv`](results/hidden_goal_results.csv)
- [`results/HIDDEN_GOAL_REPORT.md`](results/HIDDEN_GOAL_REPORT.md)

Per-game files are under:

```text
results/hidden_goal/unary/
results/hidden_goal/relational/
results/hidden_goal/compositional/
```

Each game directory contains:

- `bias.pl`: the typed Popper bias;
- `seed_N.json`: one complete run;
- `runs.csv`: per-seed tabular data; and
- `summary.json`: mean and population standard deviation.

The JSON/CSV data include training-example counts, held-out counts, learned rule, true rule for analysis, agreement, precision, recall, induction calls and time, planning time, plan actions, plan length, success, and failure reason.

## 9. Earlier synthetic goal experiment

[`goal_ilp_experiment.py`](goal_ilp_experiment.py) is an earlier two-template synthetic experiment. It is useful for understanding the first hidden-goal prototype, but it is not the current three-game interactive benchmark.

Its report is [`GOAL_ILP_REPORT.md`](GOAL_ILP_REPORT.md).

The current benchmark should be run through `hidden_goal_experiment.py` when reproducing the final hidden-goal contribution.

## 10. Common pitfalls

### Do not confuse the two research questions

The maze experiment learns a **transition model** such as `state_after/1` or `transition/2` and plans to a known maze goal.

The hidden-goal experiment learns a **goal predicate** such as `goal/1` and then plans to states satisfying that learned predicate.

They share Popper and ASP ideas, but they are separate experiments.

### Do not call the hidden benchmark ARC-AGI-3 itself

It is a controlled symbolic benchmark inspired by hidden goals and interaction. It has no visual perception, no 64×64 grid, and no ARC-AGI-3 API.

### Do not treat the ILASP reference as a new rerun

The old ILASP binary launches but fails on the real task with `Poco::WriteFileException` in this environment. Use the published paper/report numbers as reference only.

### Do not overwrite the baseline

`symbolic-rl/q_learning.py` is the baseline implementation. If you change it, you are no longer running the same comparison.

### Do not compare convergence metrics without reading their definitions

Popper's `episodes_to_convergence` measures when the learned hypothesis last changed. Q-learning's `episodes_to_optimal_policy` measures when an evaluation first matched the final policy. Keep the per-episode curves when making a stronger sample-efficiency claim.

### Keep Popper runs isolated

Popper consults Prolog files. A fresh process per run avoids cross-run predicate contamination.

## 11. Suggested reading order

For a quick understanding:

1. [`WHITE_PAPER.md`](WHITE_PAPER.md)
2. [`PHASE1_MAPPING.md`](PHASE1_MAPPING.md)
3. [`PHASE2_REPORT.md`](PHASE2_REPORT.md)
4. [`symbolic-rl/lib/popper_backend.py`](symbolic-rl/lib/popper_backend.py)
5. [`run_experiment.py`](run_experiment.py)
6. [`hidden_goal_experiment.py`](hidden_goal_experiment.py)
7. the generated result files

For the original research context, read [`symbolic-rl/README.md`](symbolic-rl/README.md) and [`symbolic-rl/report.pdf`](symbolic-rl/report.pdf).

