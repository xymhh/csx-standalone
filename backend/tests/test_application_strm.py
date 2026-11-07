import pytest

from csx.application.strm import StrmService, build_strm_content


class FakeStrmRepository:
    def __init__(self, files):
        self.files = files
        self.records = []

    def list_library_files(self, *, library_file_id=None):
        return [
            row for row in self.files if library_file_id is None or row["id"] == library_file_id
        ]

    def upsert_record(self, library_file_id, strm_path):
        row = next((x for x in self.records if x["library_file_id"] == library_file_id), None)
        if row:
            row["strm_path"] = strm_path
        else:
            self.records.append(
                {
                    "id": len(self.records) + 1,
                    "library_file_id": library_file_id,
                    "strm_path": strm_path,
                }
            )

    def list_records(self, *, library_file_id=None):
        return [
            row
            for row in self.records
            if library_file_id is None or row["library_file_id"] == library_file_id
        ]

    def delete_record(self, record_id):
        self.records = [row for row in self.records if row["id"] != record_id]


def test_build_mount_template_and_direct_content():
    assert (
        build_strm_content("Show/Season 01/E01.mkv", mode="local_mount", local_mount_root="/mnt")
        == "/mnt/Show/Season 01/E01.mkv"
    )
    assert (
        build_strm_content("Show/a b.mkv", mode="template", url_template="https://proxy/{path}")
        == "https://proxy/Show/a%20b.mkv"
    )
    assert (
        build_strm_content("Show/a.mkv", mode="direct", direct_url="https://drive/file")
        == "https://drive/file"
    )


def test_strm_sync_writes_contents_and_upserts_records(tmp_path):
    repo = FakeStrmRepository([{"id": 1, "path": "Show/Season 01/E01.mkv", "provider": "115"}])
    service = StrmService(
        repo,
        strm_settings={
            "strm_root": str(tmp_path),
            "mode": "local_mount",
            "local_mount_root": "/mnt/cloud",
        },
    )
    result = service.sync()
    path = tmp_path / "Show/Season 01/E01.strm"
    assert result.generated == 1
    assert path.read_text() == "/mnt/cloud/Show/Season 01/E01.mkv\n"
    assert repo.records[0]["strm_path"] == str(path)
    assert service.sync().unchanged == 1


def test_strm_sync_cleans_invalidated_file_and_rejects_path_escape(tmp_path):
    path = tmp_path / "removed.strm"
    path.write_text("/mnt/removed.mkv")
    repo = FakeStrmRepository([])
    repo.records = [{"id": 3, "library_file_id": 8, "strm_path": str(path)}]
    result = StrmService(
        repo,
        strm_settings={
            "strm_root": str(tmp_path),
            "mode": "local_mount",
            "local_mount_root": "/mnt",
        },
    ).sync(clean_missing=True)
    assert result.removed == 1 and not path.exists() and not repo.records
    with pytest.raises(ValueError, match="路径无效"):
        build_strm_content("../outside.mkv", mode="direct", direct_url="https://x")


def test_strm_sync_reports_individual_errors(tmp_path):
    repo = FakeStrmRepository([{"id": 2, "path": "Show/E02.mkv"}])
    result = StrmService(
        repo, strm_settings={"strm_root": str(tmp_path), "mode": "local_mount"}
    ).sync()
    assert result.generated == 0
    assert "local_mount_root 未配置" in result.errors[0]["error"]
