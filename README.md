# YouTube Video Setting

YouTube 動画を API 経由で設定する

## スクリプトを使うための準備

### YouTube API の利用

- PyCon JP のアカウントで作業
- GCP プロジェクトを任意の名前で作る
- YouTube Data API V3 の有効化

### 認証設定

- OAuth 同意画面・・「内部」
- アプリ名
  - 任意の名前
  - サポートメールは担当者のメアド
- スコープ　以下を設定する
  - https://www.googleapis.com/auth/youtubepartner
  - https://www.googleapis.com/auth/youtube
- OAuth クライアント ID の作成
  - OAuth デスクトップアプリ
  - 名前: 任意の名前
  - クライアント ID: 表示されるので記録
  - シークレット: 表示されるので記録
  - 認証 JSON をダウンロード

## スクリプトの実行

- ダウンロードした認証 JSON を、プロジェクトルートに `client_secret.json` で設置
- 動画リストダウンロードの実行
  - `python get_youtube_video.py`
  - Excel ファイルが取得できる
- 動画のタイトルと説明文を入れる
  - `python set_youtube_title.py EXCEL_FILENAME`
  - Excel ファイルは以下のカラムが必要
    - Video ID
    - Status ・・現状使っていない
    - Video タイトル
    - Video ディスクリプション
