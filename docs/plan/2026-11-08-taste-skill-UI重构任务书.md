# 基于 taste-skill 的前端全量高维质感重构任务书

> 状态：待开工
> 规范基准：`taste-skill` (`design-taste-frontend` 2.5.1)
> 目标：运用已安装的 `taste-skill` 反庸俗化（anti-slop）顶级设计哲学，将整个前端彻底升级至 figma.com / x.ai 级质感，彻底消除“AI 生成的灰盒子套灰盒子”廉价感，实现极具沉浸感、呼吸感的大厂消费级影音控制台。

---

## 1. taste-skill 核心设计准则在 CSX 中的落地

1. **拒绝廉价灰盒子嵌套（No grey boxes on grey grounds）**：
   - 彻底消灭不必要的容器卡片边框。只有真正需要成为聚焦卡片的内容才加框，其余信息依靠排版、字重层级和优雅留白实现区分。
2. **主体即视觉重心（The subject leads at true size）**：
   - 影视系统的绝对主体就是**高清海报与电影画质**。海报卡片必须采用标准 2:3 纵横比，大图呈现，图片覆盖率最大化。
   - 没有海报时，使用微质感电影暗夜渐变（Gradient Backdrop）配精致微水印，绝不用干瘪灰色。
3. **微交互动效（Hover Micro-animations）**：
   - 链接卡片 hover 向上微升 2px（`-translate-y-0.5 transition-transform duration-200`）
   - 海报图片在容器内轻微缩放 1.025 倍（`group-hover:scale-[1.025] transition-transform duration-300`）
   - 按钮点击产生平滑按压反馈（`active:scale-[0.98]`）
4. **等宽对齐与严苛间距**：
   - 桌面端两侧边距严格对称对齐，卡片与网格留白保持 16px/24px/32px 韵律。
   - 所有数值、时间、集数进度全走等宽数字（`font-mono tabular-nums`）。
5. **纯色反转主行动点（Monochrome Inverted Actions）**：
   - 核心行动按钮（如「+ 添加追剧」、「+ 快捷转存」）采用极简且醒目的纯白底黑字反转（`bg-zinc-100 text-zinc-950 font-semibold shadow-sm hover:bg-white`），在深邃炭黑背景中极具吸睛感与高级质感。

---

## 2. 页面与组件重构清单

1. **`AppLayout.vue` / `Sidebar.vue` / `Topbar.vue`**：
   - 侧边栏：极简沉浸式背景（`bg-zinc-950/95`），5 个核心顶级入口采用大图标与现代文字微间距，活动项带精致发光指示条。
   - 顶栏：轻量半透明磨砂（`backdrop-blur-md border-b border-white/[0.06]`），右上角常驻白底黑字「+ 快捷转存」与呼吸感在线绿灯。
2. **首页「我的追剧」 (`DashboardPage.vue`)**：
   - 影视海报墙（Poster Grid）作为一屏绝对视觉中心。
   - 顶部统计为无边框轻量数字排版，避免笨重卡片。
   - 底部紧凑收纳转存队列与服务健康指示。
3. **探索推荐 (`DiscoverPage.vue`)**：
   - TMDB 今日热播/热剧/电影 2:3 国际标准海报墙，角标金星评分，点击弹出宽屏大剧照详情卡片，一键追更。
4. **传输管理 (`TasksPage.vue`)**：
   - 四合一传输中心（正在转存 / 历史流水 / 115云端离线 / 待选资源）。
5. **系统设置 (`SettingsPage.vue`)**：
   - 7 大选项卡，首项为独立网盘账号（扫码一键绑定），次项为 15 搜索源自描述双栏面板。

---

## 3. 验收要求

1. 在 `backend/` 下运行 `/app/venv312/bin/python -m pytest -ra` 保持 278 单测全绿。
2. 在 `backend/` 下运行 `/app/venv312/bin/ruff check .` 通过。
3. 在 `web/` 下运行 `npm run typecheck`（vue-tsc 零错误）与 `npm run build` 打包成功。
4. 撰写 `docs/test/2026-11-08-taste-skill-UI重构验收.md` 并提交 commit。
