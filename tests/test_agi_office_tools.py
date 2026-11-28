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


def test_artifact_present(tmp_path, monkeypatch):
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    out = build_default_registry().invoke("main", "artifact.present", {"path": "a.txt"})
    assert out["ok"] is True and out["data_url"].startswith("data:text/plain")


def test_office_write_table(tmp_path, monkeypatch):
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("SASES_AGI_DB", str(tmp_path / "agi.db"))
    reg = build_default_registry()
    out = reg.invoke("main", "office.write", {"path": "t.docx", "lines": ["head"],
        "tables": [[["a", "b"], ["1", "2"]]], "_approved": True})
    assert out["ok"] is True
    text = reg.invoke("main", "office.read", {"path": "t.docx"})["text"]
    assert "a | b" in text and "1 | 2" in text


def test_office_write_image(tmp_path, monkeypatch):
    from PIL import Image
    from docx import Document
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("SASES_AGI_DB", str(tmp_path / "agi.db"))
    Image.new("RGB", (40, 40), "blue").save(str(tmp_path / "i.png"))
    reg = build_default_registry()
    out = reg.invoke("main", "office.write", {"path": "i.docx", "lines": ["x"],
        "images": ["i.png"], "_approved": True})
    assert out["ok"] is True
    assert len(Document(str(tmp_path / "i.docx")).inline_shapes) == 1


def test_office_header_footer_and_xlsx_style(tmp_path, monkeypatch):
    from docx import Document
    from openpyxl import load_workbook
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("SASES_AGI_DB", str(tmp_path / "agi.db"))
    reg = build_default_registry()
    reg.invoke("main", "office.write", {"path": "a.docx", "lines": ["x"],
        "header": "HDR", "footer": "FTR", "_approved": True})
    doc = Document(str(tmp_path / "a.docx"))
    assert doc.sections[0].header.paragraphs[0].text == "HDR"
    assert doc.sections[0].footer.paragraphs[0].text == "FTR"
    reg.invoke("main", "office.write", {"path": "a.xlsx", "rows": [["a", "b"]],
        "bold_header": True, "widths": {"A": 20}, "_approved": True})
    wb = load_workbook(str(tmp_path / "a.xlsx"))
    assert wb.active["A1"].font.bold is True
    assert wb.active.column_dimensions["A"].width == 20
