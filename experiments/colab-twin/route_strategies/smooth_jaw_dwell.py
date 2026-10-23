"""CLI39/40: keep the original dwell, continuously sample its jaw target."""


def route_preferences():
    return {'leaf_packed': True, 'packed_inline': True, 'seed_bound_direct': True,
            'summary_fast': True, 'batch_configuration_sweep': True,
            'smooth_jaw_dwell': True}
