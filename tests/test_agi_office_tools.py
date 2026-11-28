def test_office_read_docx(tmp_path, monkeypatch):
    from docx import Document
    from agi.tools import build_default_registry

    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    doc = Document()
    doc.add_paragraph("SASES office test")
    doc.save(str(tmp_path / "a.docx"))
    out = build_default_registry().invoke("main", "office.read", {"path": "a.docx"})
    assert out["ok"] is True
    assert "SASES office test" in out["text"]


def test_office_write_requires_approval(tmp_path, monkeypatch):
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("SASES_AGI_DB", str(tmp_path / "agi.db"))
    reg = build_default_registry()
    assert reg.invoke("main", "office.write", {"path": "a.docx", "lines": ["hi"]})["error"] == "approval_required"
    assert reg.invoke("main", "office.write", {"path": "a.docx", "lines": ["hi"], "_approved": True})["ok"]
    from agi.office_tools import read
    assert "hi" in read({"path": "a.docx"})["text"]


def test_pdf_read_blank(tmp_path, monkeypatch):
    from pypdf import PdfWriter
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    w = PdfWriter(); w.add_blank_page(width=72, height=72); w.write(str(tmp_path / "a.pdf"))
    out = build_default_registry().invoke("main", "pdf.read", {"path": "a.pdf"})
    assert out["ok"] is True and out["pages"] == 1


def test_image_metadata(tmp_path, monkeypatch):
    from PIL import Image
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    Image.new("RGB", (12, 8), "red").save(str(tmp_path / "a.png"))
    out = build_default_registry().invoke("main", "image.read", {"path": "a.png"})
    assert out["ok"] is True and out["width"] == 12 and out["height"] == 8


def test_pdf_ocr_renders_pages(tmp_path, monkeypatch):
    from pypdf import PdfWriter
    from agi import ocr_tools
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    w = PdfWriter(); w.add_blank_page(width=72, height=72); w.write(str(tmp_path / "a.pdf"))
    monkeypatch.setattr(ocr_tools, "_vision_text", lambda img: {"ok": True, "text": "PAGE"})
    out = ocr_tools.pdf({"path": "a.pdf", "max_pages": 1})
    assert out["ok"] is True and out["text"] == "PAGE"
