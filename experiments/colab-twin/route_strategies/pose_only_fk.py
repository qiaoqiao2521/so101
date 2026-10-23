"""Root GPT: reuse archived pose-only query, isolated from IK and physics."""


def route_preferences():
    return {'leaf_packed': True, 'packed_inline': True, 'seed_bound_direct': True,
            'summary_fast': True, 'batch_configuration_sweep': True,
            'smooth_jaw_dwell': True, 'refresh_leg_age': True,
            'pose_only_fk': True}
