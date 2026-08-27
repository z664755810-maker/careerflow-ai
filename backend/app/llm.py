"""LLM 调用封装（OpenAI 兼容）。

严格沿用启动包约定：
- key 只走环境变量（LLM_API_KEY），代码不写死任何密钥。
- 默认 base_url 指向智谱 glm-4-flash（免费），DeepSeek 余额不足时可直接切换。
- 任何异常（无 key / 网络错误 / 限流）都返回 None，由调用方优雅降级。

切换模型示例（环境变量）：
  LLM_API_KEY=你的智谱key
  LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
  LLM_MODEL=glm-4-flash
"""
from __future__ import annotations

import os

from openai import OpenAI

from app.config import settings


def ask_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800,
    temperature: float = 0.3,
) -> str | None:
    """调用 LLM 聊天补全，失败返回 None（不抛异常）。"""
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=settings.llm_base_url
            or os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        )
        resp = client.chat.completions.create(
            model=settings.llm_model or os.getenv("LLM_MODEL", "glm-4-flash"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = resp.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        # 网络/限流/鉴权错误一律降级，保证接口不崩
        return None
