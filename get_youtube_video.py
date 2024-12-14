import os
from datetime import datetime
import pickle
from pprint import pprint
from dataclasses import dataclass

from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
from googleapiclient.discovery import build  # type: ignore
import openpyxl  # type: ignore


TOKEN_FILENAME = "token.pickle"
CREDENTIAL_FILENAME = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
]


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


@dataclass
class YoutubeVideo:
    id: str
    title: str
    status: str | None = None
    description: str | None = None
    playlist_id: str | None = None


def save_excel(items: list[YoutubeVideo]):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Videos"
    ws.append(["ID", "Title", "Status", "Description", "Playlist ID"])
    for item in items:
        ws.append(
            [item.id, item.title, item.status, item.description, item.playlist_id]
        )
    now = datetime.now()
    wb.save(f"youtube-videos-{now:%Y%m%d}.xlsx")


def main():
    service = get_youtube_service()

    # channel_id = "UCxNoKygeZIE1AwZ_NdUCkhQ"
    # next_page_token = ""
    # playlist_id = ""
    # while True:
    #     playlists_request = (
    #         service.playlists()
    #         .list(part="id,snippet", channelId=channel_id, pageToken=next_page_token)
    #         .execute()
    #     )
    #     for item in playlists_request["items"]:
    #         playlist_title = item["snippet"]["title"]
    #         if "2024" in playlist_title:
    #             playlist_id = item["id"]
    #             break
    #         print(item["snippet"]["title"])
    #     next_page_token = playlists_request.get("nextPageToken", "")
    #     if not next_page_token:
    #         break
    # pprint(playlist_id)

    #
    playlist_id = "PLMkWB0UjwFGmeCsQBaDYh1pcoDdSXaCQG"

    next_page_token = ""
    items = []
    while True:
        search_response = (
            service.playlistItems()
            .list(
                part="id,snippet",
                playlistId=playlist_id,
                maxResults=50,
                # q="",
                pageToken=next_page_token,
            )
            .execute()
        )
        for item in search_response["items"]:
            # pprint(item)
            id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            video = YoutubeVideo(id, title)
            items.append(video)
        next_page_token = search_response.get("nextPageToken", "")
        if not next_page_token:
            break
    save_excel(reversed(items))
    pprint(items)
    print(len(items))


if __name__ == "__main__":
    main()
