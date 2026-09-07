# CareerFlow AI · 项目总结（Project Summary）

> **用途说明**：本文件是 CareerFlow AI 项目的完整、自包含总结。面向两类读者：
> 1. **项目评审者 / 招聘方**：快速了解项目定位、技术栈、功能与工程质量。
> 2. **其他 AI 项目（如「二本计科生求职方向与规划咨询」）**：可从中提取技术栈、评分逻辑、示例数据、部署方式、简历话术等，用于给求职者做规划建议。
>
> 文中所有事实均来自当前代码库（截至 2026-09-01 提交 `976ea45` + `31c0a26`），可直接引用。

---

## 一、项目定位（一句话）

**CareerFlow AI 是一个面向校招求职者的「个人求职管理 + AI 匹配分析 + 模拟面试」一体化全栈 Web 应用**——既是一个能实际录入简历/岗位、查看 AI 匹配诊断、进行多轮模拟面试的工具，也是一份展示「能应对真实业务场景」能力的求职作品集项目。

- **目标用户**：应届校招生（尤其是二本/普通本科、需要靠作品集证明工程能力的计算机方向学生）。
- **核心价值**：把「海投 → 匹配判断 → 面试准备」三件最耗神的事，用一个闭环工具串起来，并用 AI 给出**可解释的诊断**（而不是一个黑盒分数）。
- **非商用声明**：作品集用途，不面向真实付费用户；但设计上考虑了鉴权、多租户隔离、外部依赖降级、云部署等真实工程问题。

---

## 二、技术栈总览

| 层 | 选型 | 关键说明 |
|---|---|---|
| 后端框架 | **Python 3.12 + FastAPI** | 异步（async/await），自动 OpenAPI 文档 `/docs` |
| ORM | **SQLAlchemy 2.0（async）** | 跨数据库可移植：本地/测试用 SQLite，生产用 PostgreSQL |
| 数据校验 | **Pydantic v2** | 输入做邮箱格式/长度校验，输出用 `from_attributes` 屏蔽密码哈希 |
| 鉴权 | **python-jose（JWT） + passlib/bcrypt** | 密码仅存哈希；登录返回 Bearer Token |
| 数据库迁移 | **Alembic** | `migrations/versions/` 管理表结构演进 |
| AI/LLM | **OpenAI 兼容接口**（可配置 base_url/model） | 默认智谱 `glm-4-flash`；Render 部署改通义 `qwen-plus`（规避免费档 429） |
| 前端框架 | **Vue 3 + Vite + TypeScript** | `<script setup>` 组合式 API |
| 状态/路由 | **Pinia + Vue Router** | `requiresAuth` 守卫；路由级懒加载 |
| UI 组件 | **Element Plus** | 表单/表格/对话框/标签等企业后台风格 |
| 可视化 | **手写零依赖 SVG 雷达图**（`RadarChart.vue`） | 不引图表库，避免前端包体进一步膨胀 |
| 部署 | **Docker 多阶段构建 → Render Free** | 前端 dist 拷入后端 `static`，同源托管，免 CORS |
| 质量保障 | **pytest-asyncio + ruff** | 22 个测试全过；lint 零告警 |

---

## 三、系统架构与目录结构

```
D:\Project-2\
├── Dockerfile                 # 多阶段：先 build 前端，再拷 dist 进后端镜像
├── render.yaml                # Render Blueprint 一键部署配置
├── README.md                  # 使用/部署说明
├── EXTENSIONS.md              # 功能扩展路线与已完成项
├── PROJECT_SUMMARY.md         # 本文件
├── backend/
│   ├── requirements.txt
│   ├── start.py               # 本地启动入口（uvicorn）
│   ├── app/
│   │   ├── main.py            # FastAPI 入口：生命周期、CORS、路由装配、同源静态托管、SPA 兜底
│   │   ├── config.py          # pydantic-settings：全部敏感配置走环境变量
│   │   ├── database.py        # 引擎/会话/建表 + 老库 ALTER 兼容
│   │   ├── models.py          # ORM 模型：User/Resume/Job/Analysis/Application/InterviewSession
│   │   ├── schemas.py         # Pydantic 请求/响应模型
│   │   ├── security.py        # 密码哈希 + JWT 签发/校验
│   │   ├── dependencies.py    # get_current_user（鉴权依赖）
│   │   ├── llm.py             # ask_llm：OpenAI 兼容调用，失败返回 None（优雅降级）
│   │   ├── upload_utils.py    # 文件上传解析（白名单 + 3MB 上限）
│   │   ├── seed.py            # 空库自动灌入演示数据（幂等）
│   │   └── api/
│   │       ├── auth.py        # 注册 / 登录
│   │       ├── resumes.py     # 简历 CRUD + 上传
│   │       ├── jobs.py        # JD CRUD
│   │       ├── analysis.py    # AI 匹配分析（四维评分）
│   │       ├── applications.py# 投递管理（看板）
│   │       └── interview.py   # 模拟面试（多轮对话）
│   ├── migrations/versions/   # Alembic 迁移脚本
│   └── tests/                 # pytest：auth/resumes/jobs/analysis/applications/interview/upload
└── frontend/
    └── src/
        ├── main.ts / App.vue  # 入口 + 全局布局/导航
        ├── router/index.ts    # 路由 + 鉴权守卫
        ├── stores/auth.ts     # Pinia 用户态
        ├── types.ts           # TS 类型（与后端 schema 对齐）
        ├── utils/api.ts       # axios 封装（JWT 拦截、401 跳登录）
        ├── styles/global.css  # 全局样式（cf-* 设计令牌）
        ├── components/RadarChart.vue  # 零依赖 SVG 雷达图
        └── views/
            ├── LoginView.vue / RegisterView.vue
            ├── DashboardView.vue
            ├── ResumeView.vue   # 简历管理（含期望薪资）
            ├── JobView.vue      # JD 管理（含薪资范围）
            ├── AnalysisView.vue # AI 分析（雷达 + 评分依据 + 一键面试）
            ├── ApplicationsView.vue  # 投递看板
            └── InterviewView.vue # 模拟面试聊天
```

**请求流**：前端 `/api/*` → FastAPI 路由（鉴权依赖注入 `get_current_user`）→ 业务 + SQLAlchemy 异步会话 → PostgreSQL/SQLite。生产环境前端由后端同源托管（`/assets` + SPA 兜底），无需跨域。

---

## 四、功能清单（及对应真实求职场景）

| # | 功能 | 对应真实场景 | 关键实现 |
|---|---|---|---|
| 1 | **账号鉴权** | 求职者私有数据保护 | 注册（邮箱+密码≥8位）/登录（OAuth2 表单→JWT）；bcrypt 哈希，绝不返回密码 |
| 2 | **简历管理** | 维护多份简历版本 | CRUD + **期望薪资**字段；支持上传 `.txt/.md/.pdf/.docx` 自动解析正文（白名单+3MB 上限） |
| 3 | **JD 管理** | 收藏目标岗位 | CRUD + **薪资范围**字段 |
| 4 | **AI 匹配分析** | 「我投这个岗到底匹不匹配？」 | 调 LLM 输出综合分 + **技能/经验/学历/薪资四维子分** + 文字诊断 + 推荐面试题；零依赖 SVG **雷达图**可视化 |
| 5 | **投递管理看板** | 跟踪投递进度 | 5 状态：想投/已投/面试中/已拿offer/已拒；备注 + 投递日期；按状态筛选 |
| 6 | **模拟面试** | 「面试前先练练」 | 基于某次分析开启多轮对话：AI 出题→候选人作答→LLM 评分反馈+下一题；**累计均分**；会话持久化、可回看 |
| 7 | **分析→面试闭环** | 从诊断直接进演练 | 分析详情/结果卡「🎤 一键开始模拟面试」→ 带 `?analysis_id=` 跳面试页自动开聊 |

> 全部功能围绕一条主线闭环：**填简历(带期望薪资) + 填JD(带薪资范围) → AI 分析(四维有据打分) → 点按钮 → 多轮模拟面试(逐轮评分+累计均分)**。

---

## 五、AI 匹配分析 · 评分逻辑（重点：薪资如何打分）

这是本项目「不黑盒、可解释」的核心。Prompt 要求 LLM 返回 5 个分数 + 一段必须**逐条点名**四维打分原因的文字：

| 维度 | 字段 | 评分依据（硬规则） |
|---|---|---|
| 综合匹配度 | `match_score` | LLM 综合四个子维度给出 0–100 |
| 技能匹配 | `skill_match` | 岗位要求技能 ↔ 简历技能的契合 |
| 经验匹配 | `exp_match` | 相关项目/实习经历 ↔ 岗位职责的契合 |
| 学历匹配 | `education_match` | 学历/专业 ↔ 岗位硬性要求 |
| **薪资契合** | `salary_fit` | **期望薪资区间 ↔ JD 薪资区间的重叠度**：高度重叠（≥约 85）给高分；部分重叠给 60–84；期望明显高于上限或低于下限给 ≤45 |

**薪资维度的关键设计（用户特别关切点）**：
- 简历有 `expected_salary`（如 `9k-13k`），JD 有 `salary_range`（如 `8k-14k`）。Prompt 会**把这两个字段原文喂给 LLM**，要求它"按区间重叠度打分，无明确信息时不得瞎估"。
- `match_summary` 必须显式写出"期望 X 落在岗位 Y 区间内/仅窄幅重叠"之类的依据，让分数**可被候选人向面试官解释**。
- 由此示例数据自洽：实施简历 `期望 9k-13k × 岗位 8k-14k` → `salary_fit=80`；而"实施简历投后端岗 `期望 9k-13k × 岗位 13k-20k`" → 仅在 13k 窄幅重叠 → `salary_fit=60`，与 52 总分的错配结论一致。

解析层做了防御：`_to_score()` 对 LLM 返回做 0–100 钳制、去单位（"85分"→85.0）、`null`→`None`；非法 JSON 时整条分析返回 503 而非 500。

---

## 六、模拟面试 · 交互与评分

- **开启**：`POST /interview`，首问取自该分析记录的 `interview_questions[0]`（无 key 也能开，因为面试题是预存文本）。
- **作答**：`POST /interview/{id}/answer` 调 LLM 评价上一条回答 → 返回 `{score, feedback, next_question}`；后端把"评价 X 分 + 反馈 + 下一题"追加进会话，并**用所有轮次分数求算术平均**作为 `current_score`。
- **结束**：LLM 返回 `next_question=null` → 会话 `status=completed`，前端锁输入并提示均分。
- **健壮性**：LLM 返回非法 JSON 时 `_parse_turn` 兜底（把原文本当反馈、安全结束面试），不会 500。
- **多租户**：所有接口按 `owner_id` 隔离，越权访问返回 404（而非 403，避免泄露资源是否存在）。

---

## 七、示例演示数据（开箱即用，无需 LLM key）

数据库为空时自动灌入（幂等，已有数据则跳过）。**演示账号**：

```
邮箱：demo@careerflow.app
密码：CareerFlow2026
```

| 类别 | 数量 | 内容要点 |
|---|---|---|
| 简历 | 4 份 | 实施顾问(9k-13k) / 后端(12k-18k) / 前端(11k-16k) / 数据分析(10k-15k) |
| JD | 4 份 | 对应岗位，薪资范围 8k-14k / 13k-20k / 12k-18k / 10k-16k |
| 分析 | 5 条 | 4 条高匹配(86/83/79/85) + 1 条错配(实施投后端 52 分)；均带四维子分 + 诊断文字 |
| 投递 | 5 条 | 覆盖全部 5 种状态：面试中/已投/想投/已offer/已拒 |
| 模拟面试 | 1 条 | **已完成三轮**：82→80→84，累计均分 82，含完整问答与面试官点评 |

> 即使**不配 LLM_API_KEY**，分析历史、雷达图、面试示例、投递看板全部有内容可看；只有"点开始分析/作答"需要 key（返回 503 并提示如何配置）。这保证了作品集在免费部署环境下也能完整演示。

**推荐演示动线**：登录 → 看板（投递进度一目了然）→ AI 分析（雷达图 + 评分依据）→ 点「🎤 一键开始模拟面试」→ 看那条已完成的三轮示例 → 回到简历/JD 页看期望薪资与薪资范围字段。

---

## 八、核心数据模型

```text
User(id, email[唯一], hashed_password, created_at)
Resume(id, owner_id*, title, content, expected_salary, created_at, updated_at)
Job(id, owner_id*, title, description, salary_range, created_at, updated_at)
Analysis(id, owner_id*, resume_id?, job_id?, match_score?, match_summary?,
         interview_questions[JSON], skill_match?, exp_match?, education_match?, salary_fit?, created_at)
Application(id, owner_id*, resume_id?, job_id?, resume_title, job_title,
            status[5种], applied_at?, notes, created_at, updated_at)
InterviewSession(id, owner_id*, analysis_id?, analysis_title, messages[JSON],
                 current_score?, status[in_progress|completed], created_at, updated_at)
```

- 所有业务表带 `owner_id` 外键并建索引，保证数据隔离。
- `Analysis.messages` / `InterviewSession.messages` 以 JSON 字符串存储，避免额外建表。
- 新增列（四维、薪资字段）通过 `init_db()` 的 inspector 防御逻辑自动 `ALTER TABLE` 补齐，并配套 Alembic 迁移，**老库无需删库即可平滑升级**。

---

## 九、API 端点速查（`/api` 前缀）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册（邮箱+密码） |
| POST | `/auth/login` | 登录（表单字段 `username`=邮箱，`password`）→ 返回 JWT |
| GET/POST | `/resumes` | 列表 / 新建 |
| GET/PUT/DELETE | `/resumes/{id}` | 详情 / 更新 / 删除 |
| POST | `/resumes/upload` | 上传文件解析（白名单+3MB） |
| GET/POST | `/jobs` | 列表 / 新建 |
| GET/PUT/DELETE | `/jobs/{id}` | 详情 / 更新 / 删除 |
| GET/POST | `/analysis` | 列表 / 新建（触发 LLM 分析） |
| GET/DELETE | `/analysis/{id}` | 详情 / 删除 |
| GET/POST | `/applications` | 列表 / 新建 |
| GET/PUT/DELETE | `/applications/{id}` | 详情 / 更新 / 删除 |
| GET/POST | `/interview` | 列表 / 开启面试 |
| GET/DELETE | `/interview/{id}` | 详情 / 删除 |
| POST | `/interview/{id}/answer` | 提交一轮作答（触发 LLM 评分） |
| GET | `/health` | 健康检查（Render healthCheckPath） |

> 除 `/auth/*` 与 `/health` 外，所有接口需 `Authorization: Bearer <token>`。

---

## 十、工程化与质量保障

- **鉴权与隔离**：JWT + bcrypt；每个业务接口注入 `get_current_user`，按 `owner_id` 过滤；越权返回 404。
- **外部依赖降级**：`ask_llm()` 任何失败（无 key、超时、限流、非法 JSON）均返回 `None` → 接口返回 **503 + 明确提示**（"请在环境变量设置 LLM_API_KEY"），而非崩溃。测试用 monkeypatch 注入假 JSON，不依赖真实 key。
- **老库兼容**：`init_db()` 用 `inspect()` 检查并 `ALTER TABLE ADD COLUMN` 补缺失列；非空库升级不破坏旧数据。
- **演示数据幂等**：仅当 `users` 表为空时 seed，绝不覆盖真实用户数据；seed 失败仅告警不阻断启动。
- **测试与 Lint**：`pytest` **22 passed**；`ruff` **零告警**；前端 `vue-tsc + vite build` 通过。
- **安全性**：密码哈希存储、JWT 签名（密钥走环境变量，开发默认有告警）、CORS 白名单、文件上传白名单+体积限制、全程 ORM 防注入。
- **可部署性**：Docker 多阶段构建；Render Blueprint（`render.yaml`）一键起服务；临时文件系统重启自动重新 seed。

---

## 十一、本地运行 & 云端部署

**本地开发**
```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000      # 或 python start.py

# 前端（另开终端）
cd frontend
npm install
npm run dev        # Vite 代理 /api → localhost:8000
```
打开 `http://localhost:5173`，用演示账号登录即可。

**环境变量**（均可不填，有合理默认；生产务必覆盖 `SECRET_KEY` 与 `LLM_API_KEY`）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./careerflow.db` | 生产改 PostgreSQL async URL |
| `SECRET_KEY` | 开发占位（启动告警） | JWT 签名，生产必须覆盖 |
| `LLM_API_KEY` | 空 | 留空则分析/作答返回 503，其余功能正常 |
| `LLM_BASE_URL` | 智谱 glm-4-flash | 可改通义 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | `glm-4-flash` | 如 `qwen-plus` |
| `AUTO_SEED` | `1`（True） | 空库自动灌演示数据；本地不想被灌可设 `0` |
| `CORS_ORIGINS` | `localhost:5173` | 独立部署前端时填 Vercel 域名（逗号分隔） |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | 空（开发态） | 注册验证码邮件。三项（`HOST/USER/PASSWORD`）齐备才视为已配置；否则进入**开发态**：不真发信，验证码由接口返回前端直接展示。兼容 Resend / Gmail / 阿里云 DirectMail 标准 SMTP |

**部署到 Render（Free）**
1. GitHub 推送到仓库。
2. Render 控制台 New → Blueprint → 选仓库（按 `render.yaml` 创建）。
3. `SECRET_KEY` 自动随机生成；`LLM_API_KEY` 在控制台手动填（不进仓库/日志）；`AUTO_SEED=1` 已配置。
4. Docker 多阶段会自动 build 前端并把 dist 拷进后端 `static`，**同源托管**，免 CORS。
5. Free 实例临时盘会重置 → 重启后自动重新 seed 演示数据（符合"仅用默认数据展示"的定位）。

---

## 十二、已知限制与后续路线

1. **数据持久性（设计取舍）**：Render Free 临时文件系统，重启丢库 → 自动重新 seed。若要真实持久，需挂 PostgreSQL 附加组件（在 `render.yaml` 加 `databases:` 或 external DB）。
2. **新注册用户数据为空**：seed 仅灌演示账号。若希望每位新用户也有示例，可加"载入示例数据"按钮或按用户 seed。
3. **前端包体**：`index.js` 约 1.1MB（Element Plus 全量引入），可改按需引入 / `manualChunks` 优化首屏。
4. **分析无缓存（技术债）**：同一对简历/JD 重复点分析会重复调用 LLM 花钱；可做 `UNIQUE(resume_id, job_id)` 命中即返回历史（已记入 EXTENSIONS.md）。
5. **LLM 依赖外部**：免费档可能限流（429），部署推荐通义 `qwen-plus` 或自备 key。
6. **邮箱验证码为开发态**：为保持演示站点零成本、零依赖，默认未配 SMTP，注册验证码直接在前端展示（而非真实发信）。需要真实发信时，配置 `SMTP_*` 环境变量即可自动切换，无需改代码。

---

## 十三、给求职者（二本计科生）的简历 / 面试话术要点

> 这部分供「求职咨询」类项目提取，用于帮同学把本项目写进简历、讲进面试。

- **一句话项目描述（简历版）**："独立全栈开发 CareerFlow AI——校招求职助手，后端 FastAPI + 异步 SQLAlchemy，前端 Vue3 + TypeScript，集成 LLM 做可解释的岗位匹配诊断与多轮模拟面试，Docker 部署至 Render。"
- **体现的工程能力（按面试官关注点）**：
  - **全栈闭环**：从数据库建模、RESTful API、JWT 鉴权到前端工程化全部自己打通。
  - **真实业务意识**：用户数据隔离（多租户）、外部依赖降级（LLM 失败不崩）、老库平滑迁移、演示数据幂等——不是玩具 Demo。
  - **AI 产品思维**：评分不是黑盒，薪资维度基于"期望 vs 岗位区间重叠度"且要求模型给出可解释依据；并把"分析→面试"做成闭环。
  - **质量习惯**：写了 pytest 单测 + ruff lint，前端类型检查通过，能部署上线。
- **可能被深挖 & 如何答**：
  - *Q：多维评分怎么保证不乱给？* → 答：薪资维度有硬规则（区间重叠度），且要求模型在诊断文字里逐条点名依据，分数可解释、可向候选人交代。
  - *Q：LLM 挂了怎么办？* → 答：`ask_llm` 失败返回 None，接口降级为 503 并提示配置 key，其余 CRUD 功能不受影响；测试也用 mock 隔离外部依赖。
  - *Q：多人用数据会不会串？* → 答：每张业务表带 `owner_id`，所有查询按当前用户过滤，越权返回 404。
- **定位建议**：作为"能应对真实业务场景"的作品集之一，重点讲**工程严谨性**（隔离/降级/迁移/测试）而非堆功能数量；正好契合"实施顾问/数字化交付"岗位看重的稳健与落地意识。

---

## 十四、关键提交与文档索引

- 功能提交：`976ea45`（薪资数据驱动 + 分析→面试闭环 + 示例数据完整化）、`31c0a26`（记忆/复盘）。
- 扩展路线与已完成项见 `EXTENSIONS.md`；使用/部署细节见 `README.md`。
- 历史会话修复的两个真实 bug（供面试讲述"踩坑"）：① seed 误依赖前端静态目录导致 Render 空库；② seed 未 `flush` 致示例面试会话丢失——均已在本地复现并修复、补测试。
