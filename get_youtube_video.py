"""再生リストの動画一覧を取得して Excel に書き出す。"""

import argparse
import os
from dataclasses import dataclass
from datetime import datetime

import openpyxl  # type: ignore
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE  # type: ignore

from youtube_api import get_youtube_service

# PyCon JP 2024 の再生リスト。環境変数 YOUTUBE_PLAYLIST_ID か
# コマンドライン引数で上書きできる。
DEFAULT_PLAYLIST_ID = "PLMkWB0UjwFGmeCsQBaDYh1pcoDdSXaCQG"

# playlistItems.list / videos.list の 1 リクエストあたりの最大件数。
MAX_RESULTS = 50


@dataclass
class YoutubeVideo:
    id: str
    title: str
    description: str | None = None
    status: str | None = None
    playlist_id: str | None = None


def get_playlist_videos(service, playlist_id: str) -> list[YoutubeVideo]:
    """再生リストに入っている動画をすべて取得する。"""
    next_page_token = ""
    items: list[YoutubeVideo] = []
    while True:
        response = (
            service.playlistItems()
            .list(
                part="id,snippet",
                playlistId=playlist_id,
                maxResults=MAX_RESULTS,
                pageToken=next_page_token,
            )
            .execute()
        )
        for item in response["items"]:
            snippet = item["snippet"]
            items.append(
                YoutubeVideo(
                    id=snippet["resourceId"]["videoId"],
                    title=snippet["title"],
                    description=snippet["description"],
                    playlist_id=playlist_id,
                )
            )
        next_page_token = response.get("nextPageToken", "")
        if not next_page_token:
            break
    return items


def fill_privacy_status(service, videos: list[YoutubeVideo]) -> None:
    """各動画の公開ステータスを videos.list でまとめて取得して埋める。

    playlistItems.list は公開ステータスを返さないため別途取得する。
    50件ずつまとめて問い合わせるのでクォータの消費は 1 件あたり 1 ユニット未満。
    """
    by_id = {video.id: video for video in videos}
    ids = list(by_id)
    for start in range(0, len(ids), MAX_RESULTS):
        chunk = ids[start : start + MAX_RESULTS]
        response = service.videos().list(part="status", id=",".join(chunk)).execute()
        for item in response.get("items", []):
            by_id[item["id"]].status = item["status"]["privacyStatus"]


def _clean(value: str | None) -> str | None:
    """Excel に書けない制御文字を取り除く。"""
    if value is None:
        return None
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def save_excel(items: list[YoutubeVideo]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Videos"
    ws.append(["ID", "Title", "Description", "Status", "Playlist ID"])
    for item in items:
        ws.append(
            [
                item.id,
                _clean(item.title),
                _clean(item.description),
                item.status,
                item.playlist_id,
            ]
        )
    now = datetime.now()
    filename = f"youtube-videos-{now:%Y%m%d}.xlsx"
    wb.save(filename)
    return filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "playlist_id",
        nargs="?",
        default=os.environ.get("YOUTUBE_PLAYLIST_ID", DEFAULT_PLAYLIST_ID),
        help="対象の再生リスト ID（環境変数 YOUTUBE_PLAYLIST_ID でも指定できる）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = get_youtube_service()

    items = get_playlist_videos(service, args.playlist_id)
    fill_privacy_status(service, items)

    # 再生リストは新しい動画が先頭に来るので、古い順に並べ直して書き出す。
    filename = save_excel(items[::-1])
    print(f"{len(items)} 本の動画を {filename} に書き出しました")


if __name__ == "__main__":
    main()
