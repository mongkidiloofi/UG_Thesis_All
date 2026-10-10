"""Bounded exact induction, explicit abstention, and counterexample revision."""

import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from .logic import bias, context, infer, pixel_facts


def bitmap_facts(symbol, colors, e):
    n = int(len(symbol) ** 0.5)
    return (
        pixel_facts(symbol, e)
        + context(colors, "entered_", e)
        + [f"absentpixel({e},{i // n},{i % n})." for i, v in enumerate(symbol) if not v]
        + [f"{'local_click' if -1 in colors else 'no_local_click'}({e})."]
    )


class Learner:
    def __init__(self, out, timeout=8, max_calls=40):
        self.out = Path(out)
        self.timeout = timeout
        self.max_calls = max_calls
        self.attempts = []

    def fit(self, name, bk, ex, language, arity, step):
        if len(self.attempts) >= self.max_calls:
            return None
        folder = self.out / f"{len(self.attempts):03d}_{name}"
        folder.mkdir(parents=True, exist_ok=False)
        for file, rows in [("bk.pl", bk), ("exs.pl", ex), ("bias.pl", language)]:
            (folder / file).write_text("\n".join(sorted(set(rows))) + "\n")
        record = dict(task=name, step=step, accepted=False, folder=str(folder))
        self.attempts.append(record)
        start = time.monotonic()
        try:
            if not any(s.startswith("pos(") for s in ex):
                # Popper's tester expects a positive index. The empty program
                # is already the exact minimum for an all-negative task.
                record.update(
                    accepted=True,
                    engine="empty_hypothesis",
                    rules="",
                    positives=0,
                    negatives=len(set(ex)),
                )
                (folder / "hypothesis.pl").write_text("")
                return ""
            record["engine"] = "popper"
            proc = subprocess.run(
                [sys.executable, "-m", "arc_agent2.worker", str(folder), str(self.timeout)],
                capture_output=True,
                text=True,
                timeout=self.timeout + 15,
            )
            (folder / "stdout.txt").write_text(proc.stdout)
            (folder / "stderr.txt").write_text(proc.stderr)
            if proc.returncode:
                raise RuntimeError(f"worker exit {proc.returncode}")
            rules = (folder / "hypothesis.pl").read_text()
            score = json.loads((folder / "score.json").read_text())
            predicted = {
                name + "(" + ",".join(args) + ")"
                for args in infer("\n".join(bk) + "\n" + rules, name, arity)
            }
            positive = {s[4:-2] for s in ex if s.startswith("pos(")}
            negative = {s[4:-2] for s in ex if s.startswith("neg(")}
            record.update(
                score=score, positives=len(positive), negatives=len(negative), rules=rules
            )
            record["accepted"] = positive <= predicted and not bool(negative & predicted)
            return rules if record["accepted"] else None
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
            record["error"] = str(exc)
            return None
        finally:
            record["seconds"] = time.monotonic() - start
            (folder / "audit.json").write_text(json.dumps(record, indent=2))


class BinaryRule:
    def __init__(self, name, learner):
        self.name = name
        self.learner = learner
        self.rows = defaultdict(Counter)
        self.rule = None
        self.cache = {}
        self.last_fit = -100
        self.errors = 0

    def predict(self, features):
        if self.rule is None:
            return None
        if features not in self.cache:
            facts = ["context(q)."] + [f"{p}(q)." for p in features]
            self.cache[features] = bool(infer("\n".join(facts) + "\n" + self.rule, self.name, 1))
        return self.cache[features]

    @property
    def positives(self):
        return sum(c[True] for c in self.rows.values())

    def observe(self, features, label, step):
        predicted = self.predict(features)
        self.rows[features][bool(label)] += 1
        if predicted is not None and predicted != label:
            self.errors += 1
            self.rule = None
            self.cache.clear()
        # Contradictory labels mean this abstraction is insufficient. Do not
        # silently majority-vote them away and call the resulting rules exact.
        if any(len(c) > 1 for c in self.rows.values()):
            self.rule = None
            self.cache.clear()
            return
        if self.rule is not None or step - self.last_fit < 8 or not self.positives:
            return
        self.last_fit = step
        rows = list(self.rows.items())
        if len(rows) > 192:
            return  # Explicit resource bound, no hidden label subsampling.
        vocab = set.union(*(set(fs) for fs, _ in rows))
        varying = {p for p in vocab if len({p in fs for fs, _ in rows}) > 1}
        bk = []
        ex = []
        for i, (fs, labels) in enumerate(rows):
            bk += [f"context(e{i})."] + [f"{p}(e{i})." for p in fs]
            ex.append(f"{'pos' if next(iter(labels)) else 'neg'}({self.name}(e{i})).")
        bodies = {p: ("example",) for p in varying | {"context"}}
        self.rule = self.learner.fit(
            self.name, bk, ex, bias(self.name, ("example",), bodies, 1, 3), 1, step
        )
        self.cache.clear()


class PixelRule:
    def __init__(self, key, learner):
        self.key = key
        self.learner = learner
        self.rows = set()
        self.rule = None
        self.last_fit = -100
        self.cache = {}
        self.errors = 0

    def predict(self, symbol, colors):
        if self.rule is None:
            return None
        key = (symbol, colors)
        if key not in self.cache:
            bk = bitmap_facts(symbol, colors, "q")
            n = int(len(symbol) ** 0.5)
            values = [0] * len(symbol)
            for _, r, c in infer("\n".join(bk) + "\n" + self.rule, "nextpixel", 3):
                values[int(r) * n + int(c)] = 1
            self.cache[key] = tuple(values)
        return self.cache[key]

    def observe(self, before, colors, after, step):
        self.rows.add((before, colors, after))
        predicted = self.predict(before, colors)
        if predicted is not None and predicted != after:
            self.rule = None
            self.cache.clear()
            self.errors += 1
        if self.rule is not None or step - self.last_fit < 4:
            return
        self.last_fit = step
        rows = sorted(self.rows)
        inputs = defaultdict(set)
        for b, c, t in rows:
            inputs[(b, c)].add(t)
        if any(len(v) > 1 for v in inputs.values()):
            return
        varying = [c for c in range(16) if len({c in cs for _, cs, _ in rows}) > 1]
        bodies = {
            "current": ("example", "coord", "coord"),
            "absentpixel": ("example", "coord", "coord"),
            "opposite": ("coord", "coord"),
        }
        if len({-1 in cs for _, cs, _ in rows}) > 1:
            bodies.update(local_click=("example",), no_local_click=("example",))
        for c in varying:
            for kind in ["has", "lacks"]:
                bodies[f"entered_{kind}{c}"] = ("example",)
        bk = []
        ex = []
        for i, (b, colors, t) in enumerate(rows):
            e = f"e{i}"
            n = int(len(b) ** 0.5)
            bk += bitmap_facts(b, colors, e)
            ex += [
                f"{'pos' if v else 'neg'}(nextpixel({e},{j // n},{j % n}))."
                for j, v in enumerate(t)
            ]
        self.rule = self.learner.fit(
            "nextpixel", bk, ex, bias("nextpixel", ("example", "coord", "coord"), bodies), 3, step
        )
        self.cache.clear()
