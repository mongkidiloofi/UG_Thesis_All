"""Interactive hidden-goal induction benchmark.

Three small deterministic symbolic games are implemented here rather than in
the maze environment.  The agent sees symbolic observations and action
outcomes, but never receives the environment's goal definition.  Popper learns
``goal/1`` incrementally; the learned rule is then inserted into a small ASP
planner and executed in a fresh game variant.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Sequence, Tuple

import goal_ilp_experiment as goal_ilp


ROOT = Path(__file__).resolve().parent
POPPER_ROOT = ROOT / "Popper"
COLORS = ("red", "blue", "green", "yellow")
ACTIONS = ("left", "right")


@dataclass(frozen=True)
class GameObservation:
    state_id: str
    facts: Tuple[Tuple[str, Tuple[str, ...]], ...]


class HiddenGoalGame:
    """Base class for deterministic line-world symbolic games."""

    game_name = "base"
    max_position = 6

    def __init__(self, variant: int):
        self.variant = variant
        self.position = 0

    def reset(self) -> GameObservation:
        self.position = 0
        return self.observe()

    def observe(self) -> GameObservation:
        state_id = f"{self.game_name}_v{self.variant}_p{self.position}"
        return GameObservation(state_id, self._facts(state_id))

    def step(self, action: str):
        if action not in ACTIONS:
            raise ValueError(action)
        if action == "left":
            self.position = max(0, self.position - 1)
        else:
            self.position = min(self.max_position, self.position + 1)
        observation = self.observe()
        reached = self._hidden_goal(observation)
        reward = 10 if reached else -1
        return observation, reward, reached, {"goal_reached": reached}

    def _facts(self, state_id: str):
        raise NotImplementedError

    def _hidden_goal(self, observation: GameObservation) -> bool:
        raise NotImplementedError


def _facts(state_id: str, objects: Sequence[str], colors: Dict[str, str], adjacent: Sequence[Tuple[str, str]]):
    facts = [("object", (state_id, obj)) for obj in objects]
    facts.extend(("object_color", (state_id, obj, colors[obj])) for obj in objects)
    facts.extend(("adjacent", (state_id, left, right)) for left, right in adjacent)
    return tuple(facts)


def _facts_by_predicate(observation: GameObservation, predicate: str):
    return [args for name, args in observation.facts if name == predicate]


class UnaryGoalGame(HiddenGoalGame):
    game_name = "unary"

    def _facts(self, state_id: str):
        # The red-object location varies by variant.  The environment knows
        # this through its hidden predicate; the learner sees only these facts.
        target = (self.variant * 2 + 2) % (self.max_position + 1)
        token_color = "red" if self.position == target else COLORS[(self.position + self.variant) % 3 + 1]
        return _facts(state_id, ("token", "marker"), {"token": token_color, "marker": "green"}, ())

    def _hidden_goal(self, observation: GameObservation) -> bool:
        return any(args[2] == "red" for args in _facts_by_predicate(observation, "object_color"))


class RelationalGoalGame(HiddenGoalGame):
    game_name = "relational"

    def _facts(self, state_id: str):
        target = (self.variant * 3 + 1) % (self.max_position + 1)
        if self.position == target:
            colors = {"left_obj": "red", "right_obj": "red", "spectator": "green"}
            adjacent = (("left_obj", "right_obj"), ("right_obj", "left_obj"))
        elif self.position % 2 == 0:
            colors = {"left_obj": "red", "right_obj": "blue", "spectator": "green"}
            adjacent = (("left_obj", "right_obj"), ("right_obj", "left_obj"))
        else:
            colors = {"left_obj": "red", "right_obj": "red", "spectator": "green"}
            adjacent = (("left_obj", "spectator"), ("spectator", "left_obj"))
        return _facts(state_id, tuple(colors), colors, adjacent)

    def _hidden_goal(self, observation: GameObservation) -> bool:
        colors = {args[1]: args[2] for args in _facts_by_predicate(observation, "object_color")}
        return any(
            colors.get(left) == colors.get(right)
            for _state, left, right in _facts_by_predicate(observation, "adjacent")
        )


class CompositionalGoalGame(HiddenGoalGame):
    game_name = "compositional"

    def _facts(self, state_id: str):
        target = (self.variant * 2 + 3) % (self.max_position + 1)
        if self.position == target:
            colors = {"red_obj": "red", "blue_obj": "blue", "other": "green"}
            adjacent = (("red_obj", "blue_obj"), ("blue_obj", "red_obj"))
        elif self.position % 3 == 0:
            colors = {"red_obj": "red", "blue_obj": "green", "other": "blue"}
            adjacent = (("red_obj", "blue_obj"), ("blue_obj", "red_obj"))
        else:
            colors = {"red_obj": "green", "blue_obj": "blue", "other": "red"}
            adjacent = (("red_obj", "other"), ("other", "red_obj"))
        return _facts(state_id, tuple(colors), colors, adjacent)

    def _hidden_goal(self, observation: GameObservation) -> bool:
        colors = {args[1]: args[2] for args in _facts_by_predicate(observation, "object_color")}
        adjacent = _facts_by_predicate(observation, "adjacent")
        return any(
            colors.get(left) == "red"
            and colors.get(right) == "blue"
            for _state, left, right in adjacent
        )


GAME_TYPES = {
    "unary": UnaryGoalGame,
    "relational": RelationalGoalGame,
    "compositional": CompositionalGoalGame,
}


def _write_bias(path: Path) -> None:
    path.write_text(
        """head_pred(goal,1).
body_pred(object,2).
body_pred(object_color,3).
body_pred(adjacent,3).
body_pred(red,1).
body_pred(blue,1).
body_pred(green,1).
body_pred(yellow,1).

type(goal,(state,)).
type(object,(state,obj)).
type(object_color,(state,obj,colour)).
type(adjacent,(state,obj,obj)).
type(red,(colour,)).
type(blue,(colour,)).
type(green,(colour,)).
type(yellow,(colour,)).

direction(goal,(in,)).
direction(object,(in,out)).
direction(object_color,(in,in,out)).
direction(adjacent,(in,out,out)).
direction(red,(in,)).
direction(blue,(in,)).
direction(green,(in,)).
direction(yellow,(in,)).

max_body(5).
max_vars(5).
max_clauses(1).
"""
    )


def _write_task(task_dir: Path, examples: Sequence[goal_ilp.LabelledState], bias_path: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    facts = [
        "object(_,_) :- fail.",
        "object_color(_,_,_) :- fail.",
        "adjacent(_,_,_) :- fail.",
    ]
    facts.extend(f"{color}({color})." for color in COLORS)
    for item in examples:
        facts.extend(f"{predicate}({','.join(args)})." for predicate, args in item.state.facts)
    (task_dir / "bk.pl").write_text(":- style_check(-discontiguous).\n" + "\n".join(facts) + "\n")
    labels = [
        f"{'pos' if item.label else 'neg'}(goal({item.state.state_id}))."
        for item in examples
    ]
    (task_dir / "exs.pl").write_text(":- style_check(-discontiguous).\n" + "\n".join(labels) + "\n")
    (task_dir / "bias.pl").write_text(bias_path.read_text())


def _learn(task_dir: Path, timeout: float = 30.0) -> str:
    if str(POPPER_ROOT) not in sys.path:
        sys.path.insert(0, str(POPPER_ROOT))
    from popper.loop import learn_solution
    from popper.util import Settings, format_prog, order_prog

    settings = Settings(
        kbpath=str(task_dir),
        info=False,
        timeout=timeout,
        max_body=5,
        max_vars=5,
        max_rules=1,
        max_literals=20,
        solver="rc2",
    )
    program, score, _stats = learn_solution(settings)
    if program is None:
        raise RuntimeError("Popper found no consistent hidden-goal hypothesis")
    hypothesis = format_prog(order_prog(program))
    (task_dir / "hypothesis.pl").write_text(hypothesis + "\n")
    (task_dir / "score.txt").write_text(str(score) + "\n")
    return hypothesis


def _to_labelled(observation: GameObservation, label: bool) -> goal_ilp.LabelledState:
    state = goal_ilp.SyntheticState(observation.state_id, observation.facts)
    return goal_ilp.LabelledState(state, label)


def _collect_interaction(game_type, variants: Sequence[int], rng: random.Random, steps_per_variant: int):
    examples: Dict[str, goal_ilp.LabelledState] = {}
    transitions = []
    action_count = 0
    for variant in variants:
        game = game_type(variant)
        game.reset()
        for _ in range(steps_per_variant):
            action = rng.choice(ACTIONS)
            before = game.observe()
            after, _reward, done, info = game.step(action)
            labelled = _to_labelled(after, bool(info["goal_reached"]))
            examples.setdefault(after.state_id, labelled)
            transitions.append((before.state_id, action, after.state_id))
            action_count += 1
            if done:
                game.reset()
    values = list(examples.values())
    rng.shuffle(values)
    return values, transitions, action_count


def _true_rule(game_name: str) -> str:
    if game_name == "unary":
        return "goal(S):- object_color(S,X,C), red(C)."
    if game_name == "relational":
        return "goal(S):- adjacent(S,X,Y), object_color(S,X,C), object_color(S,Y,C)."
    return "goal(S):- object_color(S,X,C), red(C), adjacent(S,X,Y), object_color(S,Y,D), blue(D)."


def _write_planner(path: Path, learned_hypothesis: str, state_facts: Sequence[str], transitions, start_state: str, horizon: int):
    lines = [
        f"time(0..{horizon}).",
        f"state_at({start_state},0).",
        "1 { action(left,T); action(right,T) } 1 :- time(T), T < %d, not finished(T)." % horizon,
        "state_at(N,T+1) :- state_at(S,T), action(A,T), transition(S,A,N), T < %d." % horizon,
        "goal_reached(T) :- state_at(S,T), goal(S).",
        "finished(T) :- time(T), goal_reached(G), T >= G.",
        ":- not goal_reached(_).",
        "#minimize { 1,T,A : action(A,T) }.",
        "#show action/2.",
        "#show state_at/2.",
    ]
    lines.extend(state_facts)
    lines.extend(f"transition({source},{action},{target})." for source, action, target in transitions)
    lines.append(learned_hypothesis.strip())
    path.write_text("\n".join(lines) + "\n")


def _run_planner(path: Path):
    output = subprocess.check_output(
        [sys.executable, "-m", "clingo", "-n", "0", str(path), "--opt-mode=opt", "--outf=2"],
        text=True,
    )
    result = json.loads(output)
    if result["Result"] == "UNSATISFIABLE":
        return []
    answer = result["Call"][0]["Witnesses"][-1]["Value"]
    actions = []
    for atom in answer:
        match = re.fullmatch(r"action\((left|right),(\d+)\)", atom)
        if match:
            actions.append((int(match.group(2)), match.group(1)))
    return [action for _time, action in sorted(actions)]


def _graph_for_variant(game_type, variant: int):
    game = game_type(variant)
    states = {}
    transitions = []
    for position in range(game.max_position + 1):
        game.reset()
        game.position = position
        observation = game.observe()
        states[observation.state_id] = observation
        for action in ACTIONS:
            game.reset()
            game.position = position
            after, _reward, _done, _info = game.step(action)
            transitions.append((observation.state_id, action, after.state_id))
            states[after.state_id] = after
    facts = [
        f"{color}({color})."
        for color in COLORS
    ]
    facts.extend(
        f"{predicate}({','.join(args)})."
        for observation in states.values()
        for predicate, args in observation.facts
    )
    return game, states, transitions, facts


def _induce_and_plan(game_name: str, seed: int, output_root: Path, train_variants: Sequence[int], heldout_variants: Sequence[int]):
    experiment_start = time.perf_counter()
    rng = random.Random(seed)
    game_type = GAME_TYPES[game_name]
    game_dir = output_root / game_name / f"seed_{seed}"
    game_dir.mkdir(parents=True, exist_ok=True)
    bias_path = output_root / game_name / "bias.pl"
    _write_bias(bias_path)

    train, _train_transitions, interaction_steps = _collect_interaction(game_type, train_variants, rng, 40)
    heldout, _heldout_transitions, _ = _collect_interaction(game_type, heldout_variants, rng, 50)
    if not any(item.label for item in train) or not any(not item.label for item in train):
        raise RuntimeError("training interaction did not observe both goal labels")

    hypothesis = ""
    induction_indices = []
    induction_seconds = 0.0
    for index, item in enumerate(train, start=1):
        seen = train[:index]
        has_both_labels = any(example.label for example in seen) and any(
            not example.label for example in seen
        )
        if not hypothesis and not has_both_labels:
            continue
        correctly_covers_seen = bool(hypothesis) and all(
            goal_ilp._entails(hypothesis, example.state) == example.label for example in seen
        )
        if correctly_covers_seen:
            continue
        task_dir = game_dir / "popper_task"
        _write_task(task_dir, seen, bias_path)
        start = time.perf_counter()
        hypothesis = _learn(task_dir)
        induction_seconds += time.perf_counter() - start
        induction_indices.append(index)

    heldout_predictions = [goal_ilp._entails(hypothesis, item.state) for item in heldout]
    true_rule = _true_rule(game_name)
    heldout_agreement = mean(prediction == item.label for prediction, item in zip(heldout_predictions, heldout))
    precision_denominator = sum(heldout_predictions)
    recall_denominator = sum(item.label for item in heldout)
    true_positives = sum(prediction and item.label for prediction, item in zip(heldout_predictions, heldout))
    precision = true_positives / precision_denominator if precision_denominator else 1.0
    recall = true_positives / recall_denominator if recall_denominator else 1.0

    test_variant = heldout_variants[-1]
    game, states, transitions, planner_facts = _graph_for_variant(game_type, test_variant)
    planner_path = game_dir / "planner.lp"
    start_state = game.reset().state_id
    _write_planner(planner_path, hypothesis, planner_facts, transitions, start_state, game.max_position + 2)
    planning_start = time.perf_counter()
    actions = _run_planner(planner_path)
    planning_seconds = time.perf_counter() - planning_start
    game.reset()
    reached = False
    executed = []
    for action in actions:
        _observation, _reward, done, info = game.step(action)
        executed.append(action)
        if info["goal_reached"]:
            reached = True
            break
        if done:
            break

    return {
        "game": game_name,
        "seed": seed,
        "training_examples": len(train),
        "training_positive": sum(item.label for item in train),
        "training_negative": sum(not item.label for item in train),
        "held_out_examples": len(heldout),
        "held_out_positive": sum(item.label for item in heldout),
        "held_out_negative": sum(not item.label for item in heldout),
        "interaction_steps": interaction_steps,
        "goal_induction_calls": len(induction_indices),
        "goal_induction_call_indices": induction_indices,
        "examples_to_convergence": induction_indices[-1],
        "goal_induction_seconds": induction_seconds,
        "held_out_agreement": heldout_agreement,
        "held_out_precision": precision,
        "held_out_recall": recall,
        "true_rule": true_rule,
        "learned_rule": hypothesis,
        "syntactically_identical": goal_ilp._canonical_hypothesis(hypothesis) == goal_ilp._canonical_hypothesis(true_rule),
        "planning_seconds": planning_seconds,
        "plan_actions": executed,
        "plan_length": len(executed),
        "planning_success": reached,
        "failure_reason": "" if reached else "planned actions did not reach the hidden goal state",
        "runtime_seconds": time.perf_counter() - experiment_start,
    }


def _summary(rows):
    def metric(key):
        values = [float(row[key]) for row in rows]
        return {"mean": mean(values), "spread": pstdev(values), "n": len(values)}

    return {
        "game": rows[0]["game"],
        "runs": len(rows),
        "metrics": {
            "training_examples": metric("training_examples"),
            "held_out_examples": metric("held_out_examples"),
            "examples_to_convergence": metric("examples_to_convergence"),
            "held_out_agreement": metric("held_out_agreement"),
            "held_out_precision": metric("held_out_precision"),
            "held_out_recall": metric("held_out_recall"),
            "goal_induction_calls": metric("goal_induction_calls"),
            "goal_induction_seconds": metric("goal_induction_seconds"),
            "planning_seconds": metric("planning_seconds"),
            "plan_length": metric("plan_length"),
        },
        "success_rate": mean(bool(row["planning_success"]) for row in rows),
        "syntactic_match_count": sum(bool(row["syntactically_identical"]) for row in rows),
        "failure_count": sum(not bool(row["planning_success"]) for row in rows),
    }


def _write_csv(path: Path, rows):
    fields = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if isinstance(value, (str, int, float, bool, list))
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                key: json.dumps(row.get(key)) if isinstance(row.get(key), list) else row.get(key, "")
                for key in fields
            }
            for row in rows
        )


def _write_report(results_dir: Path, summaries):
    lines = [
        "# Interactive hidden-goal induction report",
        "",
        "Three deterministic symbolic line-world games were run. The agent received symbolic state facts and action outcomes, but not the true goal rule. Popper induced `goal/1` incrementally, and the learned rule was inserted into a Clingo ASP planner.",
        "",
        "| Game | Seeds | Convergence examples | Held-out agreement | Precision | Recall | Planning success |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for game_name in ("unary", "relational", "compositional"):
        summary = summaries[game_name]
        m = summary["metrics"]
        lines.append(
            f"| {game_name} | {summary['runs']} | {m['examples_to_convergence']['mean']:.3f} ± {m['examples_to_convergence']['spread']:.3f} | "
            f"{m['held_out_agreement']['mean']:.3f} ± {m['held_out_agreement']['spread']:.3f} | "
            f"{m['held_out_precision']['mean']:.3f} ± {m['held_out_precision']['spread']:.3f} | "
            f"{m['held_out_recall']['mean']:.3f} ± {m['held_out_recall']['spread']:.3f} | {summary['success_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "All three games use interaction for data collection and a separate held-out interaction pass for validation. No ARC-AGI-3 perception or API is involved. No counting/numeric goal was attempted.",
            "",
            "The planner receives the learned goal rule together with observed symbolic facts and deterministic transition outcomes. The environment's hidden goal predicate is used only for reward/terminal outcomes and final success verification.",
            "",
        ]
    )
    for game_name in ("unary", "relational", "compositional"):
        summary = summaries[game_name]
        rows = [
            json.loads(path.read_text())
            for path in sorted((results_dir / "hidden_goal" / game_name).glob("seed_*.json"))
        ]
        representative = rows[0]
        m = summary["metrics"]
        failures = [
            f"seed {row['seed']}: {row['failure_reason']}"
            for row in rows
            if not row["planning_success"]
        ]
        lines.extend(
            [
                "",
                f"## {game_name}",
                "",
                f"Representative Popper rule: `{representative['learned_rule']}`",
                f"Mean training/held-out examples: {m['training_examples']['mean']:.3f} ± {m['training_examples']['spread']:.3f} / {m['held_out_examples']['mean']:.3f} ± {m['held_out_examples']['spread']:.3f}",
                f"Mean induction calls/time: {m['goal_induction_calls']['mean']:.3f} ± {m['goal_induction_calls']['spread']:.3f} / {m['goal_induction_seconds']['mean']:.4f} ± {m['goal_induction_seconds']['spread']:.4f} s",
                f"Mean planning time/plan length: {m['planning_seconds']['mean']:.4f} ± {m['planning_seconds']['spread']:.4f} s / {m['plan_length']['mean']:.3f} ± {m['plan_length']['spread']:.3f} actions",
                f"Representative executed plan: `{', '.join(representative['plan_actions'])}`",
                f"Syntactically identical to the environment rule: {summary['syntactic_match_count']}/{summary['runs']} seeds",
                f"Failures: {summary['failure_count']}/{summary['runs']}" + ("; " + "; ".join(failures) if failures else " (none)"),
            ]
        )
    lines.extend(
        [
            "",
            "Per-game machine-readable outputs are in `results/hidden_goal/<game>/`; the combined run table is `results/hidden_goal_results.csv`.",
        ]
    )
    (results_dir / "HIDDEN_GOAL_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--output-dir", default=str(ROOT / "results"))
    parser.add_argument("--game", choices=tuple(GAME_TYPES), default=None, help=argparse.SUPPRESS)
    parser.add_argument("--seed", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    results_dir = Path(args.output_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    if args.child:
        if args.game is None:
            raise ValueError("--game is required for a child run")
        row = _induce_and_plan(args.game, args.seed, results_dir / "hidden_goal", range(6), range(6, 12))
        game_dir = results_dir / "hidden_goal" / args.game
        game_dir.mkdir(parents=True, exist_ok=True)
        (game_dir / f"seed_{args.seed}.json").write_text(json.dumps(row, indent=2) + "\n")
        print(json.dumps(row, indent=2))
        return 0

    all_rows = []
    summaries = {}
    for game_name in ("unary", "relational", "compositional"):
        game_dir = results_dir / "hidden_goal" / game_name
        game_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for seed in range(args.seeds):
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--game",
                game_name,
                "--seed",
                str(seed),
                "--output-dir",
                str(results_dir),
                "--child",
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
            rows.append(json.loads((game_dir / f"seed_{seed}.json").read_text()))
        summary = _summary(rows)
        summaries[game_name] = summary
        (game_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        _write_csv(game_dir / "runs.csv", rows)
        all_rows.extend(rows)
    _write_csv(results_dir / "hidden_goal_results.csv", all_rows)
    _write_report(results_dir, summaries)
    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
