from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock
import importlib.util
from fastapi import UploadFile
from app.services.document_service import DocumentService

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'Мельничек 2_раздел.pdf'

async def test_real_pdf_upload_and_text_extraction(tmp_path):
    spec = importlib.util.spec_from_file_location('pdf_extractor_for_test', ROOT / 'neo4j/parser_service/parser/extract_text.py')
    # dataclasses needs the module registered while its class is created
    import sys
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        original = PDF.read_bytes()
        pipeline = AsyncMock()
        pipeline.run.return_value = (False, 'not indexed')
        response = await DocumentService(AsyncMock(), pipeline, str(tmp_path / 'uploads')).upload_document(
            UploadFile(filename=PDF.name, file=BytesIO(original))
        )
        saved = Path(response.saved_path)
        assert saved.read_bytes() == original
        document = module.extract_pdf_to_intermediate(saved, tmp_path / 'extracted')
        assert len(document.raw_text) > 100
        assert document.txt_path.read_text(encoding='utf-8') == document.raw_text
        assert document.md_path.stat().st_size > 0
    finally:
        sys.modules.pop(spec.name, None)
