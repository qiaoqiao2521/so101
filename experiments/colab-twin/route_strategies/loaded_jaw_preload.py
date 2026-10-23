"""Root GPT: keep a latched loaded-jaw target after the original grasp/lift."""


def route_preferences():
    return {'leaf_packed': True, 'packed_inline': True, 'seed_bound_direct': True,
            'summary_fast': True, 'batch_configuration_sweep': True,
            'smooth_jaw_dwell': True, 'refresh_leg_age': True,
            'direction_hint_sweep': True, 'preallocate_worker_models': True,
            'fused_context_freeze': True, 'compact_status_json': True,
            'float_first_context': True, 'loaded_jaw_preload': True}
