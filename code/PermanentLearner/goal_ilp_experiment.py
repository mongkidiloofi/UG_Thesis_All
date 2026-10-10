"""Synthetic hidden-goal ILP experiment.

This is deliberately separate from the maze reproduction.  It generates pure
symbolic states, reveals only binary goal labels, and incrementally re-runs the
pinned Popper learner when the current hypothesis no longer classifies all
examples seen so far.
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


ROOT = Path(__file__).resolve().parent
POPPER_ROOT = ROOT / "Popper"
PALETTE = ("red", "blue", "green", "yellow")


@dataclass(frozen=True)
class SyntheticState:
    state_id: str
    facts: Tuple[Tuple[str, Tuple[str, ...]], ...]


@dataclass(frozen=True)
class LabelledState:
    state: SyntheticState
    label: bool


def _split_terms(text: str) -> List[str]:
    parts: List[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def _parse_atom(text: str):
    text = text.strip().rstrip(".")
    negative = text.startswith("not ")
    if negative:
        text = text[4:].strip()
    opening = text.find("(")
    if opening < 1 or not text.endswith(")"):
        raise ValueError(f"unsupported literal: {text!r}")
    predicate = text[:opening]
    arguments = []
    for term in _split_terms(text[opening + 1:-1]):
        term = term.strip()
        arguments.append(("var", term) if term and term[0].isupper() else ("const", term))
    return negative, predicate, tuple(arguments)


def _parse_hypothesis(hypothesis: str):
    rules = []
    for raw in hypothesis.splitlines():
        line = raw.strip()
        if not line or line.startswith("%") or ":-" not in line:
            continue
        head_text, body_text = line.rstrip(".").split(":-", 1)
        _negative, head_predicate, head_args = _parse_atom(head_text)
        body = tuple(_parse_atom(literal) for literal in _split_terms(body_text))
        rules.append((head_predicate, head_args, body))
    return tuple(rules)


def _unify(pattern, value, bindings: Dict[str, str]) -> bool:
    if pattern[0] == "var":
        name = pattern[1]
        if name in bindings:
            return bindings[name] == value
        bindings[name] = value
        return True
    return pattern[1] == value


def _entails(hypothesis: str, state: SyntheticState) -> bool:
    rules = _parse_hypothesis(hypothesis)
    by_predicate: Dict[str, List[Tuple[str, ...]]] = {}
    for predicate, args in state.facts:
        by_predicate.setdefault(predicate, []).append(args)
    # Popper represents typed colour constants as unary background predicates
    # (e.g. yellow(yellow)) in this version; mirror those facts in the local
    # coverage checker.
    for color in PALETTE:
        by_predicate[color] = [(color,)]

    for head_predicate, head_args, body in rules:
        if head_predicate != "goal" or len(head_args) != 1:
            continue
        bindings: Dict[str, str] = {}
        if not _unify(head_args[0], state.state_id, bindings):
            continue
        environments = [bindings]
        for negative, predicate, arguments in body:
            next_environments = []
            for environment in environments:
                matches = []
                for fact_args in by_predicate.get(predicate, []):
                    candidate = dict(environment)
                    if len(arguments) == len(fact_args) and all(
                        _unify(pattern, value, candidate)
                        for pattern, value in zip(arguments, fact_args)
                    ):
                        matches.append(candidate)
                if negative:
                    if not matches:
                        next_environments.append(environment)
                else:
                    next_environments.extend(matches)
            environments = next_environments
            if not environments:
                break
        if environments:
            return True
    return False


def _canonical_hypothesis(hypothesis: str):
    canonical = []
    for head_predicate, head_args, body in _parse_hypothesis(hypothesis):
        variables: Dict[str, str] = {}

        def term(value):
            if value[0] == "const":
                return value[1]
            name = value[1]
            if name not in variables:
                variables[name] = f"V{len(variables)}"
            return variables[name]

        head = (head_predicate, tuple(term(value) for value in head_args))
        body_atoms = tuple(
            sorted(
                (
                    negative,
                    predicate,
                    tuple(term(value) for value in arguments),
                )
                for negative, predicate, arguments in body
            )
        )
        canonical.append((head, body_atoms))
    return tuple(sorted(canonical))


def _facts_for_state(state_id: str, objects: Sequence[str], colors: Sequence[str], adjacency: Sequence[Tuple[str, str]]):
    facts = [("object", (state_id, obj)) for obj in objects]
    facts.extend(("color", (state_id, obj, color)) for obj, color in zip(objects, colors))
    facts.extend(("adjacent", (state_id, left, right)) for left, right in adjacency)
    return tuple(facts)


def _generate_state(rng: random.Random, prefix: str, index: int) -> SyntheticState:
    state_id = f"{prefix}{index}"
    count = rng.randint(3, 6)
    objects = tuple(f"o{index}_{number}" for number in range(count))
    positions = rng.sample([(x, y) for x in range(3) for y in range(3)], count)
    colors = tuple(rng.choice(PALETTE) for _ in objects)
    possible = [
        (objects[left], objects[right])
        for left in range(count)
        for right in range(left + 1, count)
        if abs(positions[left][0] - positions[right][0]) + abs(positions[left][1] - positions[right][1]) == 1
    ]
    if not possible:
        possible = [(objects[left], objects[right]) for left in range(count) for right in range(left + 1, count)]
    rng.shuffle(possible)
    adjacency = []
    for left, right in possible[: rng.randint(1, min(4, len(possible)))]:
        adjacency.extend(((left, right), (right, left)))
    return SyntheticState(state_id, _facts_for_state(state_id, objects, colors, adjacency))


def _label(state: SyntheticState, template: str, target_color: str | None) -> bool:
    colors = {(args[1], args[2]) for predicate, args in state.facts if predicate == "color"}
    if template == "unary":
        return any(color == target_color for _object, color in colors)
    color_by_object = {object_id: color for object_id, color in colors}
    return any(
        color_by_object.get(left) == color_by_object.get(right)
        for predicate, args in state.facts
        if predicate == "adjacent"
        for state_id, left, right in (args,)
        if state_id == state.state_id
    )


def _generate_pool(
    rng: random.Random,
    template: str,
    target_color: str | None,
    prefix: str,
    count: int,
    minimum_each: int,
) -> List[LabelledState]:
    labelled: List[LabelledState] = []
    positives = negatives = 0
    attempts = 0
    while len(labelled) < count or positives < minimum_each or negatives < minimum_each:
        state = _generate_state(rng, prefix, attempts)
        label = _label(state, template, target_color)
        labelled.append(LabelledState(state, label))
        positives += int(label)
        negatives += int(not label)
        attempts += 1
        if attempts > 10000:
            raise RuntimeError("could not generate a balanced synthetic state pool")
    rng.shuffle(labelled)
    return labelled


def _fact_line(predicate: str, arguments: Sequence[str]) -> str:
    return f"{predicate}({','.join(arguments)})."


def _write_bias(path: Path) -> None:
    path.write_text(
        """head_pred(goal,1).
body_pred(object,2).
body_pred(color,3).
body_pred(adjacent,3).
body_pred(red,1).
body_pred(blue,1).
body_pred(green,1).
body_pred(yellow,1).

type(goal,(state,)).
type(object,(state,obj)).
type(color,(state,obj,colour)).
type(adjacent,(state,obj,obj)).
type(red,(colour,)).
type(blue,(colour,)).
type(green,(colour,)).
type(yellow,(colour,)).

direction(goal,(in,)).
direction(object,(in,out)).
direction(color,(in,in,out)).
direction(adjacent,(in,out,out)).
direction(red,(in,)).
direction(blue,(in,)).
direction(green,(in,)).
direction(yellow,(in,)).

constant(red,colour).
constant(blue,colour).
constant(green,colour).
constant(yellow,colour).

max_body(3).
max_vars(4).
max_clauses(1).
"""
    )


def _write_task(task_dir: Path, examples: Sequence[LabelledState], bias_path: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    facts = [_fact_line(color, (color,)) for color in PALETTE]
    for item in examples:
        facts.extend(_fact_line(predicate, args) for predicate, args in item.state.facts)
    (task_dir / "bk.pl").write_text(
        ":- style_check(-discontiguous).\n" + "\n".join(facts) + "\n"
    )
    labels = [
        f"{'pos' if item.label else 'neg'}(goal({item.state.state_id}))."
        for item in examples
    ]
    (task_dir / "exs.pl").write_text(
        ":- style_check(-discontiguous).\n" + "\n".join(labels) + "\n"
    )
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
        max_body=3,
        max_vars=4,
        max_rules=1,
        max_literals=12,
        solver="rc2",
    )
    program, score, _stats = learn_solution(settings)
    if program is None:
        raise RuntimeError("Popper found no consistent goal hypothesis")
    hypothesis = format_prog(order_prog(program))
    (task_dir / "hypothesis.pl").write_text(hypothesis + "\n")
    (task_dir / "score.txt").write_text(str(score) + "\n")
    return hypothesis


def _true_hypothesis(template: str, target_color: str | None) -> str:
    if template == "unary":
        return f"goal(S):- color(S,X,C), {target_color}(C)."
    return "goal(S):- adjacent(S,X,Y), color(S,X,C), color(S,Y,C)."


def run_one(template: str, seed: int, output_dir: Path, train_size: int, heldout_size: int) -> Dict[str, object]:
    rng = random.Random(seed)
    target_color = rng.choice(PALETTE) if template == "unary" else None
    run_dir = output_dir / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    bias_path = output_dir / "bias.pl"
    _write_bias(bias_path)

    train = _generate_pool(rng, template, target_color, "s", train_size, minimum_each=10)
    heldout = _generate_pool(rng, template, target_color, "h", heldout_size, minimum_each=10)
    (run_dir / "train_states.json").write_text(
        json.dumps([{"state_id": item.state.state_id, "label": item.label} for item in train], indent=2) + "\n"
    )

    seen: List[LabelledState] = []
    hypothesis = ""
    induction_indices: List[int] = []
    induction_seconds = 0.0
    start_time = time.perf_counter()
    for index, item in enumerate(train, start=1):
        seen.append(item)
        has_both_labels = any(example.label for example in seen) and any(
            not example.label for example in seen
        )
        if not hypothesis and not has_both_labels:
            # Popper's tester requires at least one positive and one negative
            # example; this also matches the intended balanced-data setup.
            continue
        correctly_covers_seen = bool(hypothesis) and all(
            _entails(hypothesis, example.state) == example.label for example in seen
        )
        if correctly_covers_seen:
            continue
        task_dir = run_dir / "popper_task"
        _write_task(task_dir, seen, bias_path)
        induction_start = time.perf_counter()
        new_hypothesis = _learn(task_dir)
        induction_seconds += time.perf_counter() - induction_start
        induction_indices.append(index)
        hypothesis = new_hypothesis

    if not hypothesis:
        raise RuntimeError("the incremental loop did not induce a hypothesis")

    heldout_predictions = [_entails(hypothesis, item.state) for item in heldout]
    heldout_agreement = mean(
        prediction == item.label for prediction, item in zip(heldout_predictions, heldout)
    )
    true_hypothesis = _true_hypothesis(template, target_color)
    syntactically_identical = _canonical_hypothesis(hypothesis) == _canonical_hypothesis(true_hypothesis)
    return {
        "template": template,
        "seed": seed,
        "target_color": target_color,
        "train_examples": len(train),
        "train_positive": sum(item.label for item in train),
        "train_negative": sum(not item.label for item in train),
        "held_out_examples": len(heldout),
        "held_out_positive": sum(item.label for item in heldout),
        "held_out_negative": sum(not item.label for item in heldout),
        "examples_to_convergence": induction_indices[-1],
        "induction_indices": induction_indices,
        "induction_calls": len(induction_indices),
        "induction_seconds": induction_seconds,
        "held_out_agreement": heldout_agreement,
        "spurious_convergence": heldout_agreement < 1.0,
        "syntactically_identical": syntactically_identical,
        "agreement_without_syntactic_identity": heldout_agreement == 1.0 and not syntactically_identical,
        "true_hypothesis": true_hypothesis,
        "learned_hypothesis": hypothesis,
        "runtime_seconds": time.perf_counter() - start_time,
    }


def _summarize(rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    def stats(key: str):
        values = [float(row[key]) for row in rows]
        return {"mean": mean(values), "spread": pstdev(values), "n": len(values)}

    return {
        "template": rows[0]["template"],
        "runs": len(rows),
        "metrics": {
            "examples_to_convergence": stats("examples_to_convergence"),
            "held_out_agreement": stats("held_out_agreement"),
        },
        "spurious_convergence_runs": sum(bool(row["spurious_convergence"]) for row in rows),
        "syntactically_identical_runs": sum(bool(row["syntactically_identical"]) for row in rows),
        "agreement_without_syntactic_identity_runs": sum(
            bool(row["agreement_without_syntactic_identity"]) for row in rows
        ),
    }


def _write_outputs(output_dir: Path, rows: Sequence[Dict[str, object]]) -> None:
    summary = _summarize(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    fields = sorted(
        key
        for row in rows
        for key, value in row.items()
        if isinstance(value, (str, int, float, bool))
    )
    with (output_dir / "runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", choices=("unary", "relational"), required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--train-size", type=int, default=60)
    parser.add_argument("--heldout-size", type=int, default=100)
    parser.add_argument("--output-dir", default=str(ROOT / "goal_results"))
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve() / args.template
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.child:
        row = run_one(args.template, args.seed, output_dir, args.train_size, args.heldout_size)
        run_dir = output_dir / f"seed_{args.seed}"
        (run_dir / "result.json").write_text(json.dumps(row, indent=2) + "\n")
        print(json.dumps(row, indent=2))
        return 0

    rows = []
    for seed in range(args.seed, args.seed + args.seeds):
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--template",
            args.template,
            "--seed",
            str(seed),
            "--train-size",
            str(args.train_size),
            "--heldout-size",
            str(args.heldout_size),
            "--output-dir",
            str(Path(args.output_dir).resolve()),
            "--child",
        ]
        subprocess.run(command, check=True)
        rows.append(json.loads((output_dir / f"seed_{seed}" / "result.json").read_text()))
    _write_outputs(output_dir, rows)
    print(json.dumps(_summarize(rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
