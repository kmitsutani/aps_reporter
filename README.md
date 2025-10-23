# RSS Feed to Email

物理学関連のRSSフィード（arXiv、APS）から論文情報を収集し、キーワードでフィルタリングしてメール送信します。

## セットアップ

### `config.json` の編集

`config.json`によってどのようなフィードを取得するのか，どのようなスタイルで配信するのかを設定します．

以下に設定例の一例を挙げます．
```json
{
  "feeds":{
    "online":{
      "PRA-ES":"https://feeds.aps.org/rss/prasuggestions.xml",
      "PRD-ES":"https://feeds.aps.org/rss/prdsuggestions.xml",
      "PRL-ES":"https://feeds.aps.org/rss/prlsuggestions.xml",
      "PRXQ":"https://feeds.aps.org/rss/recent/prxquantum.xml"
    },
    "local":
      {"iefl": "python::scripts/filter_iefl.py"}
  },
  "style": {
    "by-entry": [
      "RPA-ES",
      "PRD-ES",
      "PRL-ES",
      "PRXQ"
    ],
    "Summary":[
      "iefl"
    ]
  }
}
```

`feeds`セクションにおいては取得フィードの設定を行います．
`feeds.online` はオンラインにあるRSSファイルのURLを表す辞書になっています
辞書の各キーはそのフィードの名前を表し各値はURLを表します．
`feeds.local`のほうはrss互換のxmlファイルを生成するローカルスクリプトの名前と場所を表す辞書になっています．

`style`セクションは各フィードをどのように配信するかを表しています．
`style.by-entry` に含まれるフィードに関しては entry(item)につきメール一通になるような区切りで通知します．
`style.Summary` に含まれるフィードに関しては一日に一通サマリーを送信します．


### Gmailアプリパスワードの生成

1. Googleアカウントで2段階認証を有効化
2. https://myaccount.google.com/apppasswords でアプリパスワードを生成

### GitHub Repository Secretsの設定

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
