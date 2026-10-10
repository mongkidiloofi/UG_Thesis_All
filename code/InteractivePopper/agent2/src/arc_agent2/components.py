"""Four-connected components of a discrete color grid."""

from dataclasses import dataclass

import numpy as np


@dataclass
class Component:
    color: int
    x: int
    y: int
    w: int
    h: int
    area: int
    mask: bytes

    @property
    def key(self):
        return (self.color, self.w, self.h, self.mask)


def components(frame):
    a = np.asarray(frame)
    seen = np.zeros(a.shape, bool)
    out = []
    height, width = a.shape
    for y in range(height):
        for x in range(width):
            if seen[y, x]:
                continue
            color = int(a[y, x])
            todo = [(x, y)]
            seen[y, x] = True
            points = []
            while todo:
                px, py = todo.pop()
                points.append((px, py))
                for qx, qy in [(px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)]:
                    if (
                        0 <= qx < width
                        and 0 <= qy < height
                        and not seen[qy, qx]
                        and a[qy, qx] == color
                    ):
                        seen[qy, qx] = True
                        todo.append((qx, qy))
            xs, ys = zip(*points)
            left, right = min(xs), max(xs)
            t, b = min(ys), max(ys)
            mask = np.zeros((b - t + 1, right - left + 1), np.uint8)
            for px, py in points:
                mask[py - t, px - left] = 1
            out.append(
                Component(color, left, t, right - left + 1, b - t + 1, len(points), mask.tobytes())
            )
    return out
