"""CLI35: sample a new motion leg with its own clock, including same-stage legs."""


def route_preferences():
    return {'leaf_packed': True, 'packed_inline': True, 'seed_bound_direct': True,
            'summary_fast': True, 'refresh_leg_age': True}
