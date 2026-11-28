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
