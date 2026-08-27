"""Excel の内容にしたがって YouTube 動画の公開ステータスを変更する。"""

from dataclasses import dataclass
from typing import Generator

import openpyxl  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from youtube_api import (
    MUTABLE_STATUS_FIELDS,
    PRIVACY_STATUSES,
    get_youtube_service,
)


@dataclass
class YoutubeVideo:
    video_id: str
    status: str


def get_video_status(service, video_id: str) -> dict:
    """動画の現在の status パートを取得する。"""
    request = service.videos().list(part="status", id=video_id)
    response = request.execute()
    items = response.get("items", [])
    if not items:
        raise LookupError(f"動画が見つかりません: {video_id}")
    return items[0]["status"]


def build_status_body(current: dict, privacy_status: str) -> dict:
    """現在の status を引き継いだうえで privacyStatus だけ差し替える。

    videos.update はリクエストボディに含めなかった書き込み可能プロパティを
    「消す」仕様なので、privacyStatus だけを送ると license や
    selfDeclaredMadeForKids などが既定値に戻ってしまう。
    そのため取得した値をそのまま詰め直す。
    https://developers.google.com/youtube/v3/docs/videos/update
    """
    status = {key: current[key] for key in MUTABLE_STATUS_FIELDS if key in current}

    # 子ども向け設定は書き込み用のプロパティ名が selfDeclaredMadeForKids。
    # 過去に API 以外から設定された動画は madeForKids しか返らないことがある。
    if "selfDeclaredMadeForKids" not in status and "madeForKids" in current:
        status["selfDeclaredMadeForKids"] = current["madeForKids"]

    # publishAt は「未公開の private 動画」にだけ指定できる。
    if privacy_status == "private" and "publishAt" in current:
        status["publishAt"] = current["publishAt"]

    status["privacyStatus"] = privacy_status
    return status


def set_video_status(service, video_id: str, privacy_status: str) -> dict:
    current = get_video_status(service, video_id)
    request = service.videos().update(
        part="status",
        body={"id": video_id, "status": build_status_body(current, privacy_status)},
    )
    return request.execute()


def get_video_list_from_xlsx(filename: str) -> Generator[YoutubeVideo, None, None]:
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        video = YoutubeVideo(row[1], row[2])
        yield video


def main(filename: str) -> int:
    service = get_youtube_service()
    failed = 0

    for i, video in enumerate(get_video_list_from_xlsx(filename)):
        print(i, video.video_id, end=": ")
        if video.status not in PRIVACY_STATUSES:
            failed += 1
            print(f"NG 未対応のステータスです: {video.status!r}")
            continue
        try:
            response = set_video_status(service, video.video_id, video.status)
        except (HttpError, LookupError) as e:
            # 1本失敗しても残りの動画の処理は続ける。
            failed += 1
            print(f"NG {e}")
            continue
        print(response["status"]["privacyStatus"])

    if failed:
        print(f"{failed} 本の動画で失敗しました")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) < 2:
        print("Usage: python set_youtube_status.py <filename>")
        sys.exit(1)
    sys.exit(main(args[1]))
