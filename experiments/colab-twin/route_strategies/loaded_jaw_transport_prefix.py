"""Use the same-owner raw prefix only for online transport configuration sweeps."""
from route_strategies.loaded_jaw_midpoint_details import route_preferences as _parent


def route_preferences():
    return {**_parent(), 'transport_refinement_prefix': True}
