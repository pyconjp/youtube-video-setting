"""Excel の内容にしたがって YouTube 動画のサムネイルを設定する。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import openpyxl  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from googleapiclient.http import MediaFileUpload  # type: ignore

from youtube_api import BASE, get_youtube_service

THUMB_DIR = BASE / "thumbnails"

# thumbnails.set が受け付ける形式とサイズ上限。
# https://developers.google.com/youtube/v3/docs/thumbnails/set
MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_THUMB_BYTES = 2 * 1024 * 1024


@dataclass
class YoutubeThumb:
    video_id: str
    thumb: str

    @property
    def thumb_filename(self) -> str:
        # Excel には拡張子なしのファイル名が入っている想定。
        if Path(self.thumb).suffix.lower() in MIME_TYPES:
            return self.thumb
        return f"{self.thumb}.png"


def find_thumb_path(thumb_filename: str) -> Path:
    """サムネイル画像のパスを検証して返す。"""
    thumb_path = THUMB_DIR / thumb_filename
    if not thumb_path.is_file():
        raise FileNotFoundError(f"サムネイルがありません: {thumb_path}")

    suffix = thumb_path.suffix.lower()
    if suffix not in MIME_TYPES:
        raise ValueError(f"対応していない画像形式です: {thumb_path.name}")

    size = thumb_path.stat().st_size
    if size > MAX_THUMB_BYTES:
        raise ValueError(
            f"サムネイルが 2MB を超えています ({size / 1024 / 1024:.2f}MB): "
            f"{thumb_path.name}"
        )
    return thumb_path


def set_video_thumb(service, video_id: str, thumb_filename: str) -> dict:
    thumb_path = find_thumb_path(thumb_filename)
    request = service.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(
            str(thumb_path),
            mimetype=MIME_TYPES[thumb_path.suffix.lower()],
        ),
    )
    return request.execute()


def get_video_list_from_xlsx(filename: str) -> Generator[YoutubeThumb, None, None]:
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        video = YoutubeThumb(row[1], row[3])
        yield video


def main(filename: str) -> int:
    service = get_youtube_service()
    failed = 0

    for i, video in enumerate(get_video_list_from_xlsx(filename)):
        print(i, video.video_id, end=": ")
        try:
            response = set_video_thumb(service, video.video_id, video.thumb_filename)
        except (HttpError, FileNotFoundError, ValueError) as e:
            # 1本失敗しても残りの動画の処理は続ける。
            failed += 1
            print(f"NG {e}")
            continue
        # thumbnails.set のレスポンスは items だけを返す（id や status は無い）。
        items = response.get("items", [])
        default = items[0].get("default", {}) if items else {}
        print(default.get("url", "OK"))

    if failed:
        print(f"{failed} 本の動画で失敗しました")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) < 2:
        print("Usage: python set_youtube_thumb.py <filename>")
        sys.exit(1)
    sys.exit(main(args[1]))
