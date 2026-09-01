"""文件解析工具：从上传的简历 / JD 文件中提取纯文本。

支持类型：
- .txt / .md / .markdown：直接按编码读取（utf-8 / gbk / latin-1 兜底）
- .pdf：使用 pypdf 提取每页文本
- .docx：使用 python-docx 提取段落文本

所有解析失败以 ValueError 抛出，由路由层转换为 400。
"""
from __future__ import annotations

import io
import os

_ALLOWED_EXT = {".txt", ".md", ".markdown", ".pdf", ".docx"}
_MAX_BYTES = 3 * 1024 * 1024  # 3MB 上限，避免超大文件撑爆内存


def extract_text_from_file(filename: str, content: bytes) -> str:
    """根据扩展名分发到对应解析器，返回提取到的文本。"""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError(
            f"不支持的文件类型：{ext or '无扩展名'}。"
            f"仅支持 {' / '.join(sorted(_ALLOWED_EXT))}"
        )
    if len(content) > _MAX_BYTES:
        raise ValueError("文件过大（上限 3MB），请压缩或拆分后重试")

    if ext in {".txt", ".md", ".markdown"}:
        return _decode_text(content)
    if ext == ".pdf":
        return _extract_pdf(content)
    if ext == ".docx":
        return _extract_docx(content)
    raise ValueError("不支持的文件类型")


def _decode_text(content: bytes) -> str:
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF 解析依赖未安装（pypdf），请联系管理员")
    reader = PdfReader(io.BytesIO(content))
    parts = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(parts).strip()


def _extract_docx(content: bytes) -> str:
    try:
        import docx
    except ImportError:
        raise ValueError("DOCX 解析依赖未安装（python-docx），请联系管理员")
    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs).strip()
