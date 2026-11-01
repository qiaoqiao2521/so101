# 进度

## Current
木乔名称与24条来源复核已发布；源站／公网验收完成。

## Done
- 名称源码更正为木乔。
- 24条官方来源逐条核对，保留5条ROS挑战页与官方源码替代证据。
- 更新卡片描述、实际核对日期、SO101模型差异、LeRobot安装和现成模型入口、FishBot分支说明、来源和更新记录。
- 内容检查通过；Astro构建13页；生成站内链接检查0缺失。保留既有i18n/404非阻塞构建警告，未借机升级框架。
- 本地5197浏览器验收30/30通过；1440桌面、390与320手机、组合筛选/URL恢复/中文搜索、11指南布局及24外链目标匹配。
- 另行读取首页标题、h1与24个time：均为木乔／2026-11-02，无沐桥；桌面截图已查看。
- GitHub有效账号qiaoqiao2521，目标公开so101，origin fetch/push均正确。

## 发布与独立回读
- 已推送源码提交 `3e2e615d0303b7f76199cad7de054355b1aaa5a6` 至 master、codex/so101-consolidation-20261031、codex/colab-twin-20261001。GitHub API已回读master相同SHA。
- 线上 https://robot.muqiao.fyi/ 当前release为 `so101-3e2e615-20261102`，来自主仓apps/resources。上传52份静态文件及deployment.json，13个HTML页面。
- 原子切换独立静态current；保留上一版 `so101-78991ce-20261101` 和更早版本。未修改Nginx、Cloudflare、域名或机器人服务。
- 源站9项路由HTTP200，包括指南、更新、来源、Pagefind和独立 /demos/gansu-school/。
- 公网浏览器30/30通过；另回读首页h1为木乔、无沐桥、24个核对日期均为2026-11-02；公网deployment.json精确指向源码提交3e2e615。报告在output/resources-refresh-20261102/public-readback.json及apps/resources/output/qa/resources-refresh-20261102-public-results.json。
- 已查看本地桌面与公网手机截图。只有网站内容、链接和UI通过；未声称机器人安装／训练／实机适配验收。

## 清理
停止本轮5197 Astro preview及独立后台浏览器；删除已发布、可重建的本地dist（1,103,662字节）。本轮未创建上传压缩包或分片；保留约3MB来源证据、浏览器报告与截图、现有依赖，以及服务端回滚版本。

## Next
本轮收口。后续按新的官方版本或用户反馈更新；复跑使用apps/resources/README.md的现有入口。

Knowledge=no_reusable_delta：本轮是既有来源复核、版本区分和静态发布流程的应用；版本现状写在项目中，不增建知识或记忆文件。

## 执行记录
编辑脚本首次从应用目录执行时使用了仓库相对路径，读取失败，未改内容；已纠正工作目录并重新执行编辑及完整相关构建。早期仅品牌构建不作为内容复核完成证据。
外部AGY实际超时一次，内置子Agent已完成相同只读任务；无外部成功或回调恢复声明。
