"""自动 seed：应对 Render 临时文件系统重启丢库。

仅当数据库为空（无任何用户）时灌入演示数据，让作品集开箱可用：
- 一个演示账号（recruiters 一键体验）
- 多份示例简历 + 多份示例 JD（覆盖不同岗位方向，方便演示「列表 / 增删改查」）
- 若干条示例 AI 分析记录（让「历史分析」一进入就有数据，直观展示功能）

已有数据则跳过，绝不覆盖真实用户数据。

说明：简历 / JD 为真实风格的示例内容；历史分析记录为「示例分析数据」，用于演示
「AI 匹配分析」功能的产出形态。配置 LLM_API_KEY 后点「开始分析」会生成实时结果
（追加到历史，不影响既有示例）。
"""
from __future__ import annotations

import json
import logging
import os

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import Analysis, Job, Resume, User
from app.security import hash_password

logger = logging.getLogger("careerflow.seed")

# 演示账号（作品集演示专用，仅 Render 演示环境使用；生产可关闭 AUTO_SEED）
DEMO_EMAIL = "demo@careerflow.app"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "CareerFlow2026")


# ============ 示例简历 ============
SAMPLE_RESUMES: list[dict] = [
    {
        "title": "简历 · 数字化实施顾问（应届）",
        "content": """教育背景
天津理工大学中环信息学院 · 计算机科学与技术（本科） · 2027 届

专业技能
- 熟悉 Python / Java 基础，了解 FastAPI、Vue3 等前后端框架
- 掌握 SQL 与关系型数据库（PostgreSQL / SQLite）基本操作
- 了解 RESTful API 设计与 JWT 鉴权流程
- 具备 Linux 基础操作与 Git 协作能力
- 了解企业数字化系统实施基本流程（需求梳理、数据初始化、培训）

实习经历
天津市赛鸣科技 · 软件开发实习生
- 参与政企数字化系统的需求梳理与测试用例编写
- 协助完成模块接口联调、数据核对与上线支持

项目经历
进销存管理系统（Flask + Vue3）
- 负责商品 / 库存 / 订单模块前后端联调与部署
校招面试题库 RAG（FastAPI + Chroma + Vue3）
- 实现文档上传、自动切分向量化与带引用溯源的问答
""",
    },
    {
        "title": "简历 · 后端开发工程师（应届）",
        "content": """教育背景
XX 大学 · 软件工程（本科） · 2027 届

专业技能
- 熟练掌握 Python / Java，熟悉 FastAPI / Spring Boot
- 熟悉 MySQL / PostgreSQL，了解 Redis 缓存与消息队列
- 了解 RESTful / 微服务架构、Docker 与 CI/CD
- 掌握 Git、Linux 与基础网络知识

实习经历
某互联网公司 · 后端开发实习生
- 参与用户中心服务的接口开发与单元测试编写
- 使用 Redis 优化热点数据查询，降低接口平均时延约 40%

项目经历
校园二手交易平台（Spring Boot + MySQL + Redis）
- 设计商品 / 订单 / 消息模块，完成高并发下单优化
""",
    },
    {
        "title": "简历 · 前端开发工程师（应届）",
        "content": """教育背景
XX 大学 · 计算机科学与技术（本科） · 2027 届

专业技能
- 熟练掌握 HTML / CSS / JavaScript，熟悉 Vue3 / TypeScript
- 了解 Element Plus、Pinia、Vue Router 等前端生态
- 掌握 Axios 接口对接与前端工程化（Vite）
- 了解响应式布局与基础组件封装

实习经历
某科技公司 · 前端开发实习生
- 参与后台管理系统页面开发与组件复用
- 使用 ECharts 完成运营数据可视化看板

项目经历
在线学习平台前端（Vue3 + Vite + Element Plus）
- 实现课程列表、播放页与学习进度跟踪
""",
    },
    {
        "title": "简历 · 数据分析师（应届）",
        "content": """教育背景
XX 大学 · 统计学（本科） · 2027 届

专业技能
- 熟练掌握 Python（pandas / numpy / sklearn）
- 熟悉 SQL 与常见数据库，了解数据清洗与建模
- 掌握 Excel / Tableau / Power BI 等可视化工具
- 了解 A/B 测试与基本统计分析方法

实习经历
某电商公司 · 数据分析实习生
- 搭建销售日报自动化脚本，提升运营取数效率
- 参与用户留存分析，输出渠道质量评估报告

项目经历
用户流失预警模型（Python + sklearn）
- 基于历史行为数据构建逻辑回归模型并评估
""",
    },
]


# ============ 示例 JD ============
SAMPLE_JOBS: list[dict] = [
    {
        "title": "JD · 数字化实施顾问（校招）",
        "description": """岗位职责
- 负责政企 / 制造行业数字化系统的现场实施、部署与培训
- 对接客户需求，完成数据初始化、流程配置与上线支持
- 整理实施文档，跟踪项目交付进度并协调资源

任职要求
- 计算机 / 信息类相关专业，本科及以上
- 良好的沟通表达能力，能接受出差、不排斥对接客户
- 了解数据库与基本网络知识，有项目实施实习经验优先
- 学习主动、逻辑清晰，能承受一定交付压力
""",
    },
    {
        "title": "JD · 后端开发工程师（校招）",
        "description": """岗位职责
- 负责核心业务系统的后端服务设计与开发
- 保障接口性能、稳定性与数据安全
- 参与技术方案评审与代码评审

任职要求
- 计算机相关专业，熟悉至少一门后端语言（Java / Python / Go）
- 熟悉 MySQL 等关系型数据库，了解缓存与消息队列
- 了解 RESTful / 微服务，有实习或项目经验优先
""",
    },
    {
        "title": "JD · 前端开发工程师（校招）",
        "description": """岗位职责
- 负责 Web 端产品的前台页面开发与交互实现
- 与后端协作完成接口对接，保障页面性能与兼容性
- 参与组件库建设与前端工程化

任职要求
- 熟悉 HTML / CSS / JavaScript，掌握至少一种主流框架（Vue / React）
- 了解 TypeScript 与前端构建工具（Vite / Webpack）
- 注重用户体验，有项目或实习经验优先
""",
    },
    {
        "title": "JD · 数据分析师（校招）",
        "description": """岗位职责
- 负责业务数据的提取、清洗与可视化
- 输出经营分析报告，支持业务决策
- 参与用户 / 商品等主题的数据建模

任职要求
- 统计 / 数学 / 计算机相关专业，熟悉 SQL 与 Python
- 了解 pandas / sklearn 等数据分析与建模工具
- 具备良好的数据敏感度与表达能力
""",
    },
]


# ============ 示例分析记录（让历史分析一进入就有数据）============
# 每条引用上面简历 / JD 的下标（0-based），并给出示例评分 / 建议 / 面试问题。
# 注意：这些是「示例分析数据」，用于演示功能；运行真实 AI 分析会追加实时结果。
SAMPLE_ANALYSES: list[dict] = [
    {
        "resume_idx": 0, "job_idx": 0, "match_score": 86,
        "match_summary": (
            "候选人的计算机背景与赛鸣科技实施实习高度契合岗位要求，已具备需求梳理、"
            "接口联调与上线支持经验。建议补充项目管理与等保 / 合规知识，进一步提升现场交付能力。"
        ),
        "interview_questions": [
            "请描述一次你参与的需求梳理到上线的完整过程。",
            "面对客户现场提出的流程变更，你会如何评估与响应？",
            "你如何理解实施顾问在政企项目中的角色？",
        ],
    },
    {
        "resume_idx": 1, "job_idx": 1, "match_score": 81,
        "match_summary": (
            "具备扎实的后端基础与 Redis 优化实战，契合岗位对性能与稳定性的要求。"
            "建议加强微服务与容器化生产经验，并补充高并发场景下的故障排查案例。"
        ),
        "interview_questions": [
            "你用 Redis 做过哪些优化？带来了什么收益？",
            "如何设计一个高并发下的下单接口？",
            "说说你对数据库索引的理解。",
        ],
    },
    {
        "resume_idx": 2, "job_idx": 2, "match_score": 79,
        "match_summary": (
            "Vue3 + TypeScript + Element Plus 技术栈与岗位高度匹配，ECharts 可视化经验是亮点。"
            "建议补充移动端适配与前端性能优化（打包体积、首屏）方面的实践。"
        ),
        "interview_questions": [
            "组件封装时你通常考虑哪些复用与隔离问题？",
            "如何优化一个首屏加载慢的 Vue 页面？",
            "你做过哪些数据可视化项目，遇到什么难点？",
        ],
    },
    {
        "resume_idx": 3, "job_idx": 3, "match_score": 83,
        "match_summary": (
            "统计学背景与 pandas/sklearn 实战符合岗位要求，流失预警项目体现建模能力。"
            "建议增强业务理解，能将分析结论转化为可落地的运营动作。"
        ),
        "interview_questions": [
            "请讲讲你做用户流失预警模型的思路与评价方式。",
            "如何向非技术同学解释一个复杂的分析结果？",
            "A/B 测试在设计时需要注意什么？",
        ],
    },
    {
        "resume_idx": 0, "job_idx": 1, "match_score": 52,
        "match_summary": (
            "候选人的实施与需求经验有价值，但本岗位偏后端研发，候选人缺乏服务端框架与数据库深度的"
            "系统实践，匹配度有限。若转向实施或业务分析岗会更合适。"
        ),
        "interview_questions": [
            "你如何看待从实施转向纯后端研发的差异？",
            "有没有系统学习过某一后端框架的计划？",
            "你更希望从事交付类还是研发类工作？",
        ],
    },
]


async def _auto_seed() -> None:
    """后台任务：数据库为空时灌入演示数据。失败不影响启动。"""
    async with AsyncSessionLocal() as db:
        try:
            count = await db.scalar(select(func.count()).select_from(User))
            if count:
                logger.info("检测到已有用户数据，跳过自动 seed")
                return

            user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
            db.add(user)
            await db.flush()  # 拿到 user.id 供子表外键使用

            # 简历
            resume_ids: list[int] = []
            for r in SAMPLE_RESUMES:
                obj = Resume(owner_id=user.id, title=r["title"], content=r["content"])
                db.add(obj)
                await db.flush()
                resume_ids.append(obj.id)

            # JD
            job_ids: list[int] = []
            for j in SAMPLE_JOBS:
                obj = Job(owner_id=user.id, title=j["title"], description=j["description"])
                db.add(obj)
                await db.flush()
                job_ids.append(obj.id)

            # 示例分析（引用上面的简历 / JD）
            for a in SAMPLE_ANALYSES:
                db.add(
                    Analysis(
                        owner_id=user.id,
                        resume_id=resume_ids[a["resume_idx"]],
                        job_id=job_ids[a["job_idx"]],
                        match_score=a["match_score"],
                        match_summary=a["match_summary"],
                        interview_questions=json.dumps(
                            a["interview_questions"], ensure_ascii=False
                        ),
                    )
                )

            await db.commit()
            logger.info(
                "已灌入演示数据（演示账号 %s：%d 简历 / %d JD / %d 分析）",
                DEMO_EMAIL,
                len(SAMPLE_RESUMES),
                len(SAMPLE_JOBS),
                len(SAMPLE_ANALYSES),
            )
        except Exception as e:  # 演示数据失败不应阻断服务
            await db.rollback()
            logger.warning("自动 seed 失败（可忽略，不影响启动）：%s", e)
