"""Small route preferences; geometry, guards and physical scoring stay external."""
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import runpy


@dataclass(frozen=True)
class RoutePolicy:
    transport_preference_m: float | None = None
    separation_steps: int = 13
    ik_seed: str = 'continuation'
    transport_candidates: int = 1
    reuse_adjacent_validity: bool = False
    reuse_separation_distances: bool = False
    batch_separation_axes: bool = False
    quad_vertices: bool = False
    small_direction_cache: bool = False
    tree_leaf8: bool = False
    leaf_packed: bool = False
    packed_inline: bool = False
    seed_bound_direct: bool = False
    summary_fast: bool = False
    refresh_leg_age: bool = False
    batch_configuration_sweep: bool = False
    smooth_jaw_dwell: bool = False

    def __post_init__(self):
        height = self.transport_preference_m
        if height is not None and (isinstance(height, bool) or
                not isinstance(height, (int, float)) or not math.isfinite(height) or
                not .023 <= height <= .060):
            raise ValueError('Transport preference must be 23..60 mm above the tray base')
        if (isinstance(self.separation_steps, bool) or not isinstance(self.separation_steps, int)
                or not 1 <= self.separation_steps <= 13):
            raise ValueError('Separation selects a prefix of the original 13 waypoints')
        if self.ik_seed not in ('continuation', 'neutral'):
            raise ValueError('IK seed must be continuation or neutral')
        if (isinstance(self.transport_candidates, bool)
                or not isinstance(self.transport_candidates, int)
                or not 1 <= self.transport_candidates <= 3):
            raise ValueError('Transport compares 1..3 fully certified routes')
        if not isinstance(self.reuse_adjacent_validity, bool):
            raise ValueError('Adjacent validity reuse must be a boolean')
        if not isinstance(self.reuse_separation_distances, bool):
            raise ValueError('Separation distance reuse must be a boolean')
        if not isinstance(self.batch_separation_axes, bool):
            raise ValueError('Batched separation axes must be a boolean')
        if not isinstance(self.quad_vertices, bool):
            raise ValueError('Four-vertex evaluation must be a boolean')
        if not isinstance(self.small_direction_cache, bool):
            raise ValueError('Small direction cache must be a boolean')
        if not isinstance(self.tree_leaf8, bool):
            raise ValueError('Eight-vertex tree leaves must be a boolean')
        if not isinstance(self.leaf_packed, bool):
            raise ValueError('Packed leaf storage must be a boolean')
        if not isinstance(self.packed_inline, bool):
            raise ValueError('Packed helper inlining must be a boolean')
        if not isinstance(self.seed_bound_direct, bool):
            raise ValueError('Seed-bound reuse must be a boolean')
        if not isinstance(self.summary_fast, bool):
            raise ValueError('All-valid summary selection must be a boolean')
        if not isinstance(self.refresh_leg_age, bool):
            raise ValueError('Motion leg clock refresh must be a boolean')
        if not isinstance(self.batch_configuration_sweep, bool):
            raise ValueError('Configuration sweep batching must be a boolean')
        if not isinstance(self.smooth_jaw_dwell, bool):
            raise ValueError('Continuous jaw dwell selection must be a boolean')

    def transport_heights(self, heights, base_height):
        """Reorder existing choices only; retain every original fallback."""
        heights = list(heights)
        if self.transport_preference_m is not None:
            target = base_height + self.transport_preference_m
            chosen = min(range(len(heights)), key=lambda i: abs(heights[i]-target))
            heights.insert(0, heights.pop(chosen))
        return heights

    def preferences(self):
        return asdict(self)


DEFAULT_ROUTE_POLICY = RoutePolicy()
BASELINE_SOURCE = Path(__file__).parent/'route_strategies/baseline.py'
DEFAULT_SOURCE = Path(__file__).parent/'route_strategies/smooth_jaw_leg_clock.py'


def load_route_policy(path=None):
    """Execute the selected local source once and pass only immutable choices."""
    path = Path(path or DEFAULT_SOURCE).resolve()
    namespace = runpy.run_path(str(path))
    factory = namespace['route_preferences']
    values = factory()
    if not isinstance(values, dict):
        raise ValueError('route_preferences() must return a preferences dictionary')
    policy = RoutePolicy(**values)
    return policy, {'loaded_path': str(Path(namespace['__file__']).resolve()),
                    'entrypoint': 'route_preferences',
                    'entrypoint_path': str(Path(factory.__code__.co_filename).resolve()),
                    'preferences': policy.preferences()}
