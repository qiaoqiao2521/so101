"""Latch the existing loaded preload once at lift entry; keep original guards."""
from route_strategies.loaded_jaw_transport_prefix import route_preferences as _parent


def route_preferences():
    return {**_parent(), 'loaded_jaw_lift_preload': True}
