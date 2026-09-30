"""Derived SO101 scenes and configuration-space collision checks, in radians.

The original MJCF/STLs remain unchanged. MuJoCo uses convex collision hulls
for these meshes; libccd separation distances are approximate diagnostics,
not calibrated physical clearances or a hardware safety guarantee.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


JOINT_NAMES = (
    "shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex",
    "wrist_roll", "gripper",
)


def _vector(value, length: int, field: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{field} must contain {length} finite numbers")
    return result


def _numbers(values) -> str:
    return " ".join(format(float(value), ".17g") for value in values)


def _add_visible_environment_copy(world: ET.Element, geom: ET.Element,
                                  existing_names: set[str]) -> None:
    """Show world obstacles without making their visual copies collide.

    Renderer hides collision group 3 by default. Copy only the table/boxes
    into visible group 2; the existing robot already has visual meshes.
    """
    name = f"visible_{geom.get('name')}"
    if name in existing_names:
        raise ValueError(f"Visible environment geom name already exists: {name}")
    visible = copy.deepcopy(geom)
    visible.set("name", name)
    visible.set("group", "2")
    visible.set("contype", "0")
    visible.set("conaffinity", "0")
    world.append(visible)
    existing_names.add(name)


def build_scene(source: Path, scene_path: Path, obstacles: list[dict], *,
                table_z: float = -0.005) -> mujoco.MjModel:
    """Compile a separate lit scene with static boxes and an anchored base.

    The source has 13 moving-link collision meshes, but only visual meshes on
    its fixed base. Copy those four base mesh/pose definitions into collision
    geoms in this derived file; do not substitute a coarse bounding box.
    """
    source, scene_path = Path(source).resolve(), Path(scene_path).resolve()
    if source == scene_path:
        raise ValueError("The derived scene must not overwrite its source")
    if not math.isfinite(table_z):
        raise ValueError("table_z must be finite")
    scene = ET.parse(source)
    root = scene.getroot()
    compiler = root.find("compiler")
    world, asset = root.find("worldbody"), root.find("asset")
    if compiler is None or world is None or asset is None:
        raise ValueError("Expected SO101 compiler, worldbody and mesh assets")
    meshdir = Path(compiler.get("meshdir", "."))
    compiler.set("meshdir", str((source.parent / meshdir).resolve()))

    collision_default = root.find(".//default[@class='collision']/geom")
    if collision_default is None:
        raise ValueError("SO101 collision class is missing")
    collision_default.set("group", "3")
    collision_default.set("contype", "1")
    collision_default.set("conaffinity", "1")

    base = world.find("body[@name='base']")
    if base is None or base.find("joint") is not None:
        raise ValueError("Expected the SO101 base to be fixed to the world")
    if not base.findall("geom[@class='collision']"):
        for geom in list(base.findall("geom[@class='visual']")):
            duplicate = copy.deepcopy(geom)
            duplicate.set("class", "collision")
            duplicate.attrib.pop("name", None)
            base.append(duplicate)

    for body in world.iter("body"):
        for number, geom in enumerate(body.findall("geom[@class='collision']")):
            geom.set("name", geom.get("name", f"collision_{body.get('name')}_{number}"))
            geom.set("group", "3")
            geom.set("contype", "1")
            geom.set("conaffinity", "1")

    # In this model the convex hulls overlap at assembled joints. In particular
    # MuJoCo's parent filter does not suppress the world-welded base/shoulder
    # pair. Apply the same explicit neighbour policy to physics and planning.
    contact = root.find("contact")
    if contact is None:
        contact = ET.SubElement(root, "contact")
    excluded_bodies = {frozenset((x.get("body1"), x.get("body2")))
                       for x in contact.findall("exclude")}
    for parent in world.iter("body"):
        for child in parent.findall("body"):
            names = (parent.get("name"), child.get("name"))
            if frozenset(names) not in excluded_bodies:
                ET.SubElement(contact, "exclude", body1=names[0], body2=names[1])

    option = root.find("option")
    if option is None:
        option = ET.SubElement(root, "option")
    option.set("timestep", "0.002")
    option.set("gravity", "0 0 -9.81")
    flags = option.find("flag")
    if flags is None:
        flags = ET.SubElement(option, "flag")
    # MuJoCo 3.3.7 native CCD returned zero distance for separated wrist/jaw
    # hulls under a pure base-yaw change. libccd preserves the invariant in
    # the real-model regression; keep this choice in the saved scene too.
    flags.set("nativeccd", "disable")
    visual = root.find("visual")
    if visual is None:
        visual = ET.SubElement(root, "visual")
    headlight = visual.find("headlight")
    if headlight is None:
        headlight = ET.SubElement(visual, "headlight")
    headlight.set("diffuse", "0.8 0.8 0.8")
    headlight.set("ambient", "0.4 0.4 0.4")
    if asset.find("texture[@type='skybox']") is None:
        ET.SubElement(asset, "texture", name="planning_skybox", type="skybox",
                      builtin="gradient", rgb1="0.9 0.94 0.98", rgb2="0.6 0.7 0.8",
                      width="512", height="3072")
    ET.SubElement(world, "light", name="planning_light", pos="0 -1 2", dir="0 0 -1")
    existing_names = {g.get("name") for g in world.iter("geom") if g.get("name")}
    if "worktable" in existing_names:
        raise ValueError("The source already contains a worktable")
    table = ET.SubElement(world, "geom", name="worktable", type="plane", group="3",
                          contype="1", conaffinity="1", size="0.6 0.6 0.01",
                          pos=_numbers([0, 0, table_z]), rgba="0.2 0.25 0.3 1")
    existing_names.add("worktable")
    _add_visible_environment_copy(world, table, existing_names)
    for obstacle in obstacles:
        name = obstacle.get("name")
        if not isinstance(name, str) or not name.strip() or name in existing_names:
            raise ValueError("Obstacle names must be nonempty and unique geom names")
        position = _vector(obstacle["pos"], 3, "obstacle pos")
        size = _vector(obstacle["size"], 3, "obstacle half extents")
        rgba = _vector(obstacle.get("rgba", [0.9, 0.25, 0.15, 1]), 4, "obstacle rgba")
        if np.any(size <= 0) or np.any(rgba < 0) or np.any(rgba > 1):
            raise ValueError("Obstacle sizes must be positive; rgba must be within 0..1")
        box = ET.SubElement(world, "geom", name=name, type="box", group="3",
                            contype="1", conaffinity="1", pos=_numbers(position),
                            size=_numbers(size), rgba=_numbers(rgba))
        existing_names.add(name)
        _add_visible_environment_copy(world, box, existing_names)
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene.write(scene_path, encoding="utf-8", xml_declaration=True)
    model = mujoco.MjModel.from_xml_path(str(scene_path))
    if model.nq != 6 or tuple(model.joint(i).name for i in range(model.njnt)) != JOINT_NAMES:
        raise ValueError("Expected the six SO101 hinge joints in canonical order")
    collision_ids = np.flatnonzero(model.geom_group == 3)
    if len(collision_ids) < 18 or np.any(model.geom_contype[collision_ids] == 0) or np.any(
            model.geom_conaffinity[collision_ids] == 0):
        raise ValueError("Expected 13 moving meshes, four base meshes and active scene collisions")
    return model


class CollisionChecker:
    """Sequential FK/distance checks using an MjData independent of execution.

    Same-body parts and directly connected parent/child links are assembled
    neighbours and excluded. The fixed base is mounted on the worktable, so
    only base/worktable contacts are exempt. No nonadjacent robot pair is
    whitelisted, and the fixed base remains checked against every obstacle.
    ``excluded_pairs`` records each concrete exclusion for report provenance.
    """

    def __init__(self, model: mujoco.MjModel, *, gripper: float = 0.35,
                 margin_m: float = 0.002):
        if model.nq != 6 or model.njnt != 6:
            raise ValueError("CollisionChecker expects the six-joint SO101 model")
        if not math.isfinite(gripper) or not math.isfinite(margin_m) or margin_m < 0:
            raise ValueError("Fixed gripper and nonnegative clearance margin must be finite")
        self.model, self.gripper, self.margin_m = model, float(gripper), float(margin_m)
        self.data = mujoco.MjData(model)
        self.bounds = np.array(model.jnt_range[:5], copy=True)
        if not np.all(model.jnt_limited) or not model.jnt_range[5, 0] <= gripper <= model.jnt_range[5, 1]:
            raise ValueError("All six joints need limits and the fixed gripper must be within them")
        collision_ids = [int(i) for i in np.flatnonzero(model.geom_group == 3)]
        if not collision_ids or any(model.geom_contype[i] == 0 or model.geom_conaffinity[i] == 0
                                    for i in collision_ids):
            raise ValueError("Collision geoms must have active masks")
        self.pairs: list[tuple[int, int]] = []
        self.excluded_pairs: list[dict] = []
        self._names = {i: model.geom(i).name or f"geom_{i}" for i in collision_ids}
        for index, first in enumerate(collision_ids):
            first_body = int(model.geom_bodyid[first])
            for second in collision_ids[index + 1:]:
                second_body = int(model.geom_bodyid[second])
                if first_body == 0 and second_body == 0:
                    continue  # Static scene objects cannot collide with a moving arm by themselves.
                reason = None
                if first_body == second_body:
                    reason = "same_rigid_body"
                elif first_body and second_body and (
                        model.body_parentid[first_body] == second_body or
                        model.body_parentid[second_body] == first_body):
                    reason = "direct_parent_child_joint"
                elif self._mounted_base_table(first, second):
                    reason = "fixed_base_worktable_mount"
                if reason:
                    self.excluded_pairs.append({"pair": [self._names[first], self._names[second]],
                                                "reason": reason})
                elif (int(model.geom_contype[first]) & int(model.geom_conaffinity[second]) or
                      int(model.geom_contype[second]) & int(model.geom_conaffinity[first])):
                    self.pairs.append((first, second))
        if not self.pairs:
            raise ValueError("No robot/environment or nonadjacent self-collision pairs remain")

    def _mounted_base_table(self, first: int, second: int) -> bool:
        for base_geom, table_geom in ((first, second), (second, first)):
            body_id = int(self.model.geom_bodyid[base_geom])
            if (self._names[table_geom] == "worktable" and body_id != 0 and
                    self.model.body(body_id).name == "base" and
                    self.model.body_dofnum[body_id] == 0 and self.model.body_parentid[body_id] == 0):
                return True
        return False

    def evaluate(self, q5orq6, *, require_fixed_gripper: bool = True) -> dict:
        """Check q5 planning poses, or actual q6 execution poses with opt-out.

        When ``require_fixed_gripper=False``, a supplied sixth coordinate is
        checked as measured; it is never silently replaced by the plan value.
        """
        invalid = {"valid": False, "min_distance_m": None, "reason": "invalid_configuration", "pair": None}
        try:
            q = np.asarray(q5orq6, dtype=float)
        except (TypeError, ValueError):
            return invalid
        if q.shape not in ((5,), (6,)) or not np.all(np.isfinite(q)):
            invalid["reason"] = "configuration_shape_or_nonfinite"
            return invalid
        q = np.append(q, self.gripper) if q.shape == (5,) else q.copy()
        if require_fixed_gripper and not math.isclose(float(q[5]), self.gripper, rel_tol=0, abs_tol=1e-9):
            invalid["reason"] = "gripper_not_fixed"
            return invalid
        if np.any(q < self.model.jnt_range[:, 0]) or np.any(q > self.model.jnt_range[:, 1]):
            invalid["reason"] = "joint_limit"
            return invalid
        self.data.qpos[:] = q
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)
        nearest_distance, nearest_pair = float("inf"), None
        for first, second in self.pairs:
            distance = float(mujoco.mj_geomDistance(self.model, self.data, first, second, 1.0, None))
            if not math.isfinite(distance):
                invalid["reason"] = "nonfinite_geometry_distance"
                return invalid
            if distance < nearest_distance:
                nearest_distance, nearest_pair = distance, (first, second)
        valid = nearest_distance >= self.margin_m
        reason = "clear"
        if not valid:
            bodies = [int(self.model.geom_bodyid[i]) for i in nearest_pair]
            names = [self._names[i] for i in nearest_pair]
            reason = "self_collision" if all(bodies) else (
                "table_collision" if "worktable" in names else "obstacle_collision")
        return {"valid": valid, "min_distance_m": nearest_distance, "reason": reason,
                "pair": [self._names[i] for i in nearest_pair]}

    def is_valid(self, q5) -> bool:
        return bool(self.evaluate(q5)["valid"])
