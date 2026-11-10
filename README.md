# CloudSubscribeX 独立版

CloudSubscribeX 是独立运行的网盘订阅、搜索、转存、媒体整理与 STRM 管理系统，不依赖 MoviePilot。项目按 P0–P7 阶段完成：后端分层与 SQLite 持久化、网盘/搜索源 vendor 迁入、命名与转存编排、鉴权及资源 API、Vue 3 管理台、签到/STRM/通知/媒体服务器集成，以及 P7 备份恢复、崩溃任务自愈和迁移往返演练。

## 快速开始

需要 Python 3.12、Node.js 22（仅开发前端需要）和 Docker（可选）。

```bash
# 后端 API，工作目录为 backend
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export CSX_DATA_DIR="$PWD/data"
export CSX_ADMIN_PASSWORD='请设置强口令'
export CSX_SECRET_KEY='请设置独立的长随机密钥'
uvicorn csx.api.main:app --host 127.0.0.1 --port 8000
```

容器部署推荐把配置写进 `config.json`（见下文「配置」一节），只留一个挂载目录：

```bash
cp config/config.example.json config/config.json   # 改成自己的口令与密钥
docker compose up -d
```

# 前端开发服务器，另开终端
cd web
npm ci --include=dev
npm run dev

# 一体化容器（在项目根目录）
docker compose up --build -d
```

首次启动会自动执行数据库迁移并创建管理员。若未设置 `CSX_ADMIN_PASSWORD`，随机初始口令写入 `<CSX_DATA_DIR>/initial-admin-password.txt`（权限 0600）。生产部署应使用 HTTPS 反向代理、挂载 `/config` 目录持久化数据和配置，并设置强 `CSX_SECRET_KEY`。

## 功能与界面

- 管理台提供 Dashboard、Progress、Baseline、Radar、Candidates、Tasks、History、Media、Settings、Search 十个页面。
- 管理订阅与候选，调度网盘转存任务，跟踪进度与历史；支持命名解析、画质洗版判断、重试和死信状态。
- 支持 P2 vendor 搬运的网盘驱动与搜索源；账号凭据加密存储，API 不回显明文。
- 支持多账号签到及历史、STRM 生成、Webhook/Telegram/飞书通知、Emby/Jellyfin 探测和媒体库刷新。
- **跨盘转存**：资源盘与媒体库盘不同时（如夸克分享 → 115 媒体库），经本地缓存下载后秒传或上传到媒体库盘；缓存目录 `./cache` 挂载到容器 `/cache`，开关与线程数在「设置 → 播放与整理 → 跨盘转存」。
- 系统维护接口支持 SQLite 在线热备和备份清单；恢复可使用 CLI。
- 后端全部测试使用离线 Fake/Mock；带 `net` 标记的真实驱动 smoke 测试默认跳过。

## 配置

配置优先级（高 → 低）：**环境变量（`CSX_` 前缀）→ 工作目录 `.env` → `config.json` → 代码默认值**。

`config.json` 路径默认 `/config/config.json`，可用环境变量 `CSX_CONFIG_FILE` 指定。文件不存在、JSON 损坏或不是对象时静默跳过，不会阻止启动。

```json
{
  "data_dir": "/config",
  "web_dist": "/app/web/dist",
  "admin_user": "admin",
  "admin_password": "请设置强口令",
  "secret_key": "请设置独立的长随机密钥",
  "tmdb_api_key": "",
  "cookie_secure": true,
  "log_level": "INFO"
}
```

容器部署只需挂载一个目录，配置与数据库都在里面：

```yaml
services:
  csx-standalone:
    image: ghcr.io/xymhh/csx-standalone:latest
    environment:
      CSX_CONFIG_FILE: /config/config.json
    volumes:
      - ./config:/config
      - ./strm:/strm
```

### 环境变量速查

环境变量仍然可用且优先级最高，适合临时覆盖。空值代表未设置；列表型配置可按 Pydantic Settings 支持的 JSON 形式提供。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `CSX_DATA_DIR` | `data` | SQLite 数据库、初始管理员口令和默认备份目录所在的数据目录 |
| `CSX_LOG_LEVEL` | `INFO` | 日志等级 |
| `CSX_CORS_ORIGINS` | `http://localhost:5173` | 允许的浏览器来源列表 |
| `CSX_WEB_DIST` | `web/dist` | 已构建前端静态文件目录 |
| `CSX_TRANSFER_ROOT` | `CSX` | 网盘转存根目录 |
| `CSX_LIBRARY_ROOT` | 空 | 整理后的媒体库根目录 |
| `CSX_SECRET_KEY` | 空 | 账号凭据加密密钥；配置账号前必须设置并长期保管 |
| `CSX_ADMIN_USER` | `admin` | 首次启动建立的管理员用户名 |
| `CSX_ADMIN_PASSWORD` | 空 | 首次启动管理员口令；留空时生成随机口令文件 |
| `CSX_COOKIE_SECURE` | `false` | HTTPS 部署设为 `true`，让登录 cookie 带 Secure 属性 |
| `CSX_SESSION_TTL_DAYS` | `7` | 登录会话有效天数 |
| `CSX_LOGIN_MAX_ATTEMPTS` | `5` | 登录失败次数限制 |
| `CSX_LOGIN_WINDOW_SECONDS` | `900` | 登录失败计数窗口（秒） |
| `CSX_115_COOKIE` | 空 | 115 驱动的环境变量凭据回退值；优先使用管理界面加密保存的账号 |
| `CSX_QUARK_COOKIE` | 空 | 夸克驱动的环境变量凭据回退值；优先使用管理界面加密保存的账号 |
| `CSX_MIGRATIONS_DIR` | 自动定位 | Alembic `migrations/` 目录；仅源码/特殊打包部署需手动指定 |
| `CLOUDSUBSCRIBE_BROWSER_IDLE_SECONDS` | vendor 默认值 | 浏览器搜索源的空闲配置，仅在启用对应搜索源时使用 |

签到、STRM、通知、媒体服务器、搜索源等业务配置在管理界面的分组设置或账号页中维护，不是进程环境变量。不要把密钥写进仓库或日志。修改 `CSX_SECRET_KEY` 会导致此前加密的账号凭据无法解密。

## 运维命令

```bash
# 查看服务状态和日志

docker compose ps
docker compose logs -f csx

# 后端质量门禁（在 backend/）
/app/venv312/bin/python -m pytest -ra
/app/venv312/bin/python -m ruff check .
/app/venv312/bin/ruff format --check csx/infra csx/tools csx/api tests

# 前端门禁（在 web/）
npm run typecheck
npm run lint
npm run test
npm run build

# 在线热备（在 backend/，容器内使用同一份 /data 挂载）
/app/venv312/bin/python -m csx.tools.backup

# 恢复前先停止应用，避免有其他进程继续访问数据库；恢复后再启动
/app/venv312/bin/python -m csx.tools.restore /data/backups/csx-backup-YYYYMMDD-HHMMSS.db.gz
```

系统 API：`POST /api/v1/system/backup` 创建备份，`GET /api/v1/system/backups` 列出备份；两者都要求管理员登录。文件默认保存于 `<CSX_DATA_DIR>/backups/`，包括 gzip 数据库、SHA256 与表行数清单。恢复命令先验证 gzip、SQLite 文件头、`PRAGMA integrity_check` 和可用的 SHA256 manifest，然后为当前数据库生成 `<database>.pre-restore.bak`，最后原子替换数据库文件。恢复会使已创建的 SQLAlchemy engine 失效，因此恢复 CLI 必须在服务停止时运行。

启动时 Alembic 自动迁移到最新 revision。若进程崩溃留下 `running` 任务，重启会将 attempt 小于 3 的任务重排为 `retry_wait`，attempt 达到 3 的任务转入 `dead_letter`，并记录 `PROCESS_CRASHED_ORPHAN`。

## 常见故障排查

| 现象 | 常见原因 | 处理方法 |
| --- | --- | --- |
| 登录后接口仍返回 401 | cookie 域、反向代理 HTTPS 或 CSRF/来源配置不匹配 | 检查浏览器 cookie、代理转发头和 CORS 来源；HTTPS 部署启用 `CSX_COOKIE_SECURE` |
| 启动报告缺少/错误管理员口令 | 数据卷中管理员已经存在，或首次启动未配置口令 | 核对 `CSX_DATA_DIR` 数据卷；初次部署预设 `CSX_ADMIN_PASSWORD`，否则读取权限为 0600 的初始口令文件 |
| 网盘凭据无法解密 | `CSX_SECRET_KEY` 为空或与写入凭据时不同 | 恢复原密钥；不要通过更换密钥尝试解密旧凭据 |
| 迁移找不到 scripts | 打包环境无法自动定位迁移目录 | 设置 `CSX_MIGRATIONS_DIR` 为包含 `env.py` 和 `versions/` 的目录 |
| 在线备份失败或磁盘空间不足 | 数据目录不可写、空间不足、SQLite 文件不是普通文件型数据库 | 检查容器 `/data` 卷权限和磁盘余量，检查服务日志；不要删除唯一备份 |
| 恢复被完整性校验拒绝 | gzip/SQLite 内容损坏或 manifest 校验和不一致 | 从另一个备份副本恢复；保留损坏文件用于诊断，不要手工覆盖活动数据库 |
| 任务重启后进入 retry_wait/dead_letter | 启动时识别到上次运行中的孤儿任务 | 查看任务历史和 `PROCESS_CRASHED_ORPHAN`，确认网盘端是否已完成操作后再重试 |
| STRM 创建成功但媒体服务器未更新 | 媒体服务器地址/API key 配置错误或网络不可达 | 在 Settings 核对 Emby/Jellyfin 配置，并检查 `/api/v1/library/servers` 返回的探测状态 |
| 前端页面/API 版本不匹配 | 后端部署了新版本但静态资源仍旧 | 重新构建前端并部署新镜像，清理浏览器缓存后重载 |

## 项目文档

- [总体架构](docs/plan/2026-11-07-独立版-架构.md)
- [P1 后端任务书](docs/plan/2026-11-07-P1-任务书.md)
- [P2 网盘驱动与搜索源搬运](docs/plan/2026-11-07-P2-任务书.md)
- [P3 命名与转存编排](docs/plan/2026-11-08-P3-任务书.md)
- [P4 API 与后台调度](docs/plan/2026-11-08-P4-任务书.md)
- [P5 前端管理台](docs/plan/2026-11-08-P5-任务书.md)
- [P6 签到、STRM 与集成能力验收](docs/test/2026-11-08-P6-验收.md)
- [P7 稳定化验收](docs/test/2026-11-08-P7-验收.md)
- [部署记录](docs/test/2026-11-07-部署到法兰克福.md)
- [路径拓扑与发布方式](docs/summary/2026-11-07-1panel路径拓扑与发布方式.md)
- [目录弹窗新建文件夹验收](docs/test/2026-11-09-目录新建文件夹验收.md)
- [路径与分层配置接通](docs/summary/2026-11-09-路径与分层接通.md)
- [config.json 与无卷部署](docs/summary/2026-11-09-config.json与无卷部署.md)
- [config.json 与无卷部署验收](docs/test/2026-11-09-config.json与无卷部署验收.md)
- [跨盘转存架构](docs/plan/2026-11-09-跨盘转存-架构.md)
- [传输与下载 UI 对齐 CS 插件（计划）](docs/plan/2026-11-10-传输与下载UI对齐CS插件.md)
- [传输与下载 UI 本地渲染验收](docs/test/2026-11-10-传输与下载UI-本地渲染验收.md)
- [传输与下载 UI 完成总结](docs/summary/2026-11-10-传输与下载UI对齐CS插件-完成.md)
- [搜索新资源（接入后台已配置渠道）架构](docs/plan/2026-11-10-搜索新资源-架构.md)
- [全量重构日志（阶段 1–4）](docs/summary/2026-11-10-全量重构日志.md)
- [全量重构验收](docs/test/2026-11-10-全量重构验收.md)
- [全量重构完成总结](docs/summary/2026-11-10-全量重构-完成.md)
- [线上部署与页签修复验收](docs/test/2026-11-10-线上部署与页签修复验收.md)

## 许可证

项目使用 GPLv3。`backend/csx/vendor/` 中的上游驱动与搜索源保留其各自声明的版权和许可证信息；分发时请一并保留相关声明。
