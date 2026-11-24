from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi import UploadFile
from app.core.exceptions import DocumentServiceError
from app.services.document_service import DocumentService, LocalParserPipeline


def upload(name, content):
    return UploadFile(filename=name, file=BytesIO(content))


@pytest.mark.parametrize('name,content,message', [('notes.txt', b'abc', 'Only PDF'), ('empty.pdf', b'', 'empty'), ('report.pdf.exe', b'abc', 'Only PDF')])
async def test_reject_invalid_uploads(tmp_path, name, content, message):
    pipeline = AsyncMock()
    service = DocumentService(AsyncMock(), pipeline, str(tmp_path))
    with pytest.raises(DocumentServiceError, match=message):
        await service.upload_document(upload(name, content))
    pipeline.run.assert_not_awaited()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('indexed', [True, False])
async def test_upload_saves_bytes_and_reports_status(tmp_path, indexed):
    pipeline = AsyncMock()
    pipeline.run.return_value = (indexed, 'done')
    response = await DocumentService(AsyncMock(), pipeline, str(tmp_path)).upload_document(upload('test.PDF', b'%PDF-data'))
    saved = Path(response.saved_path)
    assert saved.parent == tmp_path
    assert saved.read_bytes() == b'%PDF-data'
    pipeline.run.assert_awaited_once_with(saved)
    assert response.indexed is indexed
    assert response.status == ('indexed' if indexed else 'uploaded')


async def test_upload_names_are_unique(tmp_path):
    pipeline = AsyncMock()
    pipeline.run.return_value = (False, 'saved')
    service = DocumentService(AsyncMock(), pipeline, str(tmp_path))
    first = await service.upload_document(upload('report.pdf', b'one'))
    second = await service.upload_document(upload('report.pdf', b'two'))
    assert first.saved_path != second.saved_path
    assert Path(first.saved_path).read_bytes() == b'one'
    assert Path(second.saved_path).read_bytes() == b'two'


async def test_list_documents_maps_sources(tmp_path):
    repository = AsyncMock()
    repository.list_sources.return_value = [{'source': 'a.pdf'}, {'source': 'seed'}]
    result = await DocumentService(repository, upload_dir=str(tmp_path)).list_documents()
    assert [item.source for item in result] == ['a.pdf', 'seed']
    repository.list_sources.assert_awaited_once()


async def test_disabled_parser(monkeypatch, tmp_path):
    from app.services import document_service
    monkeypatch.setattr(document_service.settings, 'document_parser_enabled', False)
    assert await LocalParserPipeline().run(tmp_path / 'a.pdf') == (False, 'Document saved; parser pipeline is disabled.')


async def test_missing_parser_directory(monkeypatch, tmp_path):
    from app.services import document_service
    monkeypatch.setattr(document_service.settings, 'document_parser_enabled', True)
    monkeypatch.setattr(document_service.settings, 'parser_service_dir', str(tmp_path / 'missing'))
    with pytest.raises(DocumentServiceError, match='directory not found'):
        await LocalParserPipeline().run(tmp_path / 'a.pdf')
