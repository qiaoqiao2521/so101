"""CLI45 scheduling candidate, reviewed by root; preparation counts in case time."""


def route_preferences():
    return {'leaf_packed': True, 'packed_inline': True, 'seed_bound_direct': True,
            'summary_fast': True, 'batch_configuration_sweep': True,
            'smooth_jaw_dwell': True, 'refresh_leg_age': True,
            'preallocate_worker_models': True}
