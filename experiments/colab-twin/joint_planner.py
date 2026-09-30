"""OMPL RRTConnect for five bounded SO101 arm joints, in radians.

The caller owns the MuJoCo model/data and supplies a deterministic state
validity callback. The gripper is fixed outside this five-dimensional space.
Collision checking is discrete: every edge is checked at a Euclidean joint
distance no greater than ``resolution_rad``. This is not continuous collision
detection; the caller must choose a resolution/clearance suitable for its scene.

OMPL seeds RNG instances from a process-wide generator. Only the first planning
call initializes that generator (seed 0 maps to 1, which OMPL requires). Later
calls continue the sequence and report the effective first seed; they do not
reset global RNG state. Reproduce a batch in a fresh process, in the same order,
and invoke this module before constructing other OMPL RNG/planner instances.
"""

from collections.abc import Callable, Iterable, Sequence
from importlib.metadata import version
import math
from numbers import Integral
import threading
import time


_DIMENSION = 5
_INITIAL_SEED: int | None = None
_SEED_LOCK = threading.Lock()


def _joint_state(values: Iterable[float], name: str) -> list[float]:
    try:
        state = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain five finite joint angles") from exc
    if len(state) != _DIMENSION or not all(math.isfinite(value) for value in state):
        raise ValueError(f"{name} must contain five finite joint angles")
    return state


def _positive_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def _edge_samples(start: list[float], goal: list[float], resolution: float):
    """Yield the edge after its start, including its unchanged final endpoint."""
    count = max(1, math.ceil(math.dist(start, goal) / resolution))
    for index in range(1, count):
        fraction = index / count
        yield [a + (b - a) * fraction for a, b in zip(start, goal)]
    yield goal.copy()


def validate_joint_path(
    path: Iterable[Iterable[float]],
    is_valid: Callable[[list[float]], bool],
    resolution_rad: float = 0.025,
) -> dict:
    """Recheck every edge, including intermediate states, at the given spacing.

    Malformed angles/resolution raise ValueError; callback exceptions propagate.
    An empty path is invalid. The report identifies the first rejected sample.
    """
    resolution = _positive_finite(resolution_rad, "resolution_rad")
    if not callable(is_valid):
        raise TypeError("is_valid must be callable")
    states = [_joint_state(state, "path waypoint") for state in path]
    report = {
        "valid": False,
        "checked_states": 0,
        "resolution_rad": resolution,
        "max_sample_step_rad": 0.0,
        "invalid_segment": None,
        "invalid_state": None,
    }
    if not states:
        report["reason"] = "empty_path"
        return report

    def check(state: list[float], segment: int | None) -> bool:
        report["checked_states"] += 1
        if not bool(is_valid(state.copy())):
            report["invalid_segment"] = segment
            report["invalid_state"] = state.copy()
            report["reason"] = "invalid_state"
            return False
        return True

    if not check(states[0], None):
        return report
    for segment, (start, goal) in enumerate(zip(states, states[1:])):
        previous = start
        for state in _edge_samples(start, goal, resolution):
            report["max_sample_step_rad"] = max(
                report["max_sample_step_rad"], math.dist(previous, state)
            )
            if not check(state, segment):
                return report
            previous = state
    report["valid"] = True
    return report


def _initialize_seed(ompl_util, requested: int) -> int:
    global _INITIAL_SEED
    with _SEED_LOCK:
        if _INITIAL_SEED is None:
            effective = max(1, requested)
            ompl_util.RNG.setSeed(effective)
            _INITIAL_SEED = effective
        return _INITIAL_SEED


def plan_joint_path(
    start5: Sequence[float],
    goal5: Sequence[float],
    bounds: Sequence[Sequence[float]],
    is_valid: Callable[[list[float]], bool],
    *,
    seed: int = 0,
    timeout_s: float = 5.0,
    resolution_rad: float = 0.025,
) -> dict:
    """Return only an exact, revalidated RRTConnect path or a named failure.

    Bounds have shape (5, 2), with finite increasing lower/upper limits. The
    returned path preserves the requested endpoints and is itself discretized
    to spacing <= resolution_rad. ``timeout_s`` bounds OMPL's solve phase;
    setup and final validation are also included in ``elapsed_seconds``.
    """
    entered = time.perf_counter()
    start = _joint_state(start5, "start5")
    goal = _joint_state(goal5, "goal5")
    resolution = _positive_finite(resolution_rad, "resolution_rad")
    timeout = _positive_finite(timeout_s, "timeout_s")
    if not isinstance(seed, Integral) or not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError("seed must be an integer in [0, 2**32 - 1]")
    seed = int(seed)
    if not callable(is_valid):
        raise TypeError("is_valid must be callable")
    try:
        limits = [[float(value) for value in pair] for pair in bounds]
    except (TypeError, ValueError) as exc:
        raise ValueError("bounds must have shape (5, 2)") from exc
    if len(limits) != _DIMENSION or any(
        len(pair) != 2
        or not all(math.isfinite(value) for value in pair)
        or pair[0] >= pair[1]
        for pair in limits
    ):
        raise ValueError("bounds must have five finite increasing limit pairs")

    result = {
        "status": "timeout",
        "path": None,
        "planner": "RRTConnect",
        "exact_solution": False,
        "planning_seconds": 0.0,
        "elapsed_seconds": 0.0,
        "resolution_rad": resolution,
        "requested_seed": seed,
        "rng_seed": _INITIAL_SEED,
        "rng_seed_scope": "process_first_plan",
        "validity_checks": 0,
    }

    def bounded_valid(state: list[float]) -> bool:
        result["validity_checks"] += 1
        return all(lo <= value <= hi for value, (lo, hi) in zip(state, limits)) and bool(
            is_valid(state.copy())
        )

    def finish() -> dict:
        result["elapsed_seconds"] = time.perf_counter() - entered
        return result

    if not bounded_valid(start):
        result["status"] = "invalid_start"
        return finish()
    if not bounded_valid(goal):
        result["status"] = "invalid_goal"
        return finish()

    # Lazy imports allow the independent path validator and invalid-input
    # checks to be used without installing OMPL. The runtime pins OMPL 2.0.1.
    from ompl import base as ob, geometric as og, util as ou

    result["ompl_version"] = version("ompl")
    result["rng_seed"] = _initialize_seed(ou, seed)
    space = ob.RealVectorStateSpace(_DIMENSION)
    ompl_bounds = ob.RealVectorBounds(_DIMENSION)
    for index, (lo, hi) in enumerate(limits):
        ompl_bounds.setLow(index, lo)
        ompl_bounds.setHigh(index, hi)
    space.setBounds(ompl_bounds)
    # OMPL's discrete motion validator checks intermediate states at this
    # fraction of the full Euclidean space extent, rather than only vertices.
    space.setLongestValidSegmentFraction(min(0.5, resolution / space.getMaximumExtent()))
    setup = og.SimpleSetup(space)
    setup.setStateValidityChecker(
        lambda state: bounded_valid([float(state[index]) for index in range(_DIMENSION)])
    )
    start_state = space.allocState()
    goal_state = space.allocState()
    for index in range(_DIMENSION):
        start_state[index] = start[index]
        goal_state[index] = goal[index]
    setup.setStartAndGoalStates(start_state, goal_state, 1e-12)
    setup.setPlanner(og.RRTConnect(setup.getSpaceInformation()))
    setup.setup()
    solving = time.perf_counter()
    planner_status = setup.solve(timeout)
    result["planning_seconds"] = time.perf_counter() - solving
    result["planner_status"] = planner_status.asString()
    if not setup.getProblemDefinition().hasExactSolution():
        result["reason"] = (
            "approximate_solution_rejected"
            if setup.getProblemDefinition().hasApproximateSolution()
            else "no_exact_solution"
        )
        return finish()

    raw_path = [
        [float(state[index]) for index in range(_DIMENSION)]
        for state in setup.getSolutionPath().getStates()
    ]
    # Preserve exactly the requested endpoints, then validate the resulting
    # edges again. A goal tolerance must never silently change the output goal.
    if not raw_path:
        result["reason"] = "empty_solution_rejected"
        return finish()
    raw_path[0] = start.copy()
    if len(raw_path) == 1:
        raw_path.append(goal.copy())
    else:
        raw_path[-1] = goal.copy()
    path = [start.copy()]
    for edge_start, edge_goal in zip(raw_path, raw_path[1:]):
        path.extend(_edge_samples(edge_start, edge_goal, resolution))
    validation = validate_joint_path(path, bounded_valid, resolution)
    result["validation"] = validation
    if not validation["valid"]:
        result["reason"] = "post_validation_failed"
        return finish()
    result.update(
        status="solved",
        path=path,
        exact_solution=True,
        raw_waypoint_count=len(raw_path),
        waypoint_count=len(path),
        path_length_rad=sum(math.dist(a, b) for a, b in zip(path, path[1:])),
    )
    return finish()
