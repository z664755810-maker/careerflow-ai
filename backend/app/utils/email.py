"""邮件发送（注册验证码）。

设计要点：
- 标准 SMTP 协议，兼容 Resend / Gmail / 阿里云 DirectMail 等任意服务商。
- 未配置 SMTP（开发态）：`send_verification_code` 直接返回验证码，由调用方透传给前端展示，
  不真正发信，保证演示站点零成本、零依赖也能走通注册。
- 已配置 SMTP 但发送失败：抛出异常，由路由降级为 503，绝不因邮件故障阻断注册。
"""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings


def _send_sync(
    host: str,
    port: int,
    user: str,
    password: str,
    frm: str,
    to: str,
    subject: str,
    body: str,
) -> None:
    """同步发送（在 asyncio.to_thread 中执行，避免阻塞事件循环）。"""
    msg = EmailMessage()
    msg["From"] = frm
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        # 587 等 STARTTLS 端口
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)


async def send_verification_code(email: str, code: str) -> str | None:
    """发送注册验证码。

    Args:
        email: 收件邮箱
        code: 6 位验证码

    Returns:
        - 开发态（未配置 SMTP）：返回 code 本身，由调用方展示在前端
        - 已配置 SMTP：返回 None 表示已成功发送

    Raises:
        配置存在但发送失败：抛出异常，由路由降级 503
    """
    if not settings.smtp_configured:
        return code  # 开发态：不真正发信

    await asyncio.to_thread(
        _send_sync,
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.smtp_from,
        email,
        "CareerFlow 邮箱验证码",
        f"您的注册验证码是：{code}（10 分钟内有效）",
    )
    return None
