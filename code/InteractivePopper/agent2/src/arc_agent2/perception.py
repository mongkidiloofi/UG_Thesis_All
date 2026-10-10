"""Color components, action-correlated motion, and stationary bitmap proposals.

No palette roles, screen crops, game identifiers, supplied sprites, or goals.
Objectness, bounded square bitmap proposals, and a static-terrain memory are
explicit inductive biases; they are not universal properties of ARC games.
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .components import components


def normalized(bits):
    a = np.asarray(bits, dtype=np.uint8)
    ys, xs = np.where(a)
    if not len(xs):
        return ()
    a = a[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    # Remove adjacent duplicate rows/columns: a cheap scale-invariant signature.
    a = a[np.r_[True, np.any(a[1:] != a[:-1], axis=1)]]
    a = a[:, np.r_[True, np.any(a[:, 1:] != a[:, :-1], axis=0)]]
    return (a.shape, a.tobytes())


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def proposals(frame, cs, actor=None):
    out = {}
    for c in cs:
        if not (2 <= c.w == c.h <= 16):
            continue
        if actor is not None and overlap((c.x, c.y, c.w, c.h), actor):
            continue
        key = (c.color, c.x, c.y, c.w)
        bits = frame[c.y : c.y + c.h, c.x : c.x + c.w] == c.color
        if 1 < bits.sum():
            out[key] = tuple(int(v) for v in bits.flat)
    # Nested components of one color are represented by their enclosing patch.
    return {
        k: v
        for k, v in out.items()
        if not any(
            k != j
            and k[0] == j[0]
            and j[1] <= k[1]
            and j[2] <= k[2]
            and k[1] + k[3] <= j[1] + j[3]
            and k[2] + k[3] <= j[2] + j[3]
            for j in out
        )
    }


@dataclass
class View:
    frame: np.ndarray
    components: list
    position: tuple | None
    patches: dict
    context: str


class MotionTracker:
    """Match component translations without assigning any fixed color roles."""

    def __init__(self):
        self.actor_key = None
        self.size = None
        self.floor_colors = set()
        self.co_moving_keys = set()

    def locate(self, components):
        matches = [component for component in components if component.key == self.actor_key]
        return (matches[0].x, matches[0].y) if len(matches) == 1 else None

    def discover(self, before, after, old, new):
        left = defaultdict(list)
        right = defaultdict(list)
        shifts = defaultdict(list)
        for c in old:
            left[c.key].append(c)
        for c in new:
            right[c.key].append(c)
        totals = np.bincount(np.asarray(before).flat, minlength=16)
        for key, items in left.items():
            if len(items) != 1 or len(right.get(key, [])) != 1:
                continue
            a, b = items[0], right[key][0]
            delta = (b.x - a.x, b.y - a.y)
            if delta != (0, 0) and (delta[0] == 0 or delta[1] == 0) and a.area >= 2:
                shifts[delta].append((a, b))
        if not shifts:
            return None
        # A vacated background patch can appear to move opposite the actor.
        # Prefer translations explaining a larger fraction of their colors.
        delta, pairs = max(
            shifts.items(),
            key=lambda item: (
                sum(a.area / max(1, int(totals[a.color])) for a, b in item[1]),
                sum(a.area for a, b in item[1]),
            ),
        )
        a, b = max(pairs, key=lambda pair: pair[0].area)
        self.actor_key = a.key
        self.size = (a.w, a.h)
        self.co_moving_keys = {a.key for a, b in pairs}
        mask = np.frombuffer(a.mask, dtype=np.uint8).reshape(a.h, a.w).astype(bool)
        counts = np.bincount(
            np.asarray(after)[a.y : a.y + a.h, a.x : a.x + a.w][mask], minlength=16
        )
        counts[a.color] = 0
        if counts.max():
            self.floor_colors.add(int(counts.argmax()))
        return (a.x, a.y), (b.x, b.y), delta


class Perception:
    def __init__(self):
        self.tracker = MotionTracker()
        self.previous = None
        self.terrain = None
        self.offset = (0, 0)
        self.size = None
        self.level = None
        self.color_changes = np.zeros(16, dtype=int)
        self.frames = 0

    def box(self, position):
        if position is None or self.size is None:
            return None
        return (position[0] + self.offset[0], position[1] + self.offset[1], *self.size)

    def ingest(self, frame, level):
        frame = np.asarray(frame, dtype=np.uint8).copy()
        if self.level != level:
            self.tracker = MotionTracker()
            self.previous = None
            self.terrain = None
            self.size = None
            self.offset = (0, 0)
            self.level = level
            self.frames = 0
            self.color_changes[:] = 0
        cs = components(frame)
        discovered = None
        if self.previous is not None and self.tracker.actor_key is None:
            found = self.tracker.discover(self.previous.frame, frame, self.previous.components, cs)
            if found:
                old, pos, delta = found
                discovered = (old, pos, delta)
                group = [c for c in cs if c.key in self.tracker.co_moving_keys]
                left = min(c.x for c in group)
                t = min(c.y for c in group)
                self.size = (
                    max(c.x + c.w for c in group) - left,
                    max(c.y + c.h for c in group) - t,
                )
                self.offset = (left - pos[0], t - pos[1])
        position = self.tracker.locate(cs)
        box = self.box(position)
        if self.terrain is None:
            self.terrain = frame.copy()
        if discovered:
            oldbox = self.box(discovered[0])
            x, y, w, h = oldbox
            # Initial occluded terrain is inferred from pixels vacated by motion.
            floor = min(self.tracker.floor_colors) if self.tracker.floor_colors else 0
            self.terrain[y : y + h, x : x + w] = floor
        old_map = self.terrain.copy()
        self.terrain = frame.copy()
        if box:
            x, y, w, h = box
            self.terrain[y : y + h, x : x + w] = old_map[y : y + h, x : x + w]
        counts = np.bincount(frame.flat, minlength=16)
        if self.previous is not None:
            prior = np.bincount(self.previous.frame.flat, minlength=16)
            self.color_changes += counts != prior
        self.frames += 1
        common = set(np.where(counts > frame.size * 0.05)[0])
        nuisance = set(
            np.where((self.color_changes >= 3) & (self.color_changes > self.frames * 0.5))[0]
        )
        # A coarse context for novelty, never a supposedly complete Markov state.
        objs = [
            (c.color, c.x, c.y, c.w, c.h, c.mask.hex())
            for c in cs
            if c.key not in self.tracker.co_moving_keys
            and c.color not in common | nuisance
            and 1 < c.area <= 128
            and max(c.w, c.h) <= 4 * min(c.w, c.h)
        ]
        context = hashlib.sha256(repr(sorted(objs)).encode()).hexdigest()[:16]
        view = View(frame, cs, position, proposals(frame, cs, box), context)
        self.previous = view
        return view, discovered

    def destination(self, position, delta):
        if position is None or delta is None:
            return None, (), False
        q = (position[0] + delta[0], position[1] + delta[1])
        box = self.box(q)
        if box is None:
            return q, (), False
        x, y, w, h = box
        height, width = self.terrain.shape
        valid = 0 <= x <= width - w and 0 <= y <= height - h
        colors = (
            tuple(int(c) for c in np.unique(self.terrain[y : y + h, x : x + w])) if valid else ()
        )
        return q, colors, valid

    def features(self, view, action, mapping, position=None, symbols=None, data=None):
        position = view.position if position is None else position
        q, colors, valid = self.destination(position, mapping.get(action))
        target = self.box(q) if valid else None
        if data is not None:
            x, y = data["x"], data["y"]
            target = (x, y, 1, 1)
            valid = 0 <= x < view.frame.shape[1] and 0 <= y < view.frame.shape[0]
            colors = (int(view.frame[y, x]),) if valid else ()
        features = {f"button_{action}", "in_bounds" if valid else "outside"}
        for c in range(16):
            features.add(f"{'has' if c in colors else 'lacks'}_c{c}")
        if target:
            x, y, w, h = target
            patch = self.terrain[y : y + h, x : x + w]
            for c in colors:
                dest = normalized(patch == c)
                match = False
                for key, bits in view.patches.items():
                    color, px, py, n = key
                    if color != c or overlap((px, py, n, n), target):
                        continue
                    if symbols is not None:
                        bits = symbols.get(key, bits)
                    if normalized(np.array(bits).reshape(n, n)) == dest:
                        match = True
                        break
                features.add(f"{'equal' if match else 'unequal'}_c{c}")
        return frozenset(features), colors, q, valid
