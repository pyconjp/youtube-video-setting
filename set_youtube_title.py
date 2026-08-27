"""Excel の内容にしたがって YouTube 動画のタイトルと説明文を設定する。"""

from dataclasses import dataclass
from typing import Generator

import openpyxl  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from youtube_api import MUTABLE_SNIPPET_FIELDS, get_youtube_service


@dataclass
class YoutubeVideo:
    video_id: str
    title: str | None
    description: str | None


def get_video_snippet(service, video_id: str) -> dict:
    """動画の現在の snippet パートを取得する。"""
    request = service.videos().list(part="snippet", id=video_id)
    response = request.execute()
    items = response.get("items", [])
    if not items:
        raise LookupError(f"動画が見つかりません: {video_id}")
    return items[0]["snippet"]


def build_snippet_body(
    current: dict, title: str | None, description: str | None
) -> dict:
    """現在の snippet を引き継いだうえでタイトルと説明文を差し替える。

    videos.update はリクエストボディに含めなかった書き込み可能プロパティを
    「消す」仕様なので、tags や defaultLanguage も詰め直す必要がある。
    thumbnails や channelTitle などの読み取り専用プロパティは送らない。
    https://developers.google.com/youtube/v3/docs/videos/update
    """
    snippet = {key: current[key] for key in MUTABLE_SNIPPET_FIELDS if key in current}

    if title is not None:
        snippet["title"] = title
    if description is not None:
        snippet["description"] = description

    # snippet を更新するときは title と categoryId が必須。
    for key in ("title", "categoryId"):
        if not snippet.get(key):
            raise ValueError(f"snippet の更新には {key} が必要です")
    return snippet


def set_video_snippet(service, video_id: str, snippet: dict) -> dict:
    request = service.videos().update(
        part="snippet",
        body={"id": video_id, "snippet": snippet},
    )
    return request.execute()


def get_video_list_from_xlsx(filename: str) -> Generator[YoutubeVideo, None, None]:
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        video = YoutubeVideo(row[0], row[2], row[3])
        yield video


def main(filename: str) -> int:
    service = get_youtube_service()
    failed = 0

    for i, video in enumerate(get_video_list_from_xlsx(filename)):
        print(i, video.video_id, end=": ")
        try:
            current = get_video_snippet(service, video.video_id)
            snippet = build_snippet_body(current, video.title, video.description)
            response = set_video_snippet(service, video.video_id, snippet)
        except (HttpError, LookupError, ValueError) as e:
            # 1本失敗しても残りの動画の処理は続ける。
            failed += 1
            print(f"NG {e}")
            continue
        print(response["snippet"]["title"])

    if failed:
        print(f"{failed} 本の動画で失敗しました")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) < 2:
        print("Usage: python set_youtube_title.py <filename>")
        sys.exit(1)
    sys.exit(main(args[1]))
