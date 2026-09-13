# CareerFlow AI · 项目长期记忆

## 项目定位（不变的事实）
- 目录 `D:/Project-2`，FastAPI(async SQLAlchemy 2.0) + Vue3/TS/Pinia/Element Plus，Alembic 迁移，Docker 多阶段 → Render Free 同源托管。
- **用户是「作品集作者 + 方案/验收/部署负责人」，不是手工编码者**。代码由 AI 生成，用户负责需求定义、方案拍板、交互调优、部署上线、线上验证。
  → 沟通与交付文档一律按此定位表述，**不要默认用户能读懂代码细节**，也不要替他夸大编码贡献。

## 线上环境（2026-09-12 实测确认）
- **线上地址：https://careerflow-hbem.onrender.com**（注意：`careerflow.onrender.com` 是错的服务名，返回 404，别再探测那个）
- 演示账号：`demo@careerflow.app` / `CareerFlow2026`
- `/health` 200、根路径 200、注册两步流程可用、`AnalysisRequest` 含 `force` 字段 → **线上跑的是最新代码**

## 本机固定环境（沿用）
- Python：`C:/Users/Lenovo/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
- Node：`C:/Users/Lenovo/.workbuddy/binaries/node/versions/22.22.2-2/node.exe`
- 跑后端命令须带 `PYTHONPATH=D:/Project-2/backend`（**不是** `/d/Project-2/backend`）
- **推送一律由用户用 GitHub Desktop 完成**，助理只做本地 commit（网络对 github.com 不稳定，fetch 常被 reset）

## 判断"代码是否已上线"的可靠方法（教训沉淀）
`git fetch` 失败时，本地 `origin/main` 引用不可信，**不要用它判断推送成败**。
改用线上产物反查版本：
1. 抓首页 → 找 `/assets/index-*.js` / `*.css` → 比体积（按需引入后主 CSS ≈ 42KB，之前 364KB）
2. 抓 `/openapi.json` → 看请求模型字段（如 `force` 是否存在）
3. 探端点存在性（新端点 200、旧端点 405 → 说明已更新）

## 简历可用的量化事实（实测，勿改数）
- 规模：后端 19 个 py / 约 2356 行；前端 8 视图 / 约 2488 行
- 质量：pytest **29 条全过**、ruff 零告警、Alembic **6 个**迁移
- 性能：主 JS 1.11MB→310KB(-72%)、主 CSS 364KB→42KB(-88%)、dist 1.5M→958K(-37%)
- 演示数据：4 简历 / 4 JD / 5 分析（含 1 条故意错配 52 分）/ 5 投递（覆盖 5 状态）/ 1 场三轮面试（82→80→84）

## 求职材料的存放约定
- `求职材料_CareerFlow_项目说明与面试话术.md` **刻意不提交进 Git 仓库**（含"代码由 AI 实现"自述与话术，属私人材料，不宜随作品集仓库推送）。
- 同理，后续任何"面试话术 / 自我评价 / 求职策略"类文件都放本地，默认不 commit。
