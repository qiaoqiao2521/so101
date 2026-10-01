"""Stateless, reactive joint targets for expert data collection.

Distances use Euclidean joint coordinates, in radians. The target follows the
polyline beyond the projection of the current actual pose, rather than a clock
or a cached waypoint index. At equally near branches, the earliest segment wins.
Self-intersections and near branches can therefore make progress ambiguous or
nonmonotonic; the caller must bound execution and retain failed attempts.

This geometry helper makes no collision or payload-safety claim. In particular,
the chord from the actual pose to a target beyond a corner may leave the route.
The caller must independently validate that command before any physical step.
"""
from __future__ import annotations

import numpy as np


def joint_path_lookahead(points, actualq, lookahead):
    """Return ``(absolute_target5, projected_progress_fraction)`` without history.

    Adjacent identical waypoints are removed. A route must contain at least one
    finite, numerically nonzero edge. Progress describes the current projection,
    before adding ``lookahead``; the target never extends beyond the route end.
    """
    route = np.asarray(points, dtype=np.float64)
    actual = np.asarray(actualq, dtype=np.float64)
    if route.ndim != 2 or route.shape[1] != 5 or len(route) < 2:
        raise ValueError("Joint route must have shape N x 5 with at least two points")
    if actual.shape != (5,):
        raise ValueError("Actual joint pose must have shape (5,)")
    if not np.isfinite(route).all() or not np.isfinite(actual).all():
        raise ValueError("Joint route and actual pose must be finite")
    if isinstance(lookahead, (bool, np.bool_)) or np.asarray(lookahead).ndim != 0:
        raise ValueError("Lookahead must be one finite positive scalar")
    try:
        distance = float(lookahead)
    except (TypeError, ValueError) as error:
        raise ValueError("Lookahead must be one finite positive scalar") from error
    if not np.isfinite(distance) or distance <= 0:
        raise ValueError("Lookahead must be one finite positive scalar")

    route = route[np.r_[True, np.any(np.diff(route, axis=0) != 0, axis=1)]]
    if len(route) < 2:
        raise ValueError("Joint route must contain a nonzero edge")
    edges = np.diff(route, axis=0)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        lengths = np.linalg.norm(edges, axis=1)
        squared_lengths = np.einsum("ij,ij->i", edges, edges)
        cumulative = np.r_[0.0, np.cumsum(lengths)]
        if (not np.isfinite(lengths).all() or not np.isfinite(cumulative).all()
                or not np.isfinite(squared_lengths).all() or np.any(squared_lengths <= 0)):
            raise ValueError("Joint route geometry must have finite nonzero edge lengths")
        alpha = np.clip(np.einsum("ij,ij->i", actual - route[:-1], edges) / squared_lengths, 0, 1)
        projections = route[:-1] + alpha[:, None] * edges
        distances = np.linalg.norm(projections - actual, axis=1)
    if not np.isfinite(distances).all():
        raise ValueError("Actual pose and route must have finite projection distances")

    nearest = int(np.argmin(distances))  # Deterministic first segment for exact ties.
    projected_s = float(cumulative[nearest] + alpha[nearest] * lengths[nearest])
    total = float(cumulative[-1])
    progress = float(np.clip(projected_s / total, 0, 1))
    if distance >= total - projected_s:
        return route[-1].copy(), progress
    target_s = projected_s + distance
    segment = min(int(np.searchsorted(cumulative, target_s, side="right") - 1), len(edges) - 1)
    fraction = (target_s - cumulative[segment]) / lengths[segment]
    target = route[segment] + fraction * edges[segment]
    return target.copy(), progress
