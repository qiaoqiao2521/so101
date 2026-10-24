"""Root GPT: move the original measured-pose return into an owned worker."""
from route_strategies.loaded_jaw_preload import route_preferences as parent_preferences


def route_preferences():
    return dict(parent_preferences(), async_measured_return=True)
