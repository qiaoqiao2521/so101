> 历史修复报告（2026-06-26）：当时的 spawn 和显示结果仅作为历史记录。本轮静态确认当前 URDF 保留 17 个 mesh visual，但当前 collision 数量为 0；正文“保留 collision”描述历史修改，不描述当前文件。当前仿真和实机未复验。

# Gazebo SO101 视觉显示与 spawn 失败 — 根因分析与修复报告

日期: 2026-06-26
适用: ROS2 Humble + classic Gazebo 11，so101-ros2-arm 工作空间

## 1. 问题描述

启动 `ros2 launch launch_board_with_arms.launch.py`（基于 `so101_description` URDF）后：
- Gazebo gzserver + gzclient 正常启动，板卡世界加载正常
- 两个 SO101 机械臂在 `get_model_list` 中不出现
- `spawn_entity.py` 进程存在但日志为空，看起来"卡住"

直观判断：机械臂**显示成了圆柱体和方块**（像 collision 简化几何），而不是真实 SO101 的 STL visual mesh。

## 2. 根因（共 2 个独立的 bug）

### 根因 A：URDF 的 `<visual>` 被 primitive 覆盖

**实际检查结果（spawwn 用的 URDF）：**
- `/home/muqiao/桌面/dev/ros2/workspaces/so101_ws/src/so101_description/urdf/so101.urdf`
- 头部注释：`<!-- Generated using onshape-to-robot -->`

每个 link 在真实的 STL mesh `<visual>` 之上，被额外叠加了一个 primitive `<visual>`：

| link            | mesh visuals | 多余 primitive visual | collision |
|-----------------|--------------|------------------------|-----------|
| base_link       | 4            | **cylinder** r0.07     | cylinder  |
| shoulder_link   | 3            | **box** 0.09×0.08×0.11 | box       |
| upper_arm_link  | 2            | **box**                | box       |
| lower_arm_link  | 3            | **box**                | box       |
| wrist_link      | 2            | **box**                | box       |
| gripper_link    | 2            | **box**                | box       |
| moving_jaw      | 1            | **box**                | box       |

Gazebo 渲染**所有** `<visual>`。这些 cylinder/box 把真实 STL mesh 盖住 → 看起来像方块/圆柱。

mesh 加载链路本身没问题（13 个 STL 全部存在，单位 = 米，无 scale）。

### 根因 B：lxml 拒绝带 XML 声明的 URDF 字符串

`spawn_entity.py` 读取 URDF 后调用：

```python
xml_parsed = ElementTree.fromstring(entity_xml)   # lxml
```

而用 `ET.write(xml_declaration=True)` 写出的 URDF 包含：

```xml
<?xml version='1.0' encoding='utf-8'?>
```

lxml 抛错：

```
ValueError: Unicode strings with encoding declaration are not supported.
Please use bytes input or XML fragments without declaration.
```

进程崩溃退出（stderr 被吞掉，日志看似"卡住"）。原始 URDF 用的是 `<!-- comment -->` 头，所以原始能 spawn；只要包含 `<?xml?>` 声明就会触发此 bug。

## 3. 修复

### 修复 A：删除所有 primitive `<visual>`（保留 mesh 和 collision）

```python
# Python ET
for v in list(link.findall("visual")):
    geom = v.find("geometry")
    if geom is not None and geom.find("mesh") is None:
        link.remove(v)
```

清理后每个 link 的 visual **只剩真实 STL mesh**（共 17 个），collision 的简化 primitive 正常保留。

### 修复 B：去掉 URDF 的 XML 声明

```python
import re
text = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', text)
```

## 4. 验证

- `check_urdf so101.urdf` 通过，运动链完整：base → shoulder → upper_arm → lower_arm → wrist → gripper
- CLI 直接 `ros2 service call /spawn_entity`（带 SDF 测试方块）→ `success=True`
- CLI 直接 `ros2 run gazebo_ros spawn_entity.py -file urdf -entity m_arm ...` → `Successfully spawned entity [m_arm]`
- `ros2 service call /get_model_list` → 出现 `m_arm`
- 重新运行 `ros2 launch launch_board_with_arms.launch.py`：
  - 两个臂都 `Successfully spawned entity [master_arm]` / `[follower_arm]`
  - `get_model_list` 确认 `master_arm` + `follower_arm` 都在
  - 画面中两臂显示为真实 STL mesh（不是方块/圆柱）

## 5. 备份

原 URDF 保留在：

```
src/so101_description/urdf/so101.urdf.bak_primitive_visual
```

包含 7 个 primitive visual，可恢复。

## 6. 教训

1. URDF 的 `<visual>` 中混用 mesh + primitive 时，Gazebo 会同时渲染两者。简化视觉调试时只能改 collision，**不要在 visual 里加 primitive**。
2. 写 URDF 时不要带 `<?xml?>` 声明，或者用 `ET.write(..., xml_declaration=False)`，或者用 `bytes` 传给 lxml。
3. spawn 失败时优先检查：
   - `python3 -c "import numpy"`（是否 conda python 缺 numpy）
   - URDF 首行是否有 `<?xml?>` 声明
   - 直接 `ros2 service call /spawn_entity` 用最小 SDF 测服务本身