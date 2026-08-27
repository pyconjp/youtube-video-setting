# YouTube Video Setting

YouTube 動画を API 経由で設定する

対象 API: [YouTube Data API v3](https://developers.google.com/youtube/v3)

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
  - https://www.googleapis.com/auth/youtube
- OAuth クライアント ID の作成
  - OAuth デスクトップアプリ
  - 名前: 任意の名前
  - クライアント ID: 表示されるので記録
  - シークレット: 表示されるので記録
  - 認証 JSON をダウンロード

### 環境構築

- [uv](https://docs.astral.sh/uv/) で依存関係を入れる
  - `uv sync`
- 以降のコマンドは `uv run python ...` で実行する

## スクリプトの実行

- ダウンロードした認証 JSON を、プロジェクトルートに `client_secret.json` で設置
- 初回実行時にブラウザが開くので、PyCon JP のアカウントで認可する
  - 認可結果は `token.json` に保存され、次回以降は自動で再利用される
  - 認可をやり直したいときは `token.json` を削除する
- 動画リストダウンロードの実行
  - `uv run python get_youtube_video.py [PLAYLIST_ID]`
  - 再生リスト ID は引数か環境変数 `YOUTUBE_PLAYLIST_ID` で指定できる（省略時は既定値）
  - Excel ファイル（`youtube-videos-YYYYMMDD.xlsx`）が取得できる
    - カラムは ID / Title / Description / Status / Playlist ID
    - Status には現在の公開ステータスが入る
- 動画のタイトルと説明文を入れる
  - `uv run python set_youtube_title.py EXCEL_FILENAME`
  - Excel ファイルは以下のカラムが必要
    - Video ID
    - Status ・・現状使っていない
    - Video タイトル
    - Video ディスクリプション
- 動画のステイタスを変更する
  - `uv run python set_youtube_status.py EXCEL_FILENAME`
  - Excel ファイルには以下のカラムが必要
    - Check ・・使っていない（空の行はスキップされる）
    - Video ID
    - Status ・・ `public` or `private`, `unlisted` を入れる
- 動画のサムネイルを入れる
  - `uv run python set_youtube_thumb.py EXCEL_FILENAME`
  - Excel ファイルは以下のカラムが必要
    - Check ・・使っていない（空の行はスキップされる）
    - Video ID
    - Status ・・現状使っていない
    - thumb (サムネイルのファイルID(.pngを除くファイル名))
  - 画像は `thumbnails/` に置く。PNG / JPEG の 2MB 以内

## 補足

### 更新時の挙動

`videos.update` は **リクエストに含めなかった書き込み可能なプロパティを消す** 仕様
（[公式ドキュメント](https://developers.google.com/youtube/v3/docs/videos/update)）。
そのため各スクリプトは更新前に `videos.list` で現在の値を取得し、
変更したい項目だけを差し替えてから送信している。
これによりライセンス・埋め込み許可・子ども向け設定
（`selfDeclaredMadeForKids`）・AI 生成コンテンツの申告
（`containsSyntheticMedia`）・タグなどが意図せず初期化されるのを防いでいる。

### クォータ

1日のクォータは既定で 10,000 ユニット。おおよその消費は以下のとおり。

| 操作 | 消費ユニット |
| --- | --- |
| `videos.list`（50件まとめて） | 1 |
| `videos.update` | 50 |
| `playlistItems.list` | 1 |
| `thumbnails.set` | 50 |

1本の動画にタイトル・ステータス・サムネイルをすべて設定すると
約 152 ユニット消費するので、1日あたり 60 本強が目安。

2026年6月からは `videos.insert` と `search.list` がメソッドごとの
個別クォータに分かれている
（[Revision History](https://developers.google.com/youtube/v3/revision_history)）。
本スクリプトはどちらも使っていないため影響はない。

### エラー時の挙動

各スクリプトは1本の動画で失敗しても処理を続け、最後に失敗件数を表示して
終了コード 1 で終わる。どの動画で失敗したかは実行ログを確認する。
