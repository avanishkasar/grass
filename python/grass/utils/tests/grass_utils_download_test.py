"""Tests of grass.utils.download"""

import io
import tarfile
import zipfile

import pytest

from grass.utils import download
from grass.utils.download import DownloadError, download_and_extract


@pytest.fixture
def zip_archive(tmp_path):
    """ZIP archive with a project directory"""
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as archive_file:
        archive_file.writestr("project/PERMANENT/DEFAULT_WIND", "proj: 3\n")
    return archive


@pytest.fixture
def tar_archive(tmp_path):
    """Compressed TAR archive with a project directory"""
    archive = tmp_path / "project.tar.gz"
    content = b"proj: 3\n"
    with tarfile.open(archive, "w:gz") as archive_file:
        info = tarfile.TarInfo("project/PERMANENT/DEFAULT_WIND")
        info.size = len(content)
        archive_file.addfile(info, io.BytesIO(content))
    return archive


@pytest.mark.parametrize("archive", ["zip_archive", "tar_archive"])
def test_extract_from_file_url(request, archive):
    """Archive on the local disk is extracted when given with the file scheme"""
    directory = download_and_extract(request.getfixturevalue(archive).as_uri())

    assert (directory / "PERMANENT" / "DEFAULT_WIND").is_file()


@pytest.fixture
def opened_archives(monkeypatch):
    """Record the archive objects which extract_tar and extract_zip open"""
    opened = []
    original_tar_open = tarfile.open
    original_zip_file = zipfile.ZipFile

    def tar_open(*args, **kwargs):
        archive = original_tar_open(*args, **kwargs)
        opened.append(archive)
        return archive

    def zip_file(*args, **kwargs):
        archive = original_zip_file(*args, **kwargs)
        opened.append(archive)
        return archive

    monkeypatch.setattr(download.tarfile, "open", tar_open)
    monkeypatch.setattr(download.zipfile, "ZipFile", zip_file)
    return opened


@pytest.mark.parametrize("archive", ["zip_archive", "tar_archive"])
def test_extract_closes_archive(request, archive, opened_archives):
    """The archive file is closed after it is extracted"""
    source = request.getfixturevalue(archive).as_uri()
    opened_archives.clear()  # Ignore the archive written by the fixture.
    download_and_extract(source)

    assert len(opened_archives) == 1
    archive_file = opened_archives[0]
    if isinstance(archive_file, tarfile.TarFile):
        assert archive_file.closed
    else:
        assert archive_file.fp is None


def test_extract_from_file_url_not_a_zip(tmp_path):
    """A local file with a .zip name which is not a ZIP is reported as an error

    The content type of a file URL is not checked (it is unreliable), so an
    invalid ZIP has to be caught during extraction.
    """
    archive = tmp_path / "project.zip"
    archive.write_text("This is not a ZIP file.\n")

    with pytest.raises(DownloadError, match="ZIP file is unreadable"):
        download_and_extract(archive.as_uri())


@pytest.mark.parametrize(
    "source",
    [
        "/home/user/project.zip",
        "C:\\data\\project.zip",
        "custom://example.org/project.zip",
    ],
)
def test_unsupported_url_scheme(source):
    """URL with an unsupported scheme is rejected

    A path without a scheme is not a URL, so it is rejected as well.
    """
    with pytest.raises(DownloadError, match="Unsupported URL"):
        download_and_extract(source)
