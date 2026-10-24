"""P0 fixture wiring only; no rendering or physics acceptance is claimed."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch, sentinel

import numpy as np
from PIL import Image

from run_visual_grasp import run_p0
from visual_localization import LocalizationResult


KINDS=('missing','half_occluded','fully_occluded','two_candidates')


class FixtureModel:
    def __init__(self):
        self.names=('target_collision','p0_occluder','p0_distractor')
        self.geom_pos=np.array([[0.,0.,0.],[.24,-.13,.06],[.27,-.16,.010]])
        self.geom_size=np.array([[.009,.009,.008],[.016,.016,.002],[.009,.009,.008]])
        self.geom_rgba=np.array([[.28,.57,.43,1.],[.1,.1,.1,0.],[.28,.57,.43,0.]])
        self.cam_pos=np.array([[.25,0.,.95]])
        self.cam_fovy=np.array([45.])

    def geom(self,name):
        return SimpleNamespace(id=self.names.index(name))

    def body(self,name):
        return SimpleNamespace(id=0)

    def camera(self,name):
        return SimpleNamespace(id=0)


class P0FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.scene=self.root/'source.xml'
        self.scene.write_text('<mujoco><worldbody/></mujoco>')
        self.model=FixtureModel()
        self.baseline={name:getattr(self.model,name).copy()
                       for name in ('geom_pos','geom_size','geom_rgba')}
        self.observed=[]
        self.images=[]
        self.renderer=Mock()
        self.renderer_factory=Mock(return_value=self.renderer)

    def run_cases(self,negatives,*,positives=(),estimate_factory=None):
        out=self.root/f'run-{len(list(self.root.glob("run-*")))}'
        out.mkdir()
        protocol={'p0_positives':list(positives),'p0_negatives':list(negatives),
                  'p0_max_xy_error_m':.002}

        def reset(model,rig,xy):
            self.assertIs(model,self.model)
            self.assertIs(rig,sentinel.rig)
            state={'xy':list(xy)}
            state.update({name:getattr(model,name).copy() for name in self.baseline})
            self.observed.append(state)
            world=model.geom_pos.copy()
            world[0]=[*xy,.010]
            return SimpleNamespace(time=1.,geom_xpos=world,xpos=world[:1].copy())

        def render(renderer,data):
            self.assertIs(renderer,self.renderer)
            rgb=np.full((5,7,3),(91+len(self.images)%100,125,113),dtype=np.uint8)
            self.images.append(rgb.copy())
            return rgb

        def localize(*args,**kwargs):
            self.assertEqual(len(args),2)
            self.assertIs(args[1],sentinel.calibration)
            self.assertEqual(kwargs,{'timestamp_s':1.})
            np.testing.assert_array_equal(args[0],self.images[-1])
            if estimate_factory is not None:
                return estimate_factory(len(self.observed)-1,self.observed[-1])
            return LocalizationResult(False,'target_missing',timestamp_s=1.)

        with ExitStack() as stack:
            stack.enter_context(patch('run_visual_grasp.build_contact_scene',
                return_value=(self.model,sentinel.rig,self.scene)))
            stack.enter_context(patch('run_visual_grasp.mujoco.MjModel',
                SimpleNamespace(from_xml_path=Mock(return_value=self.model))))
            stack.enter_context(patch('run_visual_grasp.mujoco.Renderer',self.renderer_factory))
            stack.enter_context(patch('run_visual_grasp.TopDownCalibration.from_mujoco_model',
                return_value=sentinel.calibration))
            stack.enter_context(patch('run_visual_grasp.reset_scene',side_effect=reset))
            stack.enter_context(patch('run_visual_grasp.render_rgb',side_effect=render))
            stack.enter_context(patch('run_visual_grasp.localize_green_target',side_effect=localize))
            stack.enter_context(patch('run_visual_grasp.save_overlay'))
            stack.enter_context(patch('run_visual_grasp.mujoco.mj_step',
                side_effect=AssertionError('Fixture wiring test must not advance physics')))
            report=run_p0(self.scene,out,protocol,None)
        return report,out

    def assert_restored(self):
        for name,values in self.baseline.items():
            np.testing.assert_array_equal(getattr(self.model,name),values)

    def test_original_strings_keep_default_center_ids_and_seven_cases(self):
        positives=[{'id':f'positive-{i}','initial_xy_m':[x,-.13]}
                   for i,x in enumerate((.24,.22,.26))]

        def estimate(index,state):
            if index<len(positives):
                return LocalizationResult(True,'ok',tuple(state['xy']),(3.,2.),.001,1.)
            return LocalizationResult(False,'target_missing',timestamp_s=1.)

        report,out=self.run_cases(KINDS,positives=positives,estimate_factory=estimate)
        self.assertTrue(report['passed'])
        self.assertTrue(report['complete'])
        self.assertEqual((report['planned'],report['attempted']),(7,7))
        self.assertEqual([row['id'] for row in report['rows'][3:]],list(KINDS))
        for row in report['rows'][3:]:
            self.assertEqual(row['fixture_xy_m'],[.24,-.13])
        for index,row in enumerate(report['rows']):
            path=out/row['raw_rgb_path']
            self.assertEqual(path.parent,out/'rgb')
            with Image.open(path) as image:
                np.testing.assert_array_equal(np.asarray(image),self.images[index])
        self.assert_restored()

    def test_left_right_translation_and_order_do_not_leak_geometry(self):
        for x in (.229,.251):
            for order in (('half_occluded','fully_occluded','two_candidates','missing'),
                          ('missing','two_candidates','fully_occluded','half_occluded')):
                with self.subTest(x=x,order=order):
                    self.observed.clear()
                    cases=[{'id':f'{i}-{kind}','kind':kind,'initial_xy_m':[x,-.13]}
                           for i,kind in enumerate(order)]
                    report,_=self.run_cases(cases)
                    self.assertTrue(report['passed'])
                    for kind,state,row in zip(order,self.observed,report['rows']):
                        self.assertEqual(state['xy'],[x,-.13])
                        np.testing.assert_array_equal(state['geom_pos'][0],self.baseline['geom_pos'][0])
                        np.testing.assert_allclose(state['geom_pos'][1],
                            [x+(.010 if kind=='half_occluded' else 0),-.13,.06],atol=1e-16,rtol=0)
                        np.testing.assert_allclose(state['geom_pos'][2],[x+.03,-.16,.010],atol=1e-16,rtol=0)
                        np.testing.assert_array_equal(state['geom_size'][1],
                            [.010 if kind=='half_occluded' else .016,.016,.002])
                        expected_alpha=[0. if kind=='missing' else 1.,
                                        1. if kind.endswith('occluded') else 0.,
                                        1. if kind=='two_candidates' else 0.]
                        np.testing.assert_array_equal(state['geom_rgba'][:,3],expected_alpha)
                        geometry=row['fixture_geometry']
                        self.assertEqual(geometry['target_collision']['position_m'],[x,-.13,.010])
                        self.assertEqual(geometry['p0_occluder']['position_m'],state['geom_pos'][1].tolist())
                        self.assertEqual(geometry['p0_distractor']['position_m'],state['geom_pos'][2].tolist())
                        self.assertEqual([geometry[name]['alpha'] for name in self.model.names],expected_alpha)
                    self.assert_restored()

    def test_malformed_or_unknown_dictionary_keeps_failure_and_continues(self):
        malformed=[{}, {'id':'bad','kind':'unknown','initial_xy_m':[.229,-.13]},
                   {'id':'bad','kind':'missing','initial_xy_m':[.229]},
                   {'id':'bad','kind':'missing','initial_xy_m':[True,-.13]},
                   {'id':'bad','kind':'missing','initial_xy_m':[float('nan'),-.13]},
                   {'id':'bad','kind':'missing','initial_xy_m':[10**1000,-.13]},
                   {'id':'bad','kind':[],'initial_xy_m':[.229,-.13]},
                   {'id':None,'kind':'missing','initial_xy_m':[.229,-.13]}]
        for bad in malformed:
            with self.subTest(bad=bad):
                self.observed.clear()
                report,_=self.run_cases([bad,'missing'])
                self.assertFalse(report['passed'])
                self.assertTrue(report['complete'])
                self.assertEqual(report['attempted'],2)
                self.assertIn('fixture_error',report['rows'][0])
                self.assertFalse(report['rows'][0]['passed'])
                self.assertTrue(report['rows'][1]['passed'])
                self.assertEqual(len(self.observed),1)
                self.assert_restored()

    def test_bad_ids_do_not_escape_raw_image_directory_and_next_case_runs(self):
        for case_id in ('../outside','/tmp/outside',r'..\outside','.','..','',None,
                        ' ','has space','\t','line\nbreak','bad\x00id','bad\x7fid','bad\x85id'):
            with self.subTest(case_id=case_id):
                bad={'id':case_id,'kind':'missing','initial_xy_m':[.229,-.13]}
                report,out=self.run_cases([bad,'missing'])
                self.assertIn('fixture_error',report['rows'][0])
                self.assertTrue(report['rows'][1]['passed'])
                self.assertEqual([path.name for path in (out/'rgb').iterdir()],['missing.png'])
                self.assert_restored()

    def test_duplicate_negative_id_preserves_first_raw_image_and_continues(self):
        cases=[{'id':'same','kind':'missing','initial_xy_m':[.229,-.13]},
               {'id':'same','kind':'fully_occluded','initial_xy_m':[.251,-.13]},
               'missing']
        report,out=self.run_cases(cases)
        self.assertFalse(report['passed'])
        self.assertTrue(report['complete'])
        self.assertTrue(report['rows'][0]['passed'])
        self.assertIn('Duplicate fixture id',report['rows'][1]['fixture_error'])
        self.assertFalse(report['rows'][1]['passed'])
        self.assertTrue(report['rows'][2]['passed'])
        self.assertEqual(len(self.observed),2)
        self.assertNotEqual(self.images[0][0,0,0],self.images[1][0,0,0])
        with Image.open(out/'rgb/same.png') as image:
            np.testing.assert_array_equal(np.asarray(image),self.images[0])
        self.assert_restored()

    def test_negative_id_cannot_overwrite_positive_raw_image(self):
        positive={'id':'same','initial_xy_m':[.24,-.13]}
        cases=[{'id':'same','kind':'missing','initial_xy_m':[.229,-.13]},'missing']

        def estimate(index,state):
            if index==0:
                return LocalizationResult(True,'ok',tuple(state['xy']),(3.,2.),.001,1.)
            return LocalizationResult(False,'target_missing',timestamp_s=1.)

        report,out=self.run_cases(cases,positives=[positive],estimate_factory=estimate)
        self.assertFalse(report['passed'])
        self.assertTrue(report['rows'][0]['passed'])
        self.assertIn('Duplicate fixture id',report['rows'][1]['fixture_error'])
        self.assertTrue(report['rows'][2]['passed'])
        self.assertEqual(len(self.observed),2)
        with Image.open(out/'rgb/same.png') as image:
            np.testing.assert_array_equal(np.asarray(image),self.images[0])
        self.assert_restored()

    def test_chinese_id_is_a_safe_single_filename(self):
        case={'id':'左侧-遮挡_01','kind':'half_occluded','initial_xy_m':[.229,-.13]}
        report,out=self.run_cases([case])
        self.assertTrue(report['passed'])
        self.assertEqual(report['rows'][0]['raw_rgb_path'],'rgb/左侧-遮挡_01.png')
        self.assertTrue((out/'rgb/左侧-遮挡_01.png').is_file())
        self.assert_restored()

    def test_raw_directory_failure_does_not_allocate_renderer(self):
        mkdir=Path.mkdir

        def fail_raw(path,*args,**kwargs):
            if path.name=='rgb':
                raise OSError('raw directory unavailable')
            return mkdir(path,*args,**kwargs)

        with patch.object(Path,'mkdir',new=fail_raw):
            with self.assertRaisesRegex(OSError,'raw directory unavailable'):
                self.run_cases(['missing'])
        self.renderer_factory.assert_not_called()
        self.renderer.close.assert_not_called()

    def test_invalid_result_with_any_pose_field_cannot_pass(self):
        for values in ({'xy_m':(.229,-.13)}, {'pixel_xy':(200.,100.)},
                       {'uncertainty_m':.001}):
            with self.subTest(values=values):
                report,_=self.run_cases(['missing'],estimate_factory=lambda *_:
                    LocalizationResult(False,'target_missing',timestamp_s=1.,**values))
                self.assertFalse(report['passed'])
                self.assertFalse(report['rows'][0]['passed'])
                self.assert_restored()

    def test_downstream_error_restores_geometry_and_closes_renderer(self):
        case={'id':'half','kind':'half_occluded','initial_xy_m':[.229,-.13]}

        def fail(*_):
            raise RuntimeError('localization failed')

        with self.assertRaisesRegex(RuntimeError,'localization failed'):
            self.run_cases([case],estimate_factory=fail)
        self.assert_restored()
        self.renderer.close.assert_called_once_with()


if __name__=='__main__':
    unittest.main()
