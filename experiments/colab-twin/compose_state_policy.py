"""Attach an unchanged learned gripper to compatible arm-only ACT weights.

This operation performs no optimization. Arm and gripper training identities
remain separate; the top-level identities are their union for archive checks.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

COMPOSITION_FORMAT = "so101-state-policy-composition-v1"


def _sha(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("Composition requires valid SHA256 identities")
    return value


def _hashes(values):
    if not isinstance(values, list) or not values or len(set(values)) != len(values):
        raise ValueError("Composition training hashes must be a nonempty unique list")
    return [_sha(value) for value in values]


def _json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def state_dict_sha256(state):
    """Bind tensor names, shapes, dtypes and exact bytes, without pickle order."""
    if not isinstance(state, dict) or not state:
        raise ValueError("Composition requires a nonempty tensor state dictionary")
    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name]
        if not isinstance(value, torch.Tensor) or not torch.isfinite(value).all():
            raise ValueError("Composition requires finite tensor weights")
        value = value.detach().cpu().contiguous()
        descriptor = json.dumps([name, str(value.dtype), list(value.shape)], separators=(",", ":"))
        digest.update(descriptor.encode() + b"\0")
        digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _component_sha(component):
    metadata = {key: value for key, value in component.items() if key != "state_dict"}
    return _json_sha({"metadata": metadata, "state_dict_sha256": state_dict_sha256(component["state_dict"])})


def _contract(data):
    # Delay these imports: the normal loader imports this validator for explicit
    # compositions only, while legacy checkpoint admission remains unchanged.
    from learning_data import SCHEMA_VERSION
    from learning_models import ACTION, ENV_STATE, STATE, ACTION_ENCODING_SEMANTICS, LEROBOT_REVISION, ModelSpec

    spec = ModelSpec(**data["model_spec"])
    if (data.get("format") != "so101-state-policy-v1" or data.get("schema_version") != SCHEMA_VERSION
            or spec.model != "act" or spec.use_vae or spec.dropout != 0
            or (spec.state_dim, spec.environment_dim, spec.action_dim) != (6, 30, 6)
            or spec.action_encoding != "arm_delta" or data.get("action_encoding") != "arm_delta"
            or data.get("action_encoding_semantics") != ACTION_ENCODING_SEMANTICS["arm_delta"]
            or data.get("lerobot_revision") != LEROBOT_REVISION):
        raise ValueError("Composition requires the compatible deterministic state ACT specification/action encoding")
    options = data.get("normalization_options", {})
    floor = options.get("velocity_scale_floor_rad_s")
    if (set(options) != {"velocity_scale_floor_rad_s", "robot_velocity_mask", "object_velocity_mask"}
            or options.get("robot_velocity_mask") is not True or options.get("object_velocity_mask") is not False
            or isinstance(floor, bool) or not isinstance(floor, (int, float))
            or not np.isfinite(floor) or floor < 0):
        raise ValueError("Composition requires unchanged robot-only masking and normalization options")
    statistics = data["normalization"]
    if set(statistics) != {STATE, ENV_STATE, ACTION}:
        raise ValueError("Composition normalization must contain only state/environment/action")
    for key, width in ((STATE, 6), (ENV_STATE, 30), (ACTION, 6)):
        if set(statistics[key]) != {"mean", "std"}:
            raise ValueError("Composition normalization statistic fields differ")
        for name in ("mean", "std"):
            values = np.asarray(statistics[key][name], dtype=float)
            if values.shape != (width,) or not np.isfinite(values).all() or name == "std" and np.any(values <= 0):
                raise ValueError("Invalid composition normalization: " + key + "." + name)
    if data.get("control_period_s") != .02:
        raise ValueError("Composition control period must remain 20 ms")
    _sha(data.get("model_sha256"))
    training = _hashes(data.get("train_dataset_sha256"))
    validation = data.get("validation_dataset_sha256", [])
    if not isinstance(validation, list) or set(training) & set(validation):
        raise ValueError("Composition training/validation identities overlap")
    origin = _hashes(data.get("normalization_source", {}).get("training_dataset_sha256"))
    if not set(origin) <= set(training):
        raise ValueError("Composition normalization origins must belong to training")
    return {key: copy.deepcopy(data[key]) for key in (
        "format", "schema_version", "model_spec", "action_encoding", "action_encoding_semantics",
        "lerobot_revision", "model_sha256", "control_period_s", "normalization", "normalization_options")}


def validate_composed_policy_metadata(data):
    """Verify separated provenance before allowing an old head training subset."""
    provenance = data.get("composition", {})
    if (provenance.get("format") != COMPOSITION_FORMAT
            or provenance.get("operation") != "reuse_learned_gripper_without_optimization"):
        raise ValueError("Unsupported explicit policy composition provenance")
    arm, head = provenance["arm"], provenance["gripper"]
    _sha(arm["checkpoint_sha256"])
    _sha(head["checkpoint_sha256"])
    _sha(head["original_base_checkpoint_sha256"])
    arm_hashes, head_hashes = _hashes(arm["train_dataset_sha256"]), _hashes(head["train_dataset_sha256"])
    union = list(dict.fromkeys(arm_hashes + head_hashes))
    if not set(head_hashes) <= set(arm_hashes) or data.get("train_dataset_sha256") != union:
        raise ValueError("Composition top-level training hashes must equal the arm/head union")
    if data.get("training_loss_scope") != "arm5_only":
        raise ValueError("Composition arm must retain the arm-only training loss scope")
    if _json_sha(_contract(data)) != provenance["compatible_contract_sha256"]:
        raise ValueError("Composition specification, physical identity, mask or normalization differs")
    if state_dict_sha256(data["state_dict"]) != arm["state_dict_sha256"]:
        raise ValueError("Composition arm tensor identity differs")
    component = data["learned_gripper_classifier"]
    if (component.get("train_dataset_sha256") != head_hashes
            or component.get("input_statistics_training_dataset_sha256") != head_hashes
            or component.get("base_checkpoint_sha256") != head["original_base_checkpoint_sha256"]
            or _component_sha(component) != head["component_sha256"]):
        raise ValueError("Composition changed the original gripper weights, statistics or training provenance")
    if component.get("input_transform", {}).get("base_normalization_options") != data["normalization_options"]:
        raise ValueError("Composition gripper input normalization/masking differs")
    if (data.get("initialization", {}).get("checkpoint_sha256") != head["original_base_checkpoint_sha256"]
            or data.get("initialization") != arm["initialization"]):
        raise ValueError("Composition arm initialization differs from the original gripper base")
    origin = data["normalization_source"]["training_dataset_sha256"]
    if (origin != arm["normalization_source"]["training_dataset_sha256"]
            or origin != head["normalization_source"]["training_dataset_sha256"]):
        raise ValueError("Composition changed original normalization training identities")
    return head_hashes


def compose_metadata(arm, gripper, *, arm_sha256, gripper_sha256):
    """Build a composition from two separately validated local checkpoint files."""
    if "composition" in arm or "learned_gripper_classifier" in arm or "composition" in gripper:
        raise ValueError("Composition requires a raw arm-only checkpoint and an original gripper checkpoint")
    if arm.get("training_loss_scope") != "arm5_only":
        raise ValueError("Composition requires arm-only supervised weights")
    arm_contract, head_contract = _contract(arm), _contract(gripper)
    if arm_contract != head_contract:
        raise ValueError("Arm and gripper specification, physics, normalization or masks differ")
    component = gripper["learned_gripper_classifier"]
    head_hashes = _hashes(component.get("train_dataset_sha256"))
    if head_hashes != gripper["train_dataset_sha256"]:
        raise ValueError("Original gripper and checkpoint training hashes differ")
    if gripper.get("initialization", {}).get("base_checkpoint_sha256") != component.get("base_checkpoint_sha256"):
        raise ValueError("Original gripper base checkpoint provenance differs")
    result = copy.deepcopy(arm)
    result["learned_gripper_classifier"] = copy.deepcopy(component)
    result["train_dataset_sha256"] = list(dict.fromkeys(arm["train_dataset_sha256"] + head_hashes))
    result["gripper_output_scope"] = "unchanged learned gripper classifier from a separate source checkpoint"
    result["policy_architecture"] = {
        "kind": "finetuned_official_act_arm_plus_unchanged_learned_state_gripper",
        "classifier_architecture": copy.deepcopy(component["architecture"]),
        "input_keys": copy.deepcopy(component["input_keys"]),
        "inputs_are_base_normalized_and_masked": True,
        "base_normalization_options": copy.deepcopy(arm["normalization_options"]),
        "classes_rad": copy.deepcopy(component["classes_rad"]),
        "base_checkpoint_sha256": _sha(arm_sha256),
        "classifier_original_base_checkpoint_sha256": component["base_checkpoint_sha256"],
        "classifier_source_checkpoint_sha256": _sha(gripper_sha256),
        "classifier_source_sha256": component["source_sha256"],
    }
    result["composition"] = {
        "format": COMPOSITION_FORMAT, "operation": "reuse_learned_gripper_without_optimization",
        "compatible_contract_sha256": _json_sha(arm_contract),
        "arm": {"checkpoint_sha256": _sha(arm_sha256), "state_dict_sha256": state_dict_sha256(arm["state_dict"]),
                "train_dataset_sha256": copy.deepcopy(arm["train_dataset_sha256"]),
                "initialization": copy.deepcopy(arm["initialization"]),
                "normalization_source": copy.deepcopy(arm["normalization_source"])},
        "gripper": {"checkpoint_sha256": _sha(gripper_sha256), "component_sha256": _component_sha(component),
                    "train_dataset_sha256": copy.deepcopy(head_hashes),
                    "original_base_checkpoint_sha256": component["base_checkpoint_sha256"],
                    "normalization_source": copy.deepcopy(gripper["normalization_source"])},
    }
    validate_composed_policy_metadata(result)
    return result


def compose(args):
    from learning_models import ENV_STATE, STATE, load_policy_checkpoint

    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"status": "failed", "operation": "checkpoint_composition_only", "task_acceptance": "not_run"}
    try:
        arm = torch.load(args.arm_checkpoint, map_location="cpu", weights_only=True)
        gripper = torch.load(args.gripper_checkpoint, map_location="cpu", weights_only=True)
        arm_sha = hashlib.sha256(args.arm_checkpoint.read_bytes()).hexdigest()
        gripper_sha = hashlib.sha256(args.gripper_checkpoint.read_bytes()).hexdigest()
        combined = compose_metadata(arm, gripper, arm_sha256=arm_sha, gripper_sha256=gripper_sha)
        new_arm, _, _ = load_policy_checkpoint(str(args.arm_checkpoint), "cpu")
        old_head, _, _ = load_policy_checkpoint(str(args.gripper_checkpoint), "cpu")
        path = args.output / "policy.pt"
        torch.save(combined, path)
        restored, _, _ = load_policy_checkpoint(str(path), "cpu")
        batch = {STATE: torch.zeros(2, 6), ENV_STATE: torch.zeros(2, 30)}
        with torch.no_grad():
            actual = restored.predict_action_chunk(batch)
            expected_arm = new_arm.predict_action_chunk(batch)
            expected_head = old_head.predict_action_chunk(batch)
        if (not torch.equal(actual[..., :5], expected_arm[..., :5])
                or not torch.equal(actual[..., 5], expected_head[..., 5])):
            raise RuntimeError("Composition reload changed independent arm/gripper inference")
        report.update(status="completed_composition", composition=combined["composition"],
                      checked_arm_tensors=len(arm["state_dict"]),
                      checked_gripper_tensors=len(gripper["learned_gripper_classifier"]["state_dict"]),
                      arm_tensors_unchanged=True, gripper_component_unchanged=True,
                      normalization_unchanged=True, reload_arm_max_abs_error=0., reload_gripper_max_abs_error=0.,
                      checkpoint={"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["total_s"] = time.perf_counter() - started
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-checkpoint", type=Path, required=True)
    parser.add_argument("--gripper-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    report = compose(args)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "completed_composition" else 1


if __name__ == "__main__":
    raise SystemExit(main())
