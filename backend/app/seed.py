"""自动 seed：应对 Render 临时文件系统重启丢库。

仅当数据库为空（无任何用户）时灌入演示数据，让作品集开箱可用：
- 一个演示账号（ recruiter 一键体验）
- 一份示例简历 + 一份示例 JD（让「AI 分析」功能开箱即用）

已有数据则跳过，绝不覆盖真实用户数据。
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import Job, Resume, User
from app.security import hash_password

logger = logging.getLogger("careerflow.seed")

# 演示账号（作品集演示专用，仅 Render 演示环境使用；生产可关闭 AUTO_SEED）
DEMO_EMAIL = "demo@careerflow.app"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "CareerFlow2026")

SAMPLE_RESUME_TITLE = "示例简历 · 计算机科学与技术（应届）"
SAMPLE_RESUME_CONTENT = """教育背景
天津理工大学中环信息学院 · 计算机科学与技术（本科） · 2027 届

专业技能
- 熟悉 Python / Java 基础，了解 FastAPI、Vue3 等前后端框架
- 掌握 SQL 与关系型数据库基本操作（PostgreSQL / SQLite）
- 了解 RESTful API 设计与 JWT 鉴权流程
- 具备基础 Linux 操作与 Git 协作能力

实习经历
天津市赛鸣科技 · 软件开发实习生
- 参与企业数字化系统的需求梳理与测试用例编写
- 协助完成模块接口联调与数据核对

项目经历
进销存管理系统（Flask + Vue3）
- 负责商品/库存/订单模块的前后端联调与部署
校招面试题库 RAG（FastAPI + Chroma + Vue3）
- 实现文档上传、自动切分向量化与带引用溯源的问答
"""

SAMPLE_JOB_TITLE = "示例 JD · 数字化实施顾问（校招）"
SAMPLE_JOB_CONTENT = """岗位职责
- 负责政企 / 制造行业数字化系统的现场实施、部署与培训
- 对接客户需求，完成数据初始化、流程配置与上线支持
- 整理实施文档，跟踪项目交付进度并协调资源

任职要求
- 计算机 / 信息类相关专业，本科及以上
- 良好的沟通表达能力，能接受出差、不排斥对接客户
- 了解数据库与基本网络知识，有项目实施实习经验优先
- 学习主动、逻辑清晰，能承受一定交付压力
"""


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
            db.add(
                Resume(
                    owner_id=user.id,
                    title=SAMPLE_RESUME_TITLE,
                    content=SAMPLE_RESUME_CONTENT,
                )
            )
            db.add(
                Job(
                    owner_id=user.id,
                    title=SAMPLE_JOB_TITLE,
                    description=SAMPLE_JOB_CONTENT,
                )
            )
            await db.commit()
            logger.info("已灌入演示数据（演示账号 %s）", DEMO_EMAIL)
        except Exception as e:  # 演示数据失败不应阻断服务
            await db.rollback()
            logger.warning("自动 seed 失败（可忽略，不影响启动）：%s", e)
