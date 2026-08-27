"""YouTube Data API v3 を使うための共通処理。

各スクリプトから使う認証まわり・サービス生成を1か所にまとめている。
"""

from pathlib import Path

from google.auth.exceptions import RefreshError  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore

BASE = Path(__file__).resolve().parent

# 認証情報の保存先。google-auth が公式にサポートする JSON 形式を使う。
TOKEN_PATH = BASE / "token.json"
# 以前のバージョンで使っていた pickle 形式のトークン。
LEGACY_TOKEN_PATH = BASE / "token.pickle"
CREDENTIAL_PATH = BASE / "client_secret.json"

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
]

# videos.list / videos.update で扱う status の書き込み可能なプロパティ。
# https://developers.google.com/youtube/v3/docs/videos#status
MUTABLE_STATUS_FIELDS = (
    "privacyStatus",
    "license",
    "embeddable",
    "publicStatsViewable",
    "selfDeclaredMadeForKids",
    "containsSyntheticMedia",
)

# videos.update で送ってよい snippet のプロパティ。
# title と categoryId は snippet を更新するときの必須項目。
MUTABLE_SNIPPET_FIELDS = (
    "title",
    "categoryId",
    "description",
    "tags",
    "defaultLanguage",
    "defaultAudioLanguage",
)

PRIVACY_STATUSES = frozenset({"public", "private", "unlisted"})


def _load_credentials() -> Credentials | None:
    """保存済みの認証情報を読み込む。無ければ None を返す。"""
    if not TOKEN_PATH.exists():
        if LEGACY_TOKEN_PATH.exists():
            print(
                f"{LEGACY_TOKEN_PATH.name} は使わなくなりました。"
                f"ブラウザで再認証して {TOKEN_PATH.name} を作り直します。"
                f"（{LEGACY_TOKEN_PATH.name} は削除して構いません）"
            )
        return None
    return Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)


def _save_credentials(creds: Credentials) -> None:
    """認証情報を JSON で保存する。他ユーザーから読めないよう権限を絞る。"""
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)


def _run_oauth_flow() -> Credentials:
    """ブラウザを開いて OAuth 2.0 の認可フローを実行する。"""
    if not CREDENTIAL_PATH.exists():
        raise SystemExit(
            f"{CREDENTIAL_PATH.name} が見つかりません。"
            "GCP でダウンロードした OAuth クライアントの JSON を"
            "プロジェクトルートに置いてください。"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIAL_PATH), SCOPES)
    # run_local_server は認可レスポンスの URL を https に書き換えてから
    # oauthlib に渡すので、OAUTHLIB_INSECURE_TRANSPORT の設定は不要。
    return flow.run_local_server(port=0)


def get_credentials(refresh: bool = False) -> Credentials:
    """有効な認証情報を返す。必要なら更新・再認証する。

    Args:
        refresh: True にすると保存済みトークンを無視して認証をやり直す。
    """
    creds = None if refresh else _load_credentials()

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # OAuth 同意画面が「テスト」状態のリフレッシュトークンは
            # 7日で失効する。その場合は認証をやり直す。
            print("トークンの更新に失敗しました。認証をやり直します。")
            creds = None

    if not creds or not creds.valid:
        creds = _run_oauth_flow()

    _save_credentials(creds)
    return creds


def get_youtube_service(refresh: bool = False):
    """認証済みの YouTube Data API v3 サービスオブジェクトを返す。"""
    creds = get_credentials(refresh=refresh)
    return build(
        API_SERVICE_NAME,
        API_VERSION,
        credentials=creds,
        cache_discovery=False,
    )
