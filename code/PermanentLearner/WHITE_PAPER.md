# FastLearner: A Popper-Based Symbolic Reinforcement Learning System

## A plain-language account of the project

## Abstract

This project started from an older system called ILP(RL). ILP(RL) combines two ideas:

1. use Inductive Logic Programming (ILP) to learn how an environment changes after an action; and
2. use Answer Set Programming (ASP) to plan actions with the learned model.

The original system used ILASP as its ILP engine. We built a Popper-backed version of the same general idea. We call this version **FastLearner** in this project. The name is a project label; it is not a claim that Popper is always faster than ILASP or Q-learning.

We then tested FastLearner in two ways. First, we used the original repository's small maze and compared it with the unchanged Q-learning baseline. Second, we built three small interactive symbolic games in the spirit of hidden-goal discovery: a unary-property game, a relational game, and a compositional game. In those games, the agent was not told the goal rule. It had to learn the rule from symbolic states and goal-related action outcomes, then use the learned rule in an ASP planner.

The maze experiment shows that the Popper replacement works end to end. Under the current bounded harness, both Popper and Q-learning reached the optimal maze path in all 30 baseline seeds. The hidden-goal experiment achieved 100% held-out agreement and 100% planning success in all three controlled games across 10 seeds per game. These results demonstrate a working implementation, not a general claim that Popper is the best ILP system or that the method solves ARC-AGI-3.

## 1. What the project was trying to answer

The original ILP(RL) paper proposed a symbolic alternative to ordinary model-free reinforcement learning. Instead of learning only a table of action values, the agent learns a logical description of the environment's transition rules.

For example, in a maze, the agent may learn rules like:

```prolog
state_after(V0) :- adjacent(right,V0,V1),
                    state_before(V1),
                    action(right),
                    not wall(V0).
```

This means: if the agent is at `V1`, chooses `right`, and the next cell `V0` is not a wall, then the next state is `V0`.

Once the transition rules are known, an ASP solver can search for a short sequence of actions that reaches the goal.

Our first research question was:

> Can Popper replace ILASP as the induction engine while preserving the symbolic RL pipeline?

Our second, separate research question was:

> Can the same general symbolic learner discover a hidden goal concept from interaction when the state is already represented symbolically?

The second question is ARC-AGI-3-inspired only at the level of hidden objectives and interaction. It does not use ARC-AGI-3's 64×64 visual grid, API, or game platform.

## 2. The original ILP(RL) system

The original code is preserved in [`symbolic-rl/`](symbolic-rl/). It uses:

- an old py-vgdl maze environment wrapped in OpenAI Gym;
- ILASP2i for induction;
- Clingo for ASP planning; and
- Q-learning as a comparison baseline.

The original loop is:

```text
observe maze state
    -> choose an action
    -> execute action
    -> observe the next state and nearby walls
    -> create a context-dependent ILASP example
    -> check whether the current hypothesis covers it
    -> call ILASP if the hypothesis fails
    -> convert the learned transition rules into planner rules
    -> ask Clingo for an action plan
    -> continue interacting
```

The examples given to ILASP are not ordinary global positive and negative facts. They are context-dependent partial interpretations, usually written as:

```prolog
#pos({state_after(Target)},
     {state_after(WrongState)},
     {state_before(Source). action(Direction). wall(Wall)}).
```

The context matters. Facts from one transition must not accidentally explain another transition. This context issue became the most important part of the Popper replacement.

The original repository also contains a transfer-learning path. It can begin with an existing transition hypothesis and adapt it while interacting with another maze.

## 3. Phase 0: checking the legacy dependencies

Before changing the learning engine, we checked the three risky dependencies separately.

### The maze environment

The embedded py-vgdl environment could be made to run on the modern machine. It needed compatibility handling for the old Gym API, NumPy aliases, Pygame constants, and related legacy behavior. The original environment source was not rewritten to make the new research result look better.

The smallest original maze, `aaa_small`, could be reset, stepped, and solved.

### ILASP2i

The old ILASP2i binary could be launched after adding compatibility libraries. However, the real context-dependent symbolic-rl task failed with a `Poco::WriteFileException` in this environment. Therefore, we did not claim to have regenerated new ILASP comparison numbers.

For ILASP, the original paper's published numbers remain the reference point. The original ILASP path remains in the repository as a reference implementation.

### Popper

Popper was made to run independently on its own examples. The working checkout is Popper v3.1.0 at commit `227c30f`, with the small compatibility change documented in [`PHASE2_REPORT.md`](PHASE2_REPORT.md).

This separation matters: the maze-engine problem and the old-ILASP problem were not treated as if they were the same failure.

## 4. Phase 1: understanding the data flow

We traced the original code before writing the adapter. The detailed mapping is in [`PHASE1_MAPPING.md`](PHASE1_MAPPING.md).

The important boundaries were:

- [`symbolic-rl/main.py`](symbolic-rl/main.py) runs the main no-transfer ILP(RL) loop.
- [`symbolic-rl/lib/induction.py`](symbolic-rl/lib/induction.py) discovers walls, creates ILASP examples, checks coverage, and invokes ILASP.
- [`symbolic-rl/lib/py_asp.py`](symbolic-rl/lib/py_asp.py) converts a learned transition hypothesis into planner vocabulary.
- [`symbolic-rl/lib/abduction.py`](symbolic-rl/lib/abduction.py) builds and runs the Clingo planner.
- [`symbolic-rl/q_learning.py`](symbolic-rl/q_learning.py) is the independent Q-learning baseline.

The safe replacement point was therefore the induction boundary. The environment, rewards, Q-learning code, and planner semantics were kept separate from Popper internals.

## 5. Phase 2: replacing ILASP with Popper

The replacement backend is [`symbolic-rl/lib/popper_backend.py`](symbolic-rl/lib/popper_backend.py). Its main interface is:

```python
learn_transition_hypothesis(...) -> str
convert_popper_hypothesis_to_planner(hypothesis) -> str
```

The first function learns a transition hypothesis. The second checks and projects that hypothesis into the syntax expected by the existing ASP planner.

### How the translation works

Popper and ILASP do not use exactly the same example format. We therefore did not put all ILASP contexts into one undifferentiated background file.

Instead, each example receives a private context identifier:

```prolog
state_before(c0,cell(1,4)).
step_right(c0,cell(2,4),cell(1,4)).
wall(c0,cell(2,5)).
open(c0,cell(2,4)).
pos(transition(c0,cell(2,4))).
```

This preserves the fact that `c0` belongs to one particular transition example.

The adapter also handles two differences between the systems:

- ILASP can tie an action constant such as `right` to an adjacency literal. Popper's ordinary bias does not express that equality in exactly the same way, so the adapter uses direction-specific predicates such as `step_right/3`.
- The original hypothesis uses `not wall(...)`. The working Popper path constructs a finite `open/2` complement for the relevant cell range and projects it back to the planner's wall semantics.

These are controlled translations of the original task, not claims that Popper and ILASP have identical internal search spaces.

### End-to-end smoke test

The standalone test is [`symbolic-rl/phase2_smoke.py`](symbolic-rl/phase2_smoke.py). It loads the original `aaa_small` maze, gathers transitions, runs Popper, converts the result, calls Clingo, executes the plan, and reaches the goal.

Observed smoke-test result:

- 7 reachable states;
- 28 transition examples;
- 8 learned transition rules;
- 0 false negatives and 0 false positives on the checked transitions;
- 7 executed actions; and
- the goal reached at `(5,1)`.

This verified that Popper could fill ILASP's role in the actual symbolic maze loop.

## 6. Phase 3: maze comparison

The main experiment runner is [`run_experiment.py`](run_experiment.py).

The Q-learning implementation was not changed to help Popper. The updated runner records the full per-episode training sequence for both methods. For Popper, transition collection is incremental: after each new transition, the current hypothesis is checked, and Popper is called again only when that hypothesis no longer covers the observed example.

The baseline used:

- `aaa_small`;
- 30 seeds;
- 100 episodes per run;
- 250 steps per episode; and
- the original four maze actions and reward convention.

### Current baseline result

| Measure | FastLearner / Popper | Q-learning |
|---|---:|---:|
| Seeds | 30 | 30 |
| Final success rate | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Final mean reward | 4.000 ± 0.000 | 4.000 ± 0.000 |
| Final mean steps | 7.000 ± 0.000 | 7.000 ± 0.000 |
| Episodes to convergence / final-policy match | 1.267 ± 0.512 | 6.933 ± 1.123 |
| Mean Popper induction calls | 4.600 ± 0.712 | — |

The last row is not a perfect apples-to-apples metric. For Popper, `episodes_to_convergence` means the episode in which the hypothesis last changed. For Q-learning, `episodes_to_optimal_policy` means the first recorded evaluation matching the final greedy policy. Both training curves are retained in each run's JSON, so they can be compared more carefully.

The honest conclusion is that the current harness shows equal final maze performance. It does not prove that FastLearner is better than Q-learning, and it does not reproduce a fresh ILASP comparison.

The original paper reported a sample-efficiency pattern of approximately 40 episodes for ILASP versus approximately 60 for Q-learning. We preserve that as a published reference, not as a newly reproduced number.

### Transfer experiment

The transfer experiment trained on `aaa_small` and evaluated on the available `experiment3_after` maze for five seeds. All five runs reached the goal with a 21-step plan. The reward was `-10` under the existing reward convention.

This is not claimed to be the paper's exact transfer pairing. The registered `aaa_medium` environment referred to a missing level file, so the available similar maze was used and documented.

## 7. The separate hidden-goal games

The hidden-goal benchmark is implemented in [`hidden_goal_experiment.py`](hidden_goal_experiment.py). It does not modify the original maze experiment.

The games are small deterministic line-worlds with symbolic observations. An observation contains facts such as:

```prolog
object(State, Object).
object_color(State, Object, Color).
adjacent(State, Object1, Object2).
```

The agent sees these facts and the outcome of its left/right action. It does not receive the hidden `goal/1` definition.

The environment uses its private goal check only to generate the terminal/reward outcome. The learning code receives the accumulated labelled state examples, asks Popper to learn `goal/1`, validates the rule on held-out states, and gives the learned rule to an ASP planner.

### The three games

1. **Unary game**: a state is a goal state when it contains a red object.
2. **Relational game**: a state is a goal state when adjacent objects have the same color.
3. **Compositional game**: a red object must be adjacent to a blue object.

The learner receives no game-specific goal rule. The same general typed Popper bias is used across the games.

### Results

Ten seeds were run for each game.

| Game | Held-out agreement | Held-out precision | Held-out recall | Planning success |
|---|---:|---:|---:|---:|
| Unary | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |
| Relational | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |
| Compositional | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 |

Mean examples to convergence were 2.5 for the unary game, 5.6 for the relational game, and 5.6 for the compositional game.

The relational rule was syntactically identical to the intended rule in all 10 runs. The unary and compositional rules were sometimes written differently, but agreed with the hidden rule on every held-out state. This is a useful distinction: logical equivalence on the tested data is not the same as identical text.

The benchmark is intentionally controlled and small. Its perfect held-out scores are evidence that the pipeline works on these generated distributions, not evidence that hidden-goal discovery is solved in general.

## 8. What the results do and do not mean

### What was demonstrated

- Popper can replace ILASP at the transition-learning boundary for the ordinary maze task.
- A Popper hypothesis can be projected into an ASP planner and used to reach a real maze goal.
- FastLearner and unchanged Q-learning both solve the tested deterministic maze under the current 30-seed harness.
- Popper can learn three hidden symbolic goal concepts from interaction-generated examples and use them for planning in controlled games.

### What was not demonstrated

- We did not rerun the original ILASP2i task successfully.
- We did not prove that Popper is generally faster or better than ILASP.
- We did not prove that Popper is generally better than Q-learning.
- We did not implement ARC-AGI-3 perception, 64×64 visual reasoning, or the real ARC API.
- We did not test a large variety of games or a counting/numeric hidden goal.
- We did not claim the transfer experiment is an exact reproduction of the paper's unavailable `aaa_medium` pairing.

## 9. Final conclusion

The project produced a working Popper-backed symbolic RL system. In the original maze setting, FastLearner preserves the central ILP(RL) idea: learn a symbolic transition model, compile it into ASP, and plan with Clingo. In the separate hidden-goal benchmark, it shows that the same style of symbolic induction can discover simple unary, relational, and compositional goals from interaction-derived examples.

The strongest defensible thesis statement is therefore:

> Popper can serve as a practical induction backend for this symbolic RL architecture, and it can learn the tested hidden symbolic goals well enough to support ASP planning. The current experiments do not establish a universal performance advantage over ILASP or Q-learning.
