# RSS Feed to Email

物理学関連のRSSフィード（arXiv、APS）から論文情報を収集し、キーワードでフィルタリングしてメール送信します。

## セットアップ

### 1. Gmailアプリパスワードの生成

1. Googleアカウントで2段階認証を有効化
2. https://myaccount.google.com/apppasswords でアプリパスワードを生成

### 2. GitHub Repository Secretsの設定

リポジトリの **Settings > Secrets and variables > Actions > New repository secret** で以下を設定：

| Secret名 | 説明 |
|---------|------|
| `SENDER_EMAIL` | 送信元のGmailアドレス |
| `RECIPIENT_EMAIL` | 送信先のメールアドレス |
| `GMAIL_APP_PASSWORD` | 送信元アカウントのアプリパスワード |

## 実行スケジュール

- 毎日 5:00 AM UTC (日本時間 14:00)
- 手動実行: ActionsタブのRun workflowボタン

## ローカルテスト

```bash
# 依存関係をインストール
pip install -r requirements.txt

# RSSフィードを生成
python scripts/papers_iefl.py filtered.xml

# メール送信テスト
python scripts/send_rss_email.py \
  --rss-file filtered.xml \
  --to recipient@example.com \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user sender@gmail.com \
  --smtp-password "app-password" \
  --from sender@gmail.com
```
