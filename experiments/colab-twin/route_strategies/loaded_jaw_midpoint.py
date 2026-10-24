"""Explicit midpoint approach search on the complete loaded-jaw parent recipe."""
from route_strategies.loaded_jaw_preload import route_preferences as _parent


def route_preferences():
    return {**_parent(), 'approach_midpoint_order': True}
