# CareerFlow AI · 项目总结补遗（2026-09-07 更新）

> 本文件是 `PROJECT_SUMMARY.md` 的增量更新，记录 2026-09-07 落地的两项工程优化：
> **① AI 分析缓存去重 + 强制重算** 与 **② 前端 Element Plus 按需引入**。
> 主总结文件中「截至 2026-09-01」的部分事实仍有效，本补遗覆盖新增能力与数据。

---

## 一、AI 分析缓存去重 + 强制重算

### 背景 / 动机
原 `POST /api/analysis` 每次点击都无条件调用一次大模型并新建一条分析记录：
同一份简历 × 同一份 JD 反复分析会产生大量重复记录，且每次都消耗 LLM 调用成本。
作品集场景下，分析列表越攒越乱，也不符合「真实业务应防止重复写」的工程直觉。

### 设计要点
1. **去重键**：同一用户的同一「简历 × JD」组合只允许一条分析结果。
   唯一索引 `uq_analysis_owner_resume_job(owner_id, resume_id, job_id)`。
   特意包含 `owner_id` —— 不同用户可能使用相同自增 id，若只用 `(resume_id, job_id)`
   会被唯一约束误伤；含 `owner_id` 后跨用户互不干扰。
2. **命中缓存**：`analyze` 入口先按 `(owner_id, resume_id, job_id)` 查已有记录；
   存在且请求未带 `force=true` 时，直接返回缓存记录（HTTP 200），**不再调 LLM、不再新建**。
3. **强制重算**：请求带 `force=true` 时，先删除该组合下的全部旧记录（`DELETE` 后 `flush`），
   再调用 LLM 生成新结果并返回（HTTP 201）。先删后建保证唯一索引不冲突。
4. **数据库兜底**：唯一索引在 DB 层防并发/直接 API 调用产生的重复；
   迁移升级时对已存在的重复行做安全清理（保留 id 最大的一条）。

### API 变化
- `POST /api/analysis`
  - 请求体新增字段：`force: boolean`（默认 `false`）。
  - 命中缓存返回 **200**；新生成 / 强制重算返回 **201**（与旧行为一致）。

### 前端变化
- `frontend/src/utils/api.ts`：`createAnalysis(resume_id, job_id, force = false)`。
- `frontend/src/views/AnalysisView.vue`：
  - 「开始分析」按钮仍走 `force=false`（命中缓存省调用）；
  - 新增「重新分析（调 AI）」按钮走 `force=true`；
  - 命中缓存时弹 `ElMessage.info` 提示「已命中缓存，未重复调用 AI」。

### 涉及文件（后端）
- `backend/app/models.py`：`Analysis` 加 `__table_args__` 唯一约束。
- `backend/app/schemas.py`：`AnalysisRequest` 加 `force: bool = False`。
- `backend/app/api/analysis.py`：查重 + force 删旧建新 + 按 `Response` 区分 200/201。
- `backend/migrations/versions/6e7f8091ab02_add_analysis_unique_constraint.py`：加唯一索引（含重复清理）。
- `backend/tests/test_analysis.py`：新增 `test_analysis_dedup_returns_cache`、`test_analysis_force_recalc`。

---

## 二、前端 Element Plus 按需引入（构建优化）

### 背景 / 动机
原 `frontend/src/main.ts` 使用 `import ElementPlus from 'element-plus'` + `app.use(ElementPlus)`
+ `import 'element-plus/dist/index.css'`，即**全量注册并打包整个 Element Plus 库**，
哪怕页面只用到了 Button / Table / Dialog 等少数组件，整个库（含全部样式）都被打进主包，
导致首屏 JS/CSS 体积过大。

### 设计要点
1. 引入 `unplugin-auto-import` + `unplugin-vue-components`，均配 `ElementPlusResolver`。
2. `vite.config.ts` 加入两个插件：
   - **AutoImport**：自动注入 `ElMessage` / `ElMessageBox` 等 API（不再需手写 `import`）。
   - **Components**：模板中用到的 `<el-*>` 组件按需自动注册并注入对应样式。
3. `main.ts` 移除 `app.use(ElementPlus)` 与全量 CSS 引入。
4. 各视图文件移除显式 `import { ElMessage, ElMessageBox } from 'element-plus'`
   （改由 AutoImport 在编译期自动注入，避免重复声明报错）。
5. `tsconfig.json` 的 `include` 增加 `auto-imports.d.ts`、`components.d.ts`
   （插件生成的类型声明，供 `vue-tsc` 识别自动导入的全局 API/组件）。
6. **类型收口**：按需引入后 `el-table` 列槽的 `row` 泛型推断退化为 `DefaultRow`
   （`Record<string, unknown>`），故在用到 `row` 处显式标注 `row as Analysis / Job / Resume`，
   既修类型又让行类型更明确。

### 包体前后对比（同份源码，`npm run build` 产物）

| 指标 | 改动前 | 改动后 | 变化 |
|------|--------|--------|------|
| dist 总体积 | 1.5 MB | 958 KB | ↓ ~37% |
| 主 JS 包 `index-*.js` | 1.11 MB | 310 KB | ↓ ~72% |
| 主 CSS `index-*.css` | 364 KB | 42 KB | ↓ ~88% |

> 组件（如 `el-table-column`、`el-message`、`el-message-box`）现各自成为独立懒加载 chunk，
> 真正用到时才下载，首屏只加载必要代码。

### 涉及文件（前端）
- `frontend/package.json` / `package-lock.json`：新增 `unplugin-auto-import`、`unplugin-vue-components`（devDependencies）。
- `frontend/vite.config.ts`：加入 AutoImport + Components 插件。
- `frontend/src/main.ts`：移除全量注册与全量样式。
- `frontend/src/views/*.vue`（AnalysisView / ResumeView / JobView / InterviewView / ApplicationsView / LoginView / RegisterView / DashboardView）：移除显式 El* 导入；表格槽 `row` 加 `as` 标注。
- `frontend/src/utils/api.ts`：`createAnalysis` 加 `force` 参数。
- `frontend/tsconfig.json`：`include` 增加自动生成的声明文件。
- 生成文件：`frontend/auto-imports.d.ts`、`frontend/components.d.ts`（建议提交，保证干净克隆可直接 `npm run build` 通过类型检查）。

---

## 三、测试与质量

- 后端 pytest：**22 → 29** 全过（新增 2 个分析去重用例 + 历史用例保持绿）。
- 前端 `npm run build`（`vue-tsc -b` 类型检查 + `vite build`）通过，无类型错误、无 lint 阻断。
- 迁移链在干净 SQLite 库验证：`alembic upgrade head` 跑通至 `6e7f8091ab02`，唯一索引正确建立。
