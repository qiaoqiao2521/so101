"""Try the original 51mm transport choice first and stop separation at step 10."""


def route_preferences():
    return {'transport_preference_m': .051, 'separation_steps': 10,
            'ik_seed': 'continuation'}
