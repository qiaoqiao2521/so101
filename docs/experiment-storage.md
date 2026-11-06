# 历史实验云端归档

SO101已结束实验的大日志、模型快照与旧传输包按原路径归档在私有Google Drive。源码保存在Git，小报告继续留在本地output，另有选定元数据的私有上下文备份；当前网页任务回放、训练数据／检查点和运行库缓存保留本地。归档不改变原实验结论，也不代表重新完成物理验收。

## 2026-11-07 归档

入口：[SO101历史归档](https://drive.google.com/drive/folders/15B-Z4LA6BUavWRFkrnhb32J85X5vdKnU)。需要原素材账号权限；没有开启公开分享。最终数量和验证状态见[迁移进度](../plans/so101-cloud-archive-20261107/progress.md)。

云端`INDEX-实验目录.md`可按235个实验目录查找；`manifest-final.json`记录1,282个原文件、归档对象与回收状态；`README-恢复说明.md`记录恢复命令。先看清单，下载需要的实验，不必恢复整批。

## 按需下载

如果rclone返回共享API配额错误，直接打开上方私有Drive目录，或用已连接素材账号的Drive插件，按`manifest-final.json`给出的对象名下载。无需为API限流重新登录。下载后的tar解包命令与下面相同。全部归档内容已完成云端读回；数量和本地回收状态以最终清单为准。

## 恢复到空目录

以下`REMOTE`使用已经授权到素材盘的rclone remote。此机器已验证为`gdrive2:`；其他机器应先完成自己的授权，不复制凭据。

```bash
REMOTE=gdrive2:
FOLDER=15B-Z4LA6BUavWRFkrnhb32J85X5vdKnU
RECOVERY=/path/to/empty/so101-recovery
mkdir -p "$RECOVERY/log-bundles" "$RECOVERY/repo/experiments/colab-twin/output"
rclone copyto "${REMOTE}manifest-final.json" "$RECOVERY/manifest-final.json" --drive-root-folder-id "$FOLDER"
```

按清单下载指定日志包，然后将其解到空的`repo`目录。包内成员已经包含`experiments/colab-twin/output/`前缀。

```bash
rclone copyto "${REMOTE}log-bundles/batch-001.tar.zst" "$RECOVERY/log-bundles/batch-001.tar.zst" --drive-root-folder-id "$FOLDER"
tar -I 'zstd -d' -xf "$RECOVERY/log-bundles/batch-001.tar.zst" -C "$RECOVERY/repo"
```

旧压缩包不再重压，原字节封装为`existing-bundles/existing-001.tar`等tar包。超过100MiB的tar按90MiB分卷存储，先下载清单列出的全部`.part-00`等分卷。它们同样使用仓库相对路径，解包目标也是空的`repo`目录。

```bash
rclone copy "${REMOTE}existing-bundles" "$RECOVERY" --include 'existing-001.tar.part-*' --drive-root-folder-id "$FOLDER"
cat "$RECOVERY"/existing-001.tar.part-* > "$RECOVERY/existing-001.tar"
tar -xf "$RECOVERY/existing-001.tar" -C "$RECOVERY/repo"
```

`retained-context.tar.zst`是小报告、配置与模型描述的备份，采用仓库相对路径，按需解到空的`repo`目录。不要直接覆盖正在使用的工作树。旧`.json.zst/.rgb.zst/.mjb.zst`可用`zstd -d --keep 文件.zst`恢复原文件名；旧MJB须结合对应模型和当时MuJoCo版本使用，不能保证跨版本直接加载。

当前工作台的`station-tasks`增加云备份并保留本地原件；网页按原UUID读取报告、视频、抓取证据和MCAP。

## 当前A2/A3网页回合备份

云端`current-a2-a3-playback.tar.zst`包含A2成功／取消、A3工位A／B的四个原任务目录和两份中间QA归档。每回合的原UUID、报告、视频、抓取证据与MCAP在同一个任务目录中。它们保留本地，仅增加备份。

该包属于现有FishBot工作台仓库，成员路径以`apps/fishbot-control-station/`开始。恢复时解到该工作台的空恢复根目录，不要放入SO101实验output，也不要混入Mint工作树。运行服务仍使用原工作台入口。
