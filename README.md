# RSS Feed Automation

このリポジトリは、VPSサーバーで実行していたcronジョブをGitHub Actionsで代替するものです。

## 概要

以下のタスクを自動実行します：

1. **RSS フィード収集・フィルタリング**: 複数の物理学関連RSSフィード（arXiv、APS）から論文情報を収集し、キーワードでフィルタリング
2. **RSS期間チェック**: APS RSSフィードの記事の期間をチェック
3. **メール送信**: フィルタリングされた論文情報をメールで送信

## セットアップ

### 1. Gmailアプリパスワードの生成

1. Googleアカウントで2段階認証を有効化
2. アプリパスワードを生成: https://myaccount.google.com/apppasswords
   - アプリ名: 任意（例: "RSS to Email"）
   - 16文字のパスワードが生成されます

### 2. GitHub Repository Secretsの設定

リポジトリの **Settings > Secrets and variables > Actions > New repository secret** で以下の2つのシークレットを設定してください：

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `GMAIL_ADDRESS` | 送信元・送信先のGmailアドレス | `Kazuya.Mitsutani@gmail.com` |
| `GMAIL_APP_PASSWORD` | 生成したGmailアプリパスワード（16文字） | `abcd efgh ijkl mnop` |

**重要**: アプリパスワードはスペースを含めても除いても動作しますが、そのままコピー&ペーストしてください。

## スクリプト

### `scripts/papers_iefl.py`

複数のRSSフィードから論文を収集し、キーワードでフィルタリングします。

**キーワード例:**
- Strong: `modular Hamiltonian`, `entanglement hamiltonian`, `measurement-induced`, `QNEC`, `Bekenstein`
- Weak: `modular`, `entanglement`, `CFT`, `holographic`, `quantum field theory`

**使用方法:**
```bash
python scripts/papers_iefl.py [output_file]
```

### `scripts/rss_duration.py`

APS RSSフィードの記事の日付範囲をチェックし、期間が短い場合に警告を出します。

**使用方法:**
```bash
python scripts/rss_duration.py [--log-level INFO]
```

### `scripts/send_rss_email.py`

RSSフィードの内容をメールで送信します（r2eの代替）。

**使用方法:**
```bash
python scripts/send_rss_email.py \
  --rss-file filtered.xml \
  --to recipient@example.com \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-email@gmail.com \
  --smtp-password your-password \
  --days-back 1
```

## GitHub Actions

`.github/workflows/rss-to-email.yml` で以下のスケジュールで実行されます：

- 毎日 5:00 AM UTC (日本時間 14:00)
- 手動トリガーも可能（ActionsタブのRun workflowボタン）

## ローカルテスト

```bash
# 依存関係をインストール
pip install -r requirements.txt

# RSSフィードを生成
python scripts/papers_iefl.py filtered.xml

# RSS期間チェック
python scripts/rss_duration.py --log-level INFO

# メール送信テスト
python scripts/send_rss_email.py \
  --rss-file filtered.xml \
  --to your-email@gmail.com \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-email@gmail.com \
  --smtp-password "your-gmail-app-password" \
  --from your-email@gmail.com
```

## 元のcronジョブ

以下のcronジョブから移行しました：

```cron
MAILTO=Kazuya.Mitsutani@gmail.com
0 5 * * *  /home/ubuntu/rssenv/bin/python /home/ubuntu/.local/bin/papers_iefl.py && /usr/bin/r2e run
0 5 * * *  python /home/ubuntu/.local/bin/rss_duration.py
```

## トラブルシューティング

### メールが届かない場合

1. GitHub Repository Secretsが正しく設定されているか確認
   - `GMAIL_ADDRESS`: Gmailアドレス
   - `GMAIL_APP_PASSWORD`: 16文字のアプリパスワード
2. Actionsのログでエラーを確認（リポジトリのActionsタブ）
3. Googleアカウントで2段階認証が有効になっているか確認
4. アプリパスワードが正しく生成されているか確認
5. 迷惑メールフォルダを確認

### RSSフィードが生成されない場合

1. フィード元のURLが有効か確認
2. インターネット接続を確認
3. Actionsのログでエラーを確認
