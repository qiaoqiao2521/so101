# 沐桥机器人资料库

SO101 与 FishBot 的公开学习入口、官方资源导航和资料交付说明。
网站地址：https://robot.muqiao.fyi/

此应用迁入主仓库 `apps/resources/`。资料站继续独立构建成静态文件，机器人控制、ROS 与仿真运行环境不进入网站。

## 本地运行

条件：Node >=22.22.0，npm >=9.6.5。从应用目录执行：

```sh
cd apps/resources
npm ci
npm run check:content
npm run build
npm run check:build
npm run preview -- --host 127.0.0.1 --port 5192
```

全文搜索索引在生产构建时生成，使用 preview 验收搜索。
可选浏览器验收脚本 `tests/browser_acceptance.py` 依赖当前环境已安装的 `~/.local/bin/browser-bg`；缺少该工具时不得把浏览器检查记为通过。

```sh
python3 tests/browser_acceptance.py http://127.0.0.1:5192 --label local
```

截图与报告保存在忽略的 `output/qa/`。

## 内容维护

- 资源记录在 `src/data/resources.json`；保留官方来源与核查日期。
- 指南、更新、来源与交付说明在 `src/content/docs/`。
- 修改目录时同步 `astro.config.mjs`，然后运行内容检查和构建。
- 私人记录、地图、标定、日志与付费文件不放入公开内容。

## 路径与来源

本站继续以现有域名根路径部署，保留 `/so101/`、`/fishbot/`、`/delivery/`、`/sources/` 与 `/pagefind/`。Git 目录改为 `apps/resources/` 不意味着网站 URL 增加 `/resources/`；若将来改变 URL 前缀，必须同时调整 Astro base、全部根路径链接、静态资源、搜索索引和浏览器验收。

源仓库：`qiaoqiao2521/robot-resource-site`，源提交 `d2149d0e7a72016be86c91be55b0aed4df253dbf`。原仓库为私有；用户于2026-11-01明确允许将经过清理的保留源码发布到公开主仓库。原始录制、标定、运维信息和历史备份继续保留在私有位置。

保留 [THIRD_PARTY.md](THIRD_PARTY.md) 的上游来源说明，不新增或推定原创内容许可证。部署模板见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。
