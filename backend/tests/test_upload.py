"""文件上传解析测试：.txt/.md 解析、.pdf 解析、不支持类型拒绝。"""
from __future__ import annotations

from tests.conftest import _login, _make_user


def _make_pdf_bytes(text: str) -> bytes:
    """手工构造一个最小可用 PDF（含可提取文本），不依赖具体 PDF 库写入 API。"""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = f"BT /F1 14 Tf 40 250 Td ({text}) Tj ET".encode()
    objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = b"%PDF-1.4\n"
    offsets: list[int] = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + o + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += (
        b"trailer\n<< /Size "
        + str(len(objs) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode()
        + b"\n%%EOF\n"
    )
    return pdf



async def test_upload_txt_and_md(client):
    """测试 .txt / .md 解析、不支持类型拒绝、空文件拒绝。"""
    from app.database import AsyncSessionLocal
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    async with AsyncSessionLocal() as db:
        u = await _make_user(db, "up1@test.com", "password123")
        await db.commit()
    token = await _login("up1@test.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # .txt
        r = await c.post(
            "/api/resumes/upload",
            files={"file": ("resume.txt", b"name: zhang\nphone: 123", "text/plain")},
            data={"title": "上传测试简历"},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        assert "zhang" in r.json()["content"]

        # .md
        r = await c.post(
            "/api/jobs/upload",
            files={"file": ("jd.md", b"# Backend\n- Python", "text/markdown")},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        assert "Backend" in r.json()["description"]

        # 不支持类型（.exe）应 400
        r = await c.post(
            "/api/resumes/upload",
            files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
            headers=headers,
        )
        assert r.status_code == 400

        # 空文件（无文本）应 400
        r = await c.post(
            "/api/resumes/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers=headers,
        )
        assert r.status_code == 400


async def test_upload_pdf(client):
    from app.database import AsyncSessionLocal
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    async with AsyncSessionLocal() as db:
        u = await _make_user(db, "up2@test.com", "password123")
        await db.commit()
    token = await _login("up2@test.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    pdf = _make_pdf_bytes("Hello PDF World")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/resumes/upload",
            files={"file": ("resume.pdf", pdf, "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        # 至少应提取到部分文本（不同 pdf 后端可能略有差异，宽松断言）
        assert r.json()["content"]
