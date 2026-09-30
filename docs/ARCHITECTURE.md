# SO101 architecture

跟随器Web应用位于mint_follower_demo，项目根由实际文件位置解析；默认ROS场景与workspace路径均在本项目内。场景工具从自身位置解析动作和映射文件，不再绑定个人桌面目录。

so101.sh是统一入口，check为纯静态检查，follower启动应用但不执行旧start.sh的fuser/权限修改逻辑。Humble基础环境保留原语义；没有在本轮替换为Jazzy或启动仿真。

嵌套历史/构建产物/私有标定原样保留。旧目录是指向此处的兼容软链接，不是另一份源码。

Colab 离线实验位于 `experiments/colab-twin/`。prepare_bundle.py 从现有 MuJoCo 包选取模型、13 个完整 STL和许可证；run_colab.py 分配独立 CPU会话、安装固定依赖、上传、执行、下载并释放会话。run_experiment.py 只操作仿真关节，在派生场景增加工作台与静态方块，用OSMesa输出视频、CSV和指标。该链路不调用跟随器Runtime、ROS或串口。个人设计材料与输出分别位于根local-documents与实验output，两者均被忽略。
