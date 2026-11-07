# 文档索引

## plan/ 计划（面向未来）

- [2026-11-07-功能基线与资产盘点.md](plan/2026-11-07-功能基线与资产盘点.md) — 立项第一步：功能面实测（95 路由 / 226 配置键 / 7 网盘 / 14 搜索源）、资产四级分级（61% 可继承）、三处必须重写、GPLv3 约束
- [2026-11-07-独立版-调研.md](plan/2026-11-07-独立版-调研.md) — 11 个现成项目的 star/许可证/差距对比 + 本地已有实现盘点；结论＝拼装（继承自有 drive/search + 现成基础设施 + 自研业务核心）
- [2026-11-07-P1-重建部署验证.md](test/2026-11-07-P1-重建部署验证.md) — 线上重建镜像 p1：旧库迁移到 alembic 0001、admin 与 4 条旧会话保留、登录链路 e2e 通过；附 6 个 1Panel 新坑与发布 SOP
- [2026-11-07-P1-验收.md](test/2026-11-07-P1-验收.md) — P1 实测证据：165 passed / ruff 0 / 领域层零框架依赖；附验收中审计出的 4 个缺陷与修法
- [2026-11-07-P1-任务书.md](plan/2026-11-07-P1-任务书.md) — P1 交付规格：domain 四文件（media/subscription/resource/task）逐条规则、10 张业务表字段、alembic `CREATE TABLE IF NOT EXISTS` 迁移、三个仓储 Protocol、7 个测试文件名与覆盖点、7 条禁止事项
- [2026-11-07-独立版-架构.md](plan/2026-11-07-独立版-架构.md) — **已冻结**：分层与目录、10 张表的数据模型、资源式 API、任务状态机、并发限流、前端 10 页 IA、8 阶段计划（56 人日）、6 条禁止事项

## test/ 测试证据

- [2026-11-07-部署到法兰克福.md](test/2026-11-07-部署到法兰克福.md) — 已部署到法兰克福 1Panel：容器 `csx-standalone` running，内网 `http://csx-standalone:8000`，`/health`+`/api/v1/meta`+静态资源 89,052B 全 200；含无 SSH 下的 1Panel v2 API 部署手法与 4 个坑
- [2026-11-07-管理员账户与域名.md](test/2026-11-07-管理员账户与域名.md) — P0.5：管理员账户 + scrypt 口令 + 会话 cookie + 登录页；16 项测试全绿；公网 https://csx.xymhh.eu.org 上线（隧道 ingress 26→27 条、CNAME proxied）；含真实浏览器登录/退出走查与 7 个 1Panel 新坑
- 2026-11-07 P0 验收：后端 `pytest` 2 passed / `ruff check` 干净 / `ruff format --check` 18 文件已格式化；前端 `vue-tsc --noEmit` 通过 / `vite build` 产出 89 kB JS + 9.6 kB CSS；本地 uvicorn 起服，`/health`、`/api/v1/meta`、`/`（前端）三个端点均 200

## summary/ 总结与复盘

（待补）
