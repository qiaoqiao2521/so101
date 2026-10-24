"""Reuse same-query raw details on the complete loaded-jaw midpoint parent."""
from route_strategies.loaded_jaw_midpoint import route_preferences as _parent


def route_preferences():
    return {**_parent(), 'reuse_refinement_details': True}
