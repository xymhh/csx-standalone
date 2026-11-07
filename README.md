# CloudSubscribeX 独立版

把 `CloudSubscribeX`（原 MoviePilot 插件）重做成**不依赖 MoviePilot** 的独立项目：自有后端、自有 UI、重新设计的架构与界面。

> 状态：**P0.5 鉴权 + 公网上线完成**（2026-11-07）——管理员账户/会话登录/登录页已上线 https://csx.xymhh.eu.org ，后端 16 项测试全绿、`ruff` 干净，前端 `typecheck` + `build` 通过。

## 快速开始

```bash
# 后端（http://127.0.0.1:8000）
cd backend && pip install -e ".[dev]" && uvicorn csx.api.main:app --reload

# 前端（http://127.0.0.1:5173，已配 /api 代理）
cd web && npm install --include=dev && npm run dev

# 单容器
docker compose up --build
```

## 为什么要有这个项目

原插件跑在 MoviePilot 进程里，43 个文件直接挂在宿主内脏上（订阅表、整理链、片名识别），MP 每次大版本升级都会断。本项目把这些能力收回自己手里。

## 能继承多少

原插件 108,949 行 Python 中，**约 61% 可直接继承**：

| 分层 | 行数 | 处理方式 |
|---|---:|---|
| 网盘驱动（7 家） | 15,165 | 原样搬 |
| 搜索源（14 个） | 24,617 | 原样搬 |
| 自有 SQLite 层 | 3,213 | 原样搬 |
| 订阅源 / utils | 5,714 | 小改 |
| 业务服务 / 路由层 | 17,929 | 改造 |
| 同步整理 / 插件入口 / 其余 | 42,311 | 重写 |

## 鉴权

单用户管理员账户，其余接口全部需要登录。

| 环境变量 | 默认 | 说明 |
| --- | --- | --- |
| `CSX_ADMIN_USER` | `admin` | 首次启动创建的管理员用户名 |
| `CSX_ADMIN_PASSWORD` | 空 | 首次启动用的初始口令；留空则随机生成并写入 `<data_dir>/initial-admin-password.txt`（0600） |
| `CSX_COOKIE_SECURE` | `false` | 走 HTTPS 部署时置 `true`（cookie 加 `Secure`） |
| `CSX_SESSION_TTL_DAYS` | `7` | 会话有效期 |
| `CSX_LOGIN_MAX_ATTEMPTS` | `5` | 同一 IP 在窗口内的失败次数上限，超出返回 429 |
| `CSX_LOGIN_WINDOW_SECONDS` | `900` | 失败计数窗口 |

- 口令用标准库 `scrypt`（n=2^14, r=8, p=1，每用户独立 salt）哈希，库里不存明文。
- 会话令牌 32 字节随机串，只把 `sha256` 落库；cookie 为 `HttpOnly + SameSite=Lax + Secure`。
- 接口：`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/auth/me`、`POST /api/v1/auth/password`（改密后旧会话全部失效）。
- 白名单只有 `/health` 与 `/api/v1/auth/login`，其余 `/api/*` 未登录一律 401。

## 部署

- 公网：**https://csx.xymhh.eu.org**（Cloudflare 隧道 `berohost` → `http://csx-standalone:8000`）
- 法兰克福 1Panel：容器 `csx-standalone`，内网 `http://csx-standalone:8000`（`1panel-network`，无宿主端口）
- 代码 `/opt/1panel/apps/csx-standalone`，compose `/opt/1panel/docker/compose/csx-standalone/docker-compose.yml`，数据卷 `data:/data`

详见 [部署记录](docs/test/2026-11-07-部署到法兰克福.md) 与 [管理员账户与域名记录](docs/test/2026-11-07-管理员账户与域名.md)。

## 文档

- [功能基线与资产盘点](docs/plan/2026-11-07-功能基线与资产盘点.md) — 95 个路由、226 个配置键、资产分级、许可证约束、5 个待定架构问题
- [调研](docs/plan/2026-11-07-独立版-调研.md) — 11 个现成项目对比，结论＝拼装
- [架构](docs/plan/2026-11-07-独立版-架构.md) — 已冻结：分层、数据模型、API、任务机、前端 10 页、8 阶段 56 人日
- [管理员账户与域名](docs/test/2026-11-07-管理员账户与域名.md) — P0.5 鉴权实现 + 公网上线实测证据

## 许可证

**GPLv3**（用户 2026-11-07 确认）。原项目同为 GPLv3，43,000 行可直接继承；不复制 AGPL 项目代码。
