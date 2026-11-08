from csx.application.organize import organize_file


class RecordingDrive:
    def __init__(self):
        self.moves = []

    def move(self, file_id, target_dir):
        self.moves.append((file_id, target_dir))

    def rename(self, file_id, new_name):
        self.moves.append((file_id, new_name))


MEDIA_TV = {"title": "Example", "type": "tv", "year": 2024}
MEDIA_MOVIE = {"title": "Example", "type": "movie", "year": 2024}


def _file_row(**overrides):
    row = {
        "file_id": "f1",
        "season": 1,
        "episode": 1,
        "quality_bucket": "remux",
        "extension": "mkv",
    }
    row.update(overrides)
    return row


def test_type_folder_disabled_keeps_flat_library_root():
    drive = RecordingDrive()

    path = organize_file(drive, _file_row(), MEDIA_TV, library_root="/CSX/媒体库")

    assert path == "/CSX/媒体库/Example (2024)/Season 01/Example (2024) S01E01 [REMUX].mkv"
    assert drive.moves[0] == ("f1", "/CSX/媒体库/Example (2024)/Season 01")


def test_type_folder_enabled_adds_tv_and_movie_directories():
    drive = RecordingDrive()

    tv_path = organize_file(
        drive,
        _file_row(),
        MEDIA_TV,
        library_root="/CSX/媒体库",
        type_folder=True,
        type_movie="电影",
        type_tv="电视剧",
    )
    movie_path = organize_file(
        drive,
        _file_row(season=None, episode=None),
        MEDIA_MOVIE,
        library_root="/CSX/媒体库",
        type_folder=True,
        type_movie="电影",
        type_tv="电视剧",
    )

    assert tv_path.startswith("/CSX/媒体库/电视剧/Example (2024)/Season 01/")
    assert movie_path == "/CSX/媒体库/电影/Example (2024)/Example (2024) [REMUX].mkv"
