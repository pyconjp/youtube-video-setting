import os
import pickle

# from pprint import pprint
from dataclasses import dataclass
from typing import Generator

from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
from googleapiclient.discovery import build  # type: ignore
import openpyxl  # type: ignore


TOKEN_FILENAME = "token.pickle"
CREDENTIAL_FILENAME = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
]

# videos.update で送れる status の書き込み可能なプロパティ。
# ここに無いもの（uploadStatus など）は読み取り専用なので送らない。
# https://developers.google.com/youtube/v3/docs/videos#status
MUTABLE_STATUS_FIELDS = (
    "privacyStatus",
    "license",
    "embeddable",
    "publicStatsViewable",
    "selfDeclaredMadeForKids",
    "containsSyntheticMedia",
)


# video_id, title, status, description, playlist_id, thumbnail
@dataclass
class YoutubeVideo:
    video_id: str
    status: str


def initialize_service(token_filename, credential_filename, scopes, reflash=False):
    """"""
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if not reflash and os.path.exists(token_filename):
        with open(token_filename, "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credential_filename, scopes
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_filename, "wb") as token:
            pickle.dump(creds, token)
    # Build the service object.
    service = build(
        api_service_name, api_version, credentials=creds, cache_discovery=False
    )
    return service


def get_youtube_service():
    service = initialize_service(
        TOKEN_FILENAME,
        CREDENTIAL_FILENAME,
        SCOPES,
        # reflash=True,
    )
    return service


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
    # 管理画面から設定した動画は madeForKids しか返らないことがある。
    if "selfDeclaredMadeForKids" not in status and "madeForKids" in current:
        status["selfDeclaredMadeForKids"] = current["madeForKids"]

    # publishAt は「まだ公開していない private 動画」にだけ指定できる。
    if privacy_status == "private" and "publishAt" in current:
        status["publishAt"] = current["publishAt"]

    status["privacyStatus"] = privacy_status
    return status


def set_video_status(service, video_id: str, status: str):
    current = get_video_status(service, video_id)
    request = service.videos().update(
        part="status",
        body={"id": video_id, "status": build_status_body(current, status)},
    )
    response = request.execute()
    return response


def get_video_list_from_xlsx(filename: str) -> Generator[YoutubeVideo, None, None]:
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        video = YoutubeVideo(row[1], row[2])
        yield video


def main(video: YoutubeVideo):
    service = get_youtube_service()
    video_id = video.video_id
    video_status = video.status

    response = set_video_status(service, video_id, video_status)
    print(response.get("id"), response.get("status"))
    # pprint(response)


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) < 2:
        print("Usage: python set_youtube_title.py <filename>")
        sys.exit()
    filename = args[1]

    videos_info = get_video_list_from_xlsx(filename)

    for i, video in enumerate(videos_info):
        print(i, end=": ")
        main(video)
