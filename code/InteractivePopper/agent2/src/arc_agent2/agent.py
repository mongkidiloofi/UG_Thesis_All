"""Observe → hypothesize → predict → explore/plan → revise, without game IDs."""

import math
import random
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

from .learning import BinaryRule, Learner, PixelRule
from .perception import Perception


class Agent2:
    """Incremental world-model learner with bounded curiosity-driven planning.

    Call ``observe`` once before ``choose`` and after every executed action.
    Only public observations enter this class; the runner owns game identifiers.
    """

    def __init__(self, out, seed=0, timeout=8, max_fits=40, search_nodes=160):
        self.perception = Perception()
        self.view = None
        self.pending = None
        self.level = None
        self.available = ()
        self.learner = Learner(Path(out), timeout, max_fits)
        self.moves = BinaryRule("advances", self.learner)
        self.changed = BinaryRule("changes", self.learner)
        self.progress = BinaryRule("progress", self.learner)
        self.exception = BinaryRule("exceptional", self.learner)
        self.channels = {}
        self.archived_channels = []
        self.history = deque(maxlen=128)
        self.vectors = defaultdict(Counter)
        self.mapping = {}
        self.rng = random.Random(seed)
        self.search_nodes = search_nodes
        self.action_counts = Counter()
        self.visits = Counter()
        self.spatial = Counter()
        self.context_trials = Counter()
        self.click_trials = Counter()
        self.patch_effects = set()
        self.effect_trials = Counter()
        self.trace = []
        self.step = 0
        self.anomalies = 0
        self.level_events = []

    def observe(self, frame, level: int, available):
        """Consume one public observation and learn from the preceding action."""
        before = self.view
        old_level = self.level
        view, discovered = self.perception.ingest(frame, level)
        self.view = view
        self.available = tuple(available)
        self.level = level
        if before is not None and self.pending is not None:
            self._record_transition(before, view, discovered, old_level)
        self.pending = None
        if view.position is not None:
            self.visits[(level, view.context, view.position, self.symbol_state())] += 1
            self.spatial[(level, view.position)] += 1

    def _record_transition(self, before, view, discovered, old_level):
        level = self.level
        self.step += 1
        p = self.pending
        action = p["action"]
        advanced = level > old_level
        changed = not np.array_equal(before.frame, view.frame)
        self.progress.observe(p["features"], advanced, self.step)
        self.changed.observe(p["features"], changed, self.step)
        row = dict(
            step=self.step,
            level_before=old_level,
            level_after=level,
            action=action,
            data=p["data"],
            reason=p["reason"],
            features=sorted(p["features"]),
            progress=advanced,
            changed=changed,
            position_before=before.position,
            position_after=view.position,
            predicted_position=p["predicted_position"],
            predicted_progress=p["predicted_progress"],
            predicted_changed=p["predicted_changed"],
            pixel_predictions=0,
            pixel_correct=0,
            pixel_changes=0,
            changed_pixel_predictions=0,
            changed_pixel_correct=0,
            exception=False,
        )
        if advanced:
            self.level_events.append(dict(step=self.step, before=old_level, after=level))
            self.archived_channels.extend(self.channel_summary())
            self.channels = {}
            self.history.clear()
        else:
            self._observe_motion(before, view, discovered, p, row)
        self.trace.append(row)

    def _observe_motion(self, before, view, discovered, p, row):
        """Learn ordinary effects while recording unexplained jumps separately."""
        action = p["action"]
        oldpos = before.position
        if discovered is not None:
            oldpos = discovered[0]
        pos = view.position
        known = self.mapping.get(action)
        delta = None if oldpos is None or pos is None else (pos[0] - oldpos[0], pos[1] - oldpos[1])
        abnormal = delta is not None and known is not None and delta not in [(0, 0), known]
        if delta is not None and delta != (0, 0):
            self.vectors[action][delta] += 1
            self.mapping[action] = self.vectors[action].most_common(1)[0][0]
        row["exception"] = abnormal
        if delta is not None and known is not None:
            self.exception.observe(p["features"], abnormal, self.step)
        if abnormal:
            self.anomalies += 1
        elif delta is not None and p["valid"] and known is not None:
            self.moves.observe(p["features"], delta != (0, 0), self.step)
        if row["predicted_position"] is not None and pos is not None:
            row["position_correct"] = tuple(row["predicted_position"]) == pos
        # No post-transition facts are used for the saved prediction.
        # Observed entry is used only as the training label for the
        # movement→symbol factorization, analogous to teacher forcing.
        entered = ()
        if pos is not None and oldpos is not None and pos != oldpos and not abnormal:
            x, y, w, h = self.perception.box(pos)
            entered = tuple(int(c) for c in np.unique(p["terrain"][y : y + h, x : x + w]))
        if p["data"] is not None:
            entered = p["colors"]
        # A clicked region remains observable if its original color
        # disappears entirely. Register its bounds, not its semantics.
        if p["data"] is not None:
            for key in before.patches.keys() | self.channels.keys():
                color, x, y, n = key
                view.patches.setdefault(
                    key,
                    tuple(int(v) for v in (view.frame[y : y + n, x : x + n] == color).flat),
                )
                before.patches.setdefault(
                    key,
                    tuple(int(v) for v in (before.frame[y : y + n, x : x + n] == color).flat),
                )
        if not abnormal:
            self._learn_regions(before, view, entered, p, row)

    def _learn_regions(self, before, view, entered, p, row):
        """Register changed regions and score predictions made before the action."""
        sample = (before.patches, entered, view.patches)
        self.history.append(sample)
        for key in sorted(before.patches.keys() & view.patches.keys(), key=lambda k: k[3]):
            b, t = before.patches[key], view.patches[key]
            local_click = (
                p["data"] is not None
                and key[1] <= p["data"]["x"] < key[1] + key[3]
                and key[2] <= p["data"]["y"] < key[2] + key[3]
            )
            channel_context = entered + ((-1,) if local_click else ())
            if (
                b != t
                and (sum(b) == sum(t) or local_click)
                and key not in self.channels
                and len(self.channels) < 2
            ):
                self._register_channel(key, b, channel_context, t, p["data"] is not None)
            if key in self.channels:
                if b != t:
                    row["pixel_changes"] += 1
                pred = p["symbols"].get(key)
                if pred is not None:
                    row["pixel_predictions"] += 1
                    row["pixel_correct"] += pred == t
                    if b != t:
                        row["changed_pixel_predictions"] += 1
                        row["changed_pixel_correct"] += pred == t
                self.channels[key].observe(b, channel_context, t, self.step)
                if b != t:
                    self.patch_effects.add(entered)
        before_symbols = tuple(
            (k, before.patches[k]) for k in sorted(self.channels) if k in before.patches
        )
        self.effect_trials[(before_symbols, entered)] += 1

    def _register_channel(self, key, b, channel_context, t, clicked):
        """Try retained programs against observations before starting a new fit."""
        channel = PixelRule(key, self.learner)
        self.channels[key] = channel
        if not clicked:
            for old, cs, new in self.history:
                if key in old and key in new:
                    channel.rows.add((old[key], cs, new[key]))
        else:
            channel.rows.add((b, channel_context, t))
        # Retained theories are proposals, not automatically
        # trusted role assignments in a new level.
        for archived in self.archived_channels:
            if archived["rule"] is None:
                continue
            channel.rule = archived["rule"]
            channel.cache.clear()
            if all(channel.predict(s, c) == t for s, c, t in channel.rows):
                break
            channel.rule = None
            channel.cache.clear()

    def symbol_state(self):
        return tuple(
            (k, self.view.patches[k]) for k in sorted(self.channels) if k in self.view.patches
        )

    def predict(self, position, symbols, action):
        fs, colors, q, valid = self.perception.features(
            self.view, action, self.mapping, position, dict(symbols)
        )
        can = self.moves.predict(fs)
        if can is None and len(self.moves.rows.get(fs, {})) == 1:
            can = next(iter(self.moves.rows[fs]))
        moving = valid and can is not False
        target = q if moving else position
        result = []
        for key, bits in symbols:
            pred = self.channels[key].predict(bits, colors if moving else ())
            result.append((key, pred if pred is not None else bits))
        return target, tuple(result), fs, colors, valid

    def click_candidates(self):
        frame = self.view.frame
        h, w = frame.shape
        points = {(c.x + c.w // 2, c.y + c.h // 2) for c in self.view.components}
        # Component centers plus a changing uniform lattice cover blank areas.
        offset = self.action_counts[6] % 8
        points.update((x, y) for y in range(offset, h, 8) for x in range(offset, w, 8))
        return sorted(
            points, key=lambda p: (self.click_trials[(self.level, p)], self.rng.random())
        )[:48]

    def fallback(self):
        candidates = []
        for action in self.available:
            points = self.click_candidates() if action == 6 else [None]
            for point in points:
                data = {"x": point[0], "y": point[1]} if point is not None else None
                fs, _, _, _ = self.perception.features(self.view, action, self.mapping, data=data)
                count = self.context_trials[(self.level, fs)]
                # A contextual exploration bonus, not Bayesian information gain.
                score = math.sqrt(math.log(self.step + 2) / (count + 1))
                if self.changed.predict(fs) is False:
                    score -= 0.5
                if self.progress.positives and self.progress.predict(fs) is True:
                    score += 2
                if point is not None:
                    score += 1 / (1 + self.click_trials[(self.level, point)])
                candidates.append((score + self.rng.random() * 0.01, action, data))
        _, action, data = max(candidates, key=lambda c: c[0])
        return action, data, "context_exploration"

    def choose(self) -> tuple[int, dict[str, int] | None]:
        """Select a button and optional click coordinates; do not execute it."""
        if not self.available:
            raise ValueError("No available actions")
        simple = [a for a in self.available if a != 6]
        unknown = [a for a in simple if a not in self.mapping and self.action_counts[a] < 3]
        if unknown:
            action = min(unknown, key=lambda a: (self.action_counts[a], a))
            data = None
            reason = "identify_control"
        elif self.rng.random() < 0.05 or self.view.position is None or not self.mapping:
            action, data, reason = self.fallback()
        else:
            action, data, reason = self._plan()
        return self._prepare_action(action, data, reason)

    def _plan(self):
        """Search predicted states for progress or an informative experiment."""
        start = (self.view.position, self.symbol_state())
        queue = deque([(start, ())])
        seen = {start}
        candidates = []
        goal = None
        while queue and len(seen) <= self.search_nodes:
            (position, symbols), path = queue.popleft()
            for a in sorted(self.mapping):
                if a not in self.available or a == 6:
                    continue
                q, t, fs, colors, valid = self.predict(position, symbols, a)
                if not valid:
                    continue
                next_path = path + (a,)
                if self.progress.positives and self.progress.predict(fs) is True:
                    goal = next_path
                    break
                if q == position and t == symbols:
                    # Falsify untested negative generalizations instead of
                    # letting a pessimistic model permanently hide regions.
                    if self.context_trials[(self.level, fs)] == 0:
                        candidates.append(((1, -0.25, len(next_path), 0), next_path))
                    continue
                visits = self.visits[(self.level, self.view.context, q, t)]
                spatial = self.spatial[(self.level, q)]
                trials = self.context_trials[(self.level, fs)]
                # Count-based novelty trades off with travel distance.
                novelty = visits + 0.25 * spatial
                curiosity = (
                    0
                    if colors in self.patch_effects and self.effect_trials[(symbols, colors)] == 0
                    else 1
                )
                candidates.append(((curiosity, novelty, len(next_path), trials), next_path))
                state = (q, t)
                if state not in seen:
                    seen.add(state)
                    queue.append((state, next_path))
            if goal:
                break
        if goal:
            action = goal[0]
            data = None
            reason = "learned_progress_plan"
        elif candidates:
            action = min(candidates, key=lambda c: c[0])[1][0]
            data = None
            reason = "model_novelty_plan"
        else:
            action, data, reason = self.fallback()
        return action, data, reason

    def _prepare_action(self, action, data, reason):
        """Store predictions before allowing the caller to execute the action."""
        fs, colors, q, valid = self.perception.features(self.view, action, self.mapping, data=data)
        predicted_position = None
        predicted_symbols = {}
        if self.view.position is not None and action in self.mapping and data is None:
            predicted_position, pixels, _, _, _ = self.predict(
                self.view.position, self.symbol_state(), action
            )
            predicted_symbols = {k: v for k, v in pixels if self.channels[k].rule is not None}
        if data is not None:
            for key, channel in self.channels.items():
                if key not in self.view.patches:
                    continue
                _, x, y, n = key
                local = x <= data["x"] < x + n and y <= data["y"] < y + n
                pred = channel.predict(self.view.patches[key], colors + ((-1,) if local else ()))
                if pred is not None:
                    predicted_symbols[key] = pred
        self.pending = dict(
            action=action,
            data=data,
            reason=reason,
            features=fs,
            colors=colors,
            valid=valid,
            predicted_position=predicted_position,
            symbols=predicted_symbols,
            predicted_progress=self.progress.predict(fs),
            predicted_changed=self.changed.predict(fs),
            terrain=self.perception.terrain.copy(),
        )
        self.action_counts[action] += 1
        self.context_trials[(self.level, fs)] += 1
        if data is not None:
            self.click_trials[(self.level, (data["x"], data["y"]))] += 1
        return action, data

    def channel_summary(self):
        return [
            dict(key=k, rule=v.rule, examples=len(v.rows), errors=v.errors)
            for k, v in self.channels.items()
        ]

    def summary(self):
        return dict(
            actions=self.step,
            levels_observed=self.level_events,
            anomalies=self.anomalies,
            mapping=self.mapping,
            channels=self.channel_summary(),
            archived_channels=self.archived_channels,
            rules={
                m.name: dict(
                    program=m.rule,
                    distinct_contexts=len(m.rows),
                    positives=m.positives,
                    contradictions=sum(len(v) > 1 for v in m.rows.values()),
                    errors=m.errors,
                )
                for m in [self.moves, self.changed, self.progress, self.exception]
            },
            fits=self.learner.attempts,
            position_predictions=sum("position_correct" in r for r in self.trace),
            position_correct=sum(r.get("position_correct", False) for r in self.trace),
            pixel_predictions=sum(r["pixel_predictions"] for r in self.trace),
            pixel_correct=sum(r["pixel_correct"] for r in self.trace),
            pixel_changes=sum(r["pixel_changes"] for r in self.trace),
            changed_pixel_predictions=sum(r["changed_pixel_predictions"] for r in self.trace),
            changed_pixel_correct=sum(r["changed_pixel_correct"] for r in self.trace),
        )
