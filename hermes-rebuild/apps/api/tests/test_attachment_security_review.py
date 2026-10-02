"""Independent checks for parser and private-store trust boundaries."""

from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from hermes_api.attachment_object_store import LocalPrivateStore, make_store
from hermes_api.attachment_validation import AttachmentValidationError, inspect_file
from hermes_api.settings import Settings


@pytest.mark.parametrize("action", ["/URI", "/GoToR", "/GoToE", "/Launch"])
def test_external_pdf_actions_are_rejected_even_inside_indirect_objects(tmp_path, action):
    writer = PdfWriter()
    page = writer.add_blank_page(width=240, height=320)
    action_ref = writer._add_object(
        DictionaryObject(
            {
                NameObject("/S"): NameObject(action),
                NameObject("/F"): TextStringObject("QA_TEST_external.pdf"),
                NameObject("/URI"): TextStringObject("https://example.invalid/QA_TEST"),
            }
        )
    )
    page[NameObject("/A")] = action_ref
    path = tmp_path / "QA_TEST_external_action.pdf"
    with path.open("wb") as output:
        writer.write(output)
    with pytest.raises(AttachmentValidationError) as failure:
        inspect_file(path, "application/pdf")
    assert failure.value.code == "PDF_ACTIVE_CONTENT"


def test_local_objects_are_immutable_and_opaque(tmp_path):
    store = LocalPrivateStore(tmp_path / "private")
    store.put_stream("QA_TEST_key", [b"QA_TEST_original"], 64)
    with pytest.raises(FileExistsError):
        store.put_stream("QA_TEST_key", [b"replacement"], 64)
    with store.open("QA_TEST_key") as original:
        assert original.read() == b"QA_TEST_original"
    for key in ("../outside", "nested/other", "..\\outside", ""):
        with pytest.raises(ValueError):
            store.open(key)


def test_private_store_never_follows_existing_symlink(tmp_path):
    target = tmp_path / "QA_TEST_outside"
    target.write_bytes(b"QA_TEST_private_outside")
    store = LocalPrivateStore(tmp_path / "private")
    link = store.root / "QA_TEST_link"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This Windows test account lacks the OS privilege to create symlink fixtures.")
    with pytest.raises((ValueError, OSError)):
        store.open("QA_TEST_link")
    assert target.read_bytes() == b"QA_TEST_private_outside"


def test_default_development_storage_is_inside_ignored_local_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = make_store(Settings(environment="test", attachment_local_root=""))
    assert store.root.is_relative_to(Path(tmp_path) / ".local")
