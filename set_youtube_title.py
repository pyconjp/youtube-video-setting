import os
import pickle
from pprint import pprint
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


# video_id, title, status, description, playlist_id, thumbnail
@dataclass
class YoutubeVideo:
    video_id: str
    title: str | None
    description: str | None


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


def get_video_info(service, video_id):
    request = service.videos().list(
        part="snippet",
        id=video_id,
    )
    response = request.execute()
    return response["items"][0]["snippet"]


def set_video_snippet(service, video_id, snippet):
    request = service.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": snippet,
        },
    )
    response = request.execute()
    return response


def get_video_list_from_xlsx(filename: str) -> Generator[YoutubeVideo, None, None]:
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        video = YoutubeVideo(row[0], row[2], row[3])
        yield video


def main(video: YoutubeVideo):
    service = get_youtube_service()
    video_id = video.video_id
    video_title = video.title
    video_description = video.description

    snippet = get_video_info(service, video_id)
    # del snippet["publishedAt"]
    snippet["title"] = video_title
    snippet["description"] = video_description
    # pprint(snippet)
    response1 = set_video_snippet(service, video_id, snippet)
    print(response1.get("id"), video_title)
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
