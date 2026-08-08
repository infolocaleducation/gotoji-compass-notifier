# GOTOJI Compass 開館時間 自動通知システム

Googleカレンダーに開館予定を入れるだけで、毎朝8:00に当日の開館時間を X と Instagram ストーリーへ自動投稿します。サーバー不要・ランニングコスト0円(GitHub Actions 無料枠で動作)。

## 仕組み

```
毎朝 8:00 JST(GitHub Actions)
  ↓
Googleカレンダーから当日の「開館」予定を取得
  ↓
開館時間カード画像(1080×1920 PNG)を自動生成
  ↓
├── X へ画像付きポスト
└── Instagram ストーリーへ投稿
```

予定タイトルの書き方で、表示内容が変わります:

| タイトルの書き方 | 表示 |
|---|---|
| 「**開館**」を含む(例: 開館、開館(北)) | 開館時間として表示 |
| 「**イベント**」を含む(例: イベント:読書会) | イベント名と時間を表示 |
| 「**貸し切り**」「**貸切**」を含む | 「この時間は一般利用できません」と表示 |
| どれも含まない(打ち合わせ等) | 無視(投稿に影響しない) |

- 時間は**予定の開始・終了時刻**から取ります(タイトルに時刻を書く必要はありません)
- 昼休み休館などは「開館」予定を2つに分けて入れれば、両方の時間帯が表示されます
- 「開館」も「イベント」も無い日は自動で「本日休館」になります
- 複数キーワードを含む場合の優先順位: 貸し切り > イベント > 開館

## 日々の運用(北さんがやること)

**Googleカレンダーに開館予定を入れる。以上。**

## セットアップ手順(最初の1回だけ)

### 1. Google カレンダー連携

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」で **Google Calendar API** を有効化
3. 「認証情報」→「サービスアカウント」を作成し、キー(JSON)をダウンロード
4. 対象のGoogleカレンダーの共有設定で、サービスアカウントのメールアドレス(`xxx@xxx.iam.gserviceaccount.com`)を**閲覧権限**で追加
5. カレンダーの設定画面で「カレンダーID」を控える

### 2. X (旧Twitter) API

1. [X Developer Portal](https://developer.x.com/) で無料プランに登録しアプリを作成
2. アプリの権限を **Read and Write** に設定
3. API Key / API Secret / Access Token / Access Token Secret の4つを控える
   (権限を変更した場合は Access Token を再生成すること)

### 3. Instagram

1. Instagramを**ビジネス(またはクリエイター)アカウント**にし、Facebookページと紐付け
2. [Meta for Developers](https://developers.facebook.com/) でアプリを作成
3. グラフAPIエクスプローラ等で**長期アクセストークン**(60日)と **IGユーザーID** を取得
4. アプリID・アプリシークレットも控える(トークン自動更新に使用)

### 4. GitHub リポジトリ

1. このフォルダを GitHub リポジトリとして push
   - Phase 1〜2(X投稿のみ)の間は **Private** で構いません
   - **Phase 3(Instagram)を有効にする時は Public にしてください。** Instagramに画像を渡すには誰でもアクセスできる画像URLが必要で、Privateリポジトリの raw URL は外部から取得できないためです(公開されるのはコードと生成画像だけで、認証情報は Secrets にあるため公開されません)
2. リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret名 | 内容 |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 手順1でダウンロードしたJSONの中身をそのまま貼り付け |
| `GOOGLE_CALENDAR_ID` | カレンダーID |
| `X_API_KEY` / `X_API_SECRET` | XのAPIキー |
| `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | Xのアクセストークン |
| `IG_USER_ID` | InstagramビジネスアカウントのユーザーID |
| `IG_ACCESS_TOKEN` | Metaの長期アクセストークン |
| `META_APP_ID` / `META_APP_SECRET` | Metaアプリの ID とシークレット(トークン自動更新用) |
| `GH_PAT` | (任意)Secrets書き込み権限つきPAT。あるとIGトークンが全自動更新に |

3. Actions タブ → `daily-post` → **Run workflow** で手動実行してテスト

## 段階的リリース(config.yml)

[config.yml](config.yml) の `features:` で機能を段階的にONにできます。

```yaml
features:
  post_x: true          # Phase 1: Xへテキスト投稿
  attach_image: true    # Phase 2: 画像付きに切り替え
  post_instagram: true  # Phase 3: IGストーリー追加
```

まず `post_x: true` だけで運用を始め、動作を確認しながら順にONにしてください。

## カスタマイズ

- **投稿文**: `config.yml` の `post:` を編集
- **画像の色**: `config.yml` の `image:` を編集
- **背景デザイン画像**: [templates/README.md](templates/README.md) 参照
- **投稿時刻**: `.github/workflows/daily-post.yml` の `cron` を編集(UTC表記。JST−9時間)

## エラー時の動き

- X と Instagram のどちらかが失敗しても、もう片方は投稿されます
- 何か失敗するとジョブが失敗になり、GitHubから**メール通知**が届きます
- Instagramのトークン(60日で失効)は毎週自動チェックされ、期限が近いと自動更新(`GH_PAT` 登録時)またはリマインドIssueが作成されます

## リポジトリ構成

```
gotoji-compass-notifier/
├── .github/workflows/
│   ├── daily-post.yml        # 毎朝の自動投稿
│   └── refresh-ig-token.yml  # IGトークンの自動更新
├── src/
│   ├── calendar_client.py    # カレンダー取得
│   ├── image.py              # 画像生成
│   ├── post_x.py             # X投稿
│   ├── post_instagram.py     # IGストーリー投稿
│   ├── ig_token.py           # IGトークン更新
│   └── main.py               # 全体制御
├── templates/                # 背景画像テンプレート(任意)
├── config.yml                # 投稿文言・色などの設定
└── output/latest.png         # 生成された当日の画像(自動コミット)
```

### 補足

- 生成画像はInstagram投稿用の公開URLを作るため、毎日リポジトリにコミットされます。履歴が肥大化してきたら年1回程度リポジトリを作り直すか、GitHub Pages 方式への切り替えを検討してください。
- API経由のInstagramストーリーはリンク・スタンプ等の装飾が付けられないため、画像単体で情報が完結するデザインになっています。
