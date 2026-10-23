"""Request ownership and current-field guards across the one-pass alternative."""
from dataclasses import replace
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np

from configuration_sweep import ConfigurationSweepInvocation, SweepBinding
from route_policy import RoutePolicy, load_route_policy
from visual_grasp_controller import VisualGraspController


class SinglePassContextTests(unittest.TestCase):
    def controller(self):
        c = VisualGraspController.__new__(VisualGraspController)
        c.checker, c.rig = object(), object()
        c.stage, c.jaw = 'close', .015
        c.route_policy = RoutePolicy()
        c.target_xy = np.array([.12, -.0])
        c.reference = np.arange(6, dtype=float)/10
        c.world = [(np.array([1.,2.]), np.array([3.,4.]))]
        c.observation = (7, .2, (.1, .2), (0., -0.))
        c.released_query = SimpleNamespace(model=object(), center=np.array([.2,.3,.01]),
            rotation=np.eye(3), uncertainty_m=.003)
        return c

    def bindings(self, c, purpose='online_chord'):
        start, end = [0.]*5+[.5], [0.]*5+[.015]
        c.route_policy = replace(c.route_policy, fused_context_freeze=False)
        left = c._sweep_binding(start, end, purpose)
        c.route_policy = replace(c.route_policy, fused_context_freeze=True)
        right = c._sweep_binding(start, end, purpose)
        return left, right

    def without_policy(self, binding):
        return tuple(row for row in binding.context if row[0] != 'route_policy')

    def test_current_controller_fields_match_and_remain_owned(self):
        c = self.controller()
        for purpose in ('planned_closure','measured_closure','online_chord'):
            with self.subTest(purpose=purpose):
                left, right = self.bindings(c,purpose)
                self.assertEqual(self.without_policy(left),self.without_policy(right))
                self.assertEqual(left._jaw_bits,right._jaw_bits)
                expected = right.context
                c.target_xy[0] += .01
                c.released_query.rotation[0,0] += .001
                self.assertEqual(right.context,expected)
                changed = c._sweep_binding([0.]*5+[.5],[0.]*5+[.015],purpose)
                self.assertFalse(right.matches(changed))

    def test_current_field_rejections_keep_original_error(self):
        for value in (np.array([math.nan]), {'a':np.array([math.inf])},
                      {'a':object()}, np.float32(1.), {RoutePolicy():1.}):
            with self.subTest(value=type(value).__name__):
                c = self.controller()
                c.world = value
                errors=[]
                for enabled in (False,True):
                    c.route_policy=RoutePolicy(fused_context_freeze=enabled)
                    try:
                        c._sweep_binding([0.]*5+[.5],[0.]*5+[.015],'online_chord')
                    except (ValueError,TypeError) as error:
                        errors.append((type(error),str(error)))
                self.assertEqual(len(errors),2)
                self.assertEqual(errors[0],errors[1])

    def test_constructor_keeps_ownership_stage_jaw_and_context_checks(self):
        common=dict(owner=object(),checker=object(),model=object(),stage='close',
                    jaw_intent_rad=.015,context=())
        for changes in ({'owner':None},{'checker':None},{'model':None},
                        {'stage':''},{'jaw_intent_rad':math.nan},
                        {'guard_scope':'other'},{'context':[]}):
            with self.subTest(changes=changes):
                errors=[]
                for enabled in (False,True):
                    try:
                        SweepBinding(**dict(common,**changes),snapshot_context=enabled)
                    except (ValueError,TypeError) as error:
                        errors.append((type(error),str(error)))
                self.assertEqual(len(errors),2)
                self.assertEqual(errors[0],errors[1])

    def test_mutated_raw_values_cannot_consume_a_previous_request(self):
        owner,checker,model=object(),object(),object()
        raw=np.array([1.,-0.])
        def binding():
            return SweepBinding(owner,checker,model,'close',.015,(raw,),snapshot_context=True)
        first=binding()
        invocation=ConfigurationSweepInvocation([0.]*5+[.5],[0.]*5+[.015],binding=first)
        invocation.execute(lambda q:True)
        raw[0]=2.
        with self.assertRaisesRegex(RuntimeError,'ownership or context changed'):
            invocation.consume(binding())
        self.assertEqual(invocation.state,'failed')

    def test_signed_zero_and_encoded_context_replacement_stay_distinct(self):
        owner,checker,model=object(),object(),object()
        def binding(value):
            return SweepBinding(owner,checker,model,'close',.015,(value,),snapshot_context=True)
        left,right=binding(np.array([-0.])),binding(np.array([0.]))
        self.assertFalse(left.matches(right))
        self.assertTrue(left.matches(replace(left)))

    def test_candidate_has_one_preference_delta_and_default_is_off(self):
        folder=Path(__file__).parent/'route_strategies'
        parent,_=load_route_policy(folder/'direction_hint_preallocated.py')
        candidate,_=load_route_policy(folder/'direction_hint_single_pass.py')
        self.assertFalse(parent.fused_context_freeze)
        self.assertEqual([key for key,value in parent.preferences().items()
                          if value!=candidate.preferences()[key]],['fused_context_freeze'])
        for bad in (1,0,None,'true'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                RoutePolicy(fused_context_freeze=bad)


if __name__=='__main__':
    unittest.main()
