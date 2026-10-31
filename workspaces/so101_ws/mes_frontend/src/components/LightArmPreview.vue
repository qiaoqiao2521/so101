<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { createWorkbenchPose, degToRad } from '../lib/fixedActionWorkbench.js';

const props = defineProps({
  pose: { type: Object, required: true },
});

const host = ref(null);
const tcpLabel = ref('X 0.000 / Y 0.000 / Z 0.000');
const activeView = ref('iso');
const gripperLabel = computed(() => Number(props.pose?.joints?.gripper ?? 0).toFixed(2));

const viewPresets = {
  iso: { label: 'ISO', position: [1.7, 1.35, 1.7], target: [0, 0.64, 0] },
  front: { label: 'FRONT', position: [0, 0.78, 2.85], target: [0, 0.58, 0] },
  side: { label: 'SIDE', position: [2.85, 0.78, 0], target: [0, 0.58, 0] },
  top: { label: 'TOP', position: [0.02, 3.2, 0.02], target: [0, 0.42, 0] },
};

let renderer;
let scene;
let camera;
let controls;
let resizeObserver;
let visibilityObserver;
let frameId = 0;
let liveArm;
let ghostArm;
let isPreviewVisible = true;

function createArmMaterial(color, opacity = 1) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.42,
    metalness: 0.14,
    transparent: opacity < 1,
    opacity,
  });
}

function createCylinderBetweenY(radius, height, material, radialSegments = 24) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, radialSegments), material);
  mesh.position.y = height / 2;
  return mesh;
}

function createSideDisk(radius, depth, material, side) {
  const disk = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, depth, 32), material);
  disk.rotation.x = Math.PI / 2;
  disk.position.z = side * 0.055;
  return disk;
}

function createBoltRing(radius, material, count = 8) {
  const ring = new THREE.Group();
  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2;
    const bolt = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.008, 10), material);
    bolt.position.set(Math.cos(angle) * radius, 0.076, Math.sin(angle) * radius);
    ring.add(bolt);
  }
  return ring;
}

function createLinkAssembly(length, materialArm, materialAccent, radius = 0.043) {
  const group = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(radius, Math.max(0.04, length - radius * 2), 8, 22), materialArm);
  body.position.y = length / 2;
  group.add(body);

  const railLeft = createCylinderBetweenY(0.012, length * 0.84, materialAccent, 16);
  const railRight = createCylinderBetweenY(0.012, length * 0.84, materialAccent, 16);
  railLeft.position.set(-0.058, length * 0.08, 0.038);
  railRight.position.set(0.058, length * 0.08, 0.038);
  group.add(railLeft, railRight);

  const braceCount = 3;
  for (let i = 0; i < braceCount; i += 1) {
    const brace = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.012, 0.022), materialAccent);
    brace.position.set(0, length * (0.22 + i * 0.24), 0.038);
    group.add(brace);
  }
  return group;
}

function createFinger(material, side) {
  const finger = new THREE.Group();
  const stem = new THREE.Mesh(new THREE.BoxGeometry(0.016, 0.09, 0.018), material);
  stem.position.set(side * 0.032, 0.045, 0);
  const pad = new THREE.Mesh(new THREE.BoxGeometry(0.026, 0.032, 0.034), material);
  pad.position.set(side * 0.042, 0.102, 0);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.012, 12, 12), material);
  tip.position.set(side * 0.044, 0.124, 0);
  finger.add(stem, pad, tip);
  return finger;
}

function createArmRig({ colorSet, opacity = 1 }) {
  const rig = new THREE.Group();
  const materialBase = createArmMaterial(colorSet.base, opacity);
  const materialArm = createArmMaterial(colorSet.arm, opacity);
  const materialAccent = createArmMaterial(colorSet.accent, opacity);

  const basePlate = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.21, 0.035, 48), materialBase);
  basePlate.position.y = 0.0175;
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 0.14, 48), materialBase);
  base.position.y = 0.105;
  const baseCollar = new THREE.Mesh(new THREE.TorusGeometry(0.126, 0.012, 10, 48), materialAccent);
  baseCollar.rotation.x = Math.PI / 2;
  baseCollar.position.y = 0.178;
  rig.add(basePlate, base, baseCollar, createBoltRing(0.158, materialAccent));

  const yawGroup = new THREE.Group();
  yawGroup.position.y = 0.14;
  rig.add(yawGroup);

  const shoulderHousing = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.088, 0.17), materialBase);
  shoulderHousing.position.y = 0.04;
  const shoulderLeftDisk = createSideDisk(0.062, 0.026, materialAccent, 1);
  const shoulderRightDisk = createSideDisk(0.062, 0.026, materialAccent, -1);
  shoulderLeftDisk.position.y = 0.08;
  shoulderRightDisk.position.y = 0.08;
  yawGroup.add(shoulderHousing, shoulderLeftDisk, shoulderRightDisk);

  const shoulderLift = new THREE.Group();
  shoulderLift.position.y = 0.08;
  yawGroup.add(shoulderLift);

  const upperLength = 0.34;
  const upperArm = createLinkAssembly(upperLength, materialArm, materialAccent, 0.044);
  shoulderLift.add(upperArm);

  const elbow = new THREE.Group();
  elbow.position.y = upperLength;
  shoulderLift.add(elbow);

  const elbowJoint = new THREE.Mesh(new THREE.SphereGeometry(0.055, 24, 24), materialAccent);
  const elbowLeftDisk = createSideDisk(0.066, 0.026, materialBase, 1);
  const elbowRightDisk = createSideDisk(0.066, 0.026, materialBase, -1);
  elbow.add(elbowJoint, elbowLeftDisk, elbowRightDisk);

  const forearmLength = 0.3;
  const forearm = createLinkAssembly(forearmLength, materialArm, materialAccent, 0.037);
  elbow.add(forearm);

  const wristFlex = new THREE.Group();
  wristFlex.position.y = forearmLength;
  elbow.add(wristFlex);

  const wristShell = new THREE.Mesh(new THREE.CapsuleGeometry(0.041, 0.09, 8, 20), materialAccent);
  wristShell.position.y = 0.08;
  const wristBand = new THREE.Mesh(new THREE.TorusGeometry(0.044, 0.006, 8, 32), materialBase);
  wristBand.rotation.x = Math.PI / 2;
  wristBand.position.y = 0.158;
  wristFlex.add(wristShell, wristBand);

  const wristRoll = new THREE.Group();
  wristRoll.position.y = 0.16;
  wristFlex.add(wristRoll);

  const wristTool = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.16, 24), materialBase);
  wristTool.position.y = 0.08;
  const toolCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.044, 0.038, 0.035, 24), materialAccent);
  toolCollar.position.y = 0.025;
  wristRoll.add(wristTool, toolCollar);

  const gripper = new THREE.Group();
  gripper.position.y = 0.16;
  wristRoll.add(gripper);

  const palm = new THREE.Mesh(new THREE.BoxGeometry(0.095, 0.035, 0.052), materialBase);
  palm.position.y = 0.03;
  const leftFinger = createFinger(materialAccent, 1);
  const rightFinger = createFinger(materialAccent, -1);
  gripper.add(palm, leftFinger, rightFinger);

  const tcpMarker = new THREE.Mesh(new THREE.SphereGeometry(0.024, 18, 18), materialAccent);
  tcpMarker.position.y = 0.12;
  gripper.add(tcpMarker);

  return {
    rig,
    yawGroup,
    shoulderLift,
    elbow,
    wristFlex,
    wristRoll,
    leftFinger,
    rightFinger,
    tcpMarker,
  };
}

function enableRigShadows(armRig) {
  armRig?.rig?.traverse((node) => {
    if (node.isMesh) {
      node.castShadow = true;
      node.receiveShadow = true;
    }
  });
}

function updateRigFromPose(target, poseLike) {
  if (!target || !poseLike?.joints) {
    return;
  }
  const joints = poseLike.joints;
  target.yawGroup.rotation.y = degToRad(joints.shoulder_panDeg || 0);
  target.shoulderLift.rotation.z = -degToRad(joints.shoulder_liftDeg || 0);
  target.elbow.rotation.z = degToRad(joints.elbow_flexDeg || 0);
  target.wristFlex.rotation.z = -degToRad(joints.wrist_flexDeg || 0);
  target.wristRoll.rotation.y = degToRad(joints.wrist_rollDeg || 0);

  const normalizedGrip = THREE.MathUtils.clamp(Number(joints.gripper || 0) / 1.2, 0, 1);
  const gripOffset = 0.028 + normalizedGrip * 0.035;
  target.leftFinger.position.x = gripOffset;
  target.rightFinger.position.x = -gripOffset;
  target.leftFinger.rotation.z = -normalizedGrip * 0.08;
  target.rightFinger.rotation.z = normalizedGrip * 0.08;
}

function refreshTcpLabel() {
  if (!liveArm) {
    return;
  }
  const worldPosition = new THREE.Vector3();
  liveArm.tcpMarker.getWorldPosition(worldPosition);
  tcpLabel.value = `X ${worldPosition.x.toFixed(3)} / Y ${worldPosition.y.toFixed(3)} / Z ${worldPosition.z.toFixed(3)}`;
}

function resizeRenderer() {
  if (!host.value || !renderer || !camera) {
    return;
  }
  const width = host.value.clientWidth;
  const height = host.value.clientHeight;
  if (!width || !height) {
    return;
  }
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function setCameraView(viewName) {
  const preset = viewPresets[viewName] || viewPresets.iso;
  activeView.value = viewName;
  if (!camera || !controls) {
    return;
  }
  camera.position.set(...preset.position);
  controls.target.set(...preset.target);
  controls.update();
  refreshTcpLabel();
}

function animate() {
  if (!renderer || !scene || !camera) {
    return;
  }
  if (!isPreviewVisible) {
    frameId = 0;
    return;
  }
  controls?.update();
  renderer.render(scene, camera);
  frameId = window.requestAnimationFrame(animate);
}

function startAnimationLoop() {
  if (!frameId && isPreviewVisible) {
    animate();
  }
}

function stopAnimationLoop() {
  if (frameId) {
    window.cancelAnimationFrame(frameId);
    frameId = 0;
  }
}

onMounted(() => {
  if (!host.value) {
    return;
  }

  scene = new THREE.Scene();
  scene.background = new THREE.Color('#f4f7fb');
  scene.fog = new THREE.Fog('#f4f7fb', 2.8, 6.8);

  camera = new THREE.PerspectiveCamera(38, 1, 0.1, 30);
  camera.position.set(...viewPresets.iso.position);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power', preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  host.value.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(...viewPresets.iso.target);
  controls.minDistance = 0.9;
  controls.maxDistance = 4.8;
  controls.maxPolarAngle = Math.PI * 0.5;

  scene.add(new THREE.HemisphereLight('#fff9ff', '#c8bde8', 1.3));
  const keyLight = new THREE.DirectionalLight('#ffffff', 1.35);
  keyLight.position.set(2.4, 3.2, 1.8);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(1024, 1024);
  keyLight.shadow.camera.near = 0.5;
  keyLight.shadow.camera.far = 8;
  keyLight.shadow.camera.left = -2.5;
  keyLight.shadow.camera.right = 2.5;
  keyLight.shadow.camera.top = 2.5;
  keyLight.shadow.camera.bottom = -2.5;
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight('#c9a8e8', 0.7);
  fillLight.position.set(-2.2, 1.6, -1.4);
  scene.add(fillLight);

  const grid = new THREE.GridHelper(2.8, 20, '#a892d9', '#ded6ee');
  grid.position.y = 0;
  scene.add(grid);

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(1.28, 48),
    new THREE.MeshStandardMaterial({ color: '#f0e8f7', transparent: true, opacity: 0.74, roughness: 0.68 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0.001;
  floor.receiveShadow = true;
  scene.add(floor);

  ghostArm = createArmRig({
    colorSet: {
      base: '#c8d4df',
      arm: '#ded6ee',
      accent: '#cdb8df',
    },
    opacity: 0.34,
  });
  updateRigFromPose(ghostArm, createWorkbenchPose(1));
  enableRigShadows(ghostArm);
  scene.add(ghostArm.rig);

  liveArm = createArmRig({
    colorSet: {
      base: '#5d4fa0',
      arm: '#7b6cc9',
      accent: '#c9a8e8',
    },
  });
  enableRigShadows(liveArm);
  scene.add(liveArm.rig);
  updateRigFromPose(liveArm, props.pose);
  setCameraView('iso');
  refreshTcpLabel();
  resizeRenderer();

  resizeObserver = new ResizeObserver(() => resizeRenderer());
  resizeObserver.observe(host.value);

  visibilityObserver = new IntersectionObserver(
    ([entry]) => {
      isPreviewVisible = Boolean(entry?.isIntersecting);
      if (isPreviewVisible) {
        resizeRenderer();
        refreshTcpLabel();
        startAnimationLoop();
      } else {
        stopAnimationLoop();
      }
    },
    {
      rootMargin: '120px 0px 120px 0px',
      threshold: 0.01,
    },
  );
  visibilityObserver.observe(host.value);

  startAnimationLoop();
});

watch(
  () => props.pose,
  (poseValue) => {
    updateRigFromPose(liveArm, poseValue);
    refreshTcpLabel();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  stopAnimationLoop();
  resizeObserver?.disconnect();
  visibilityObserver?.disconnect();
  controls?.dispose();
  renderer?.dispose();
  if (renderer?.domElement?.parentNode) {
    renderer.domElement.parentNode.removeChild(renderer.domElement);
  }
});
</script>

<template>
  <section class="light-preview-card">
    <div class="light-preview-toolbar" aria-label="机械臂视角预设">
      <button
        v-for="(preset, key) in viewPresets"
        :key="key"
        class="btn-ghost light-view-button"
        :class="{ 'light-view-button-active': activeView === key }"
        type="button"
        @click="setCameraView(key)"
      >
        {{ preset.label }}
      </button>
    </div>
    <div ref="host" class="light-preview-canvas" />
    <div class="light-preview-meta">
      <div>
        <span>TCP 估计</span>
        <strong>{{ tcpLabel }}</strong>
      </div>
      <div>
        <span>夹爪开合</span>
        <strong>{{ gripperLabel }}</strong>
      </div>
      <div>
        <span>参考姿态</span>
        <strong>灰色为 Home，对照当前蓝色姿态</strong>
      </div>
    </div>
  </section>
</template>
