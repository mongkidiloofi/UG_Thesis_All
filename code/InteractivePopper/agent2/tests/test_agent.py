"""Deterministic tests of the general machinery; these are NOT ARC scores."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from arc_agent2.agent import Agent2
from arc_agent2.learning import BinaryRule, Learner, PixelRule
from arc_agent2.perception import normalized


class Corridor:
    """Small two-level world used only as an integration-test environment.

    The policy receives rendered grids and public action/level metadata only.
    Colors are permuted, and an observation rotation can
    change all spatial coordinates. No labels are supplied to the learner.
    """

    def __init__(self, seed=11, rotation=0):
        rng = np.random.default_rng(seed)
        self.palette = rng.permutation(16)
        self.rotation = rotation
        self.effects = {a: d for a, d in zip([1, 2, 3, 4], [(4, 0), (0, -4), (-4, 0), (0, 4)])}
        self.level = 0
        self.x = 10
        self.y = 30
        self.symbol = np.array([[1, 1, 1], [1, 0, 0], [1, 0, 1]])

    def frame(self):
        a = np.full((64, 64), 2, dtype=np.uint8)
        a[30:34, 10:34] = 1
        a[30:34, 18:22] = 4
        goal = 30 if self.level == 0 else 10
        a[30:34, goal : goal + 4] = 3
        a[4:10, 46:52] = np.where(np.kron(self.symbol, np.ones((2, 2))), 7, 2)
        a[self.y : self.y + 4, self.x : self.x + 4] = 6
        return np.rot90(self.palette[a], self.rotation).copy()

    def step(self, action):
        dx, dy = self.effects[action]
        x, y = self.x + dx, self.y + dy
        if 10 <= x <= 30 and y == 30:
            self.x, self.y = x, y
            if x == 18:
                self.symbol = np.rot90(self.symbol, -1)
            goal = 30 if self.level == 0 else 10
            if x == goal:
                self.level += 1
                self.x = 30 if self.level == 1 else 10
        return self.frame()


class Tests(unittest.TestCase):
    def test_bitmap_signature_translation_scale(self):
        a = np.array([[1, 1, 1], [1, 0, 0], [1, 0, 1]])
        enlarged = np.pad(np.kron(a, np.ones((3, 3))), ((4, 2), (1, 3)))
        self.assertEqual(normalized(a), normalized(enlarged))
        self.assertNotEqual(normalized(a), normalized(np.rot90(a)))

    def test_actual_popper_and_contradiction_retraction(self):
        with tempfile.TemporaryDirectory() as d:
            learner = Learner(Path(d), timeout=8)
            model = BinaryRule("progress", learner)
            model.observe(frozenset(["ordinary"]), False, 1)
            model.observe(frozenset(["novel"]), True, 2)
            self.assertIsNotNone(model.rule)
            self.assertFalse(model.predict(frozenset(["ordinary"])))
            self.assertTrue(model.predict(frozenset(["novel"])))
            model.observe(frozenset(["novel"]), False, 3)
            self.assertIsNone(model.rule)
            self.assertIsNone(model.predict(frozenset(["novel"])))
            self.assertTrue(learner.attempts[0]["accepted"])

    def test_click_inversion_from_negative_only_initial_transition(self):
        with tempfile.TemporaryDirectory() as d:
            learner = Learner(Path(d), timeout=8)
            model = PixelRule((2, 0, 0, 2), learner)
            ones = (1, 1, 1, 1)
            zeros = (0, 0, 0, 0)
            model.observe(ones, (2, -1), zeros, 1)
            self.assertEqual(model.rule, "")
            self.assertEqual(learner.attempts[0]["engine"], "empty_hypothesis")
            model.observe(zeros, (3,), zeros, 5)
            model.observe(zeros, (3, -1), ones, 9)
            model.observe(ones, (2,), ones, 13)
            self.assertIsNotNone(model.rule)
            for bits in [(1, 0, 0, 1), (0, 1, 0, 1)]:
                self.assertEqual(model.predict(bits, (3, -1)), tuple(1 - v for v in bits))
                self.assertEqual(model.predict(bits, (3,)), bits)

    def test_rotated_recolored_two_level_world(self):
        for rotation in [0, 1]:
            world = Corridor(seed=11 + rotation, rotation=rotation)
            with tempfile.TemporaryDirectory() as d:
                agent = Agent2(Path(d), seed=0, timeout=8, max_fits=18)
                agent.observe(world.frame(), world.level, [1, 2, 3, 4])
                for step in range(1, 101):
                    action, data = agent.choose()
                    self.assertIsNone(data)
                    frame = world.step(action)
                    agent.observe(frame, world.level, [1, 2, 3, 4])
                    if world.level >= 2:
                        break
                self.assertEqual(world.level, 2)
                self.assertEqual(len(agent.level_events), 2)
                self.assertGreater(agent.progress.positives, 0)
                self.assertTrue(
                    any(f["accepted"] and f["task"] == "progress" for f in agent.learner.attempts)
                )
                self.assertTrue(
                    any(
                        r["level_before"] == 1 and r["reason"] == "learned_progress_plan"
                        for r in agent.trace
                    )
                )


if __name__ == "__main__":
    unittest.main()
