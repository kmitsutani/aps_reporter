#!/usr/bin/env python3
"""
Main script for processing RSS feeds and sending emails.
Supports two styles:
- by-entry: Send one email per entry
- Summary: Send one summary report per day
"""
import os
import sys
import json
import smtplib
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import feedparser
import pandas as pd
from dateutil import parser as date_parser
from latex2mathml.converter import convert as latex_to_mathml
import re


def convert_latex_to_mathml(text):
    """Convert LaTeX formulas in text to MathML.

    Supports both inline ($...$) and display ($$...$$) formulas.
    """
    def replace_display_math(match):
        latex = match.group(1).strip()
        try:
            mathml = latex_to_mathml(latex)
            return f'<div style="text-align: center; margin: 1em 0;">{mathml}</div>'
        except Exception as e:
            print(f"Warning: Failed to convert display math: {latex[:50]}... Error: {e}")
            return f'<div style="text-align: center; margin: 1em 0;"><code>{latex}</code></div>'

    def replace_inline_math(match):
        latex = match.group(1).strip()
        try:
            mathml = latex_to_mathml(latex)
            return mathml
        except Exception as e:
            print(f"Warning: Failed to convert inline math: {latex[:50]}... Error: {e}")
            return f'<code>{latex}</code>'

    # First process $$...$$ (display math)
    text = re.sub(r'\$\$(.*?)\$\$', replace_display_math, text, flags=re.DOTALL)

    # Then process $...$ (inline math)
    text = re.sub(r'\$(.*?)\$', replace_inline_math, text)

    return text


def fetch_online_feed(url):
    """Fetch an RSS feed from a URL."""
    print(f"  Fetching online feed: {url}")
    return feedparser.parse(url)


def fetch_local_feed(script_path):
    """Generate RSS feed by running a local script."""
    print(f"  Running local script: {script_path}")

    # Remove 'python::' prefix if present
    if script_path.startswith('python::'):
        script_path = script_path[8:]

    # Create temporary file for output
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path, tmp_path],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"    Script output: {result.stdout}")

        # Parse the generated feed
        feed = feedparser.parse(tmp_path)
        return feed
    except subprocess.CalledProcessError as e:
        print(f"    Error running script: {e}")
        print(f"    stderr: {e.stderr}")
        return feedparser.FeedParserDict()
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def filter_recent_entries(entries, days_back=1):
    """Filter entries to only include those from the last N days."""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_entries = []

    for entry in entries:
        pub_date_str = entry.get('published', entry.get('updated', ''))
        try:
            pub_date = date_parser.parse(pub_date_str)
            # Make timezone-naive for comparison
            if pub_date.tzinfo:
                pub_date = pub_date.replace(tzinfo=None)

            if pub_date >= cutoff_date:
                recent_entries.append(entry)
        except Exception as e:
            print(f"    Could not parse date '{pub_date_str}': {e}")
            # Include entry if date parsing fails
            recent_entries.append(entry)

    return recent_entries


def send_by_entry_email(feed_name, entry, smtp_config):
    """Send one email per entry."""
    title = entry.get('title', 'No title')
    link = entry.get('link', '')
    summary = entry.get('summary', entry.get('description', ''))

    # Convert LaTeX to MathML
    summary_with_mathml = convert_latex_to_mathml(summary)

    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{feed_name}] {title}"
    msg['From'] = smtp_config['from_email']
    msg['To'] = smtp_config['to_email']

    # Text version
    text_body = f"{title}\n\n{link}\n\n{summary[:500]}..."

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            background-color: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 15px 0;
            color: #555;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1><a href="{link}" target="_blank">{title}</a></h1>
        <div class="summary">{summary_with_mathml}</div>
        <p><a href="{link}" target="_blank">Read more →</a></p>
    </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Send email
    try:
        with smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port']) as server:
            server.starttls()
            server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
            server.send_message(msg)
        print(f"    Email sent: {title[:50]}...")
    except Exception as e:
        print(f"    Failed to send email: {e}")
        raise


def generate_summary_html(feed_name, entries):
    """Generate HTML summary report for multiple entries."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    css = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .entry {
            margin: 30px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }
        .entry h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        .entry h2 a {
            color: #2c3e50;
            text-decoration: none;
        }
        .entry h2 a:hover {
            color: #3498db;
        }
        .summary {
            background-color: white;
            padding: 15px;
            border-left: 3px solid #95a5a6;
            margin: 15px 0;
            color: #555;
        }
        .meta {
            color: #7f8c8d;
            font-size: 0.9em;
            margin: 10px 0;
        }
        .no-entries {
            text-align: center;
            color: #7f8c8d;
            padding: 40px;
            font-style: italic;
        }
    </style>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{feed_name} - デイリーレポート ({today_str})</title>
    {css}
</head>
<body>
    <div class="container">
        <h1>{feed_name} - デイリーレポート ({today_str})</h1>
        <p>合計 {len(entries)} 件の論文</p>
"""

    if not entries:
        html_content += '<div class="no-entries">本日の新着論文はありませんでした。</div>'
    else:
        for entry in entries:
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))
            pub_date_str = entry.get('published', entry.get('updated', ''))

            # Convert LaTeX to MathML
            summary_with_mathml = convert_latex_to_mathml(summary)

            try:
                pub_date = date_parser.parse(pub_date_str)
                formatted_date = pub_date.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = pub_date_str

            html_content += f'''
        <div class="entry">
            <h2><a href="{link}" target="_blank">{title}</a></h2>
            <div class="meta">公開日: {formatted_date}</div>
            <div class="summary">{summary_with_mathml}</div>
        </div>
'''

    html_content += """
    </div>
</body>
</html>
"""

    return html_content


def send_summary_email(feed_name, entries, smtp_config):
    """Send one summary email for all entries."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Generate HTML report
    html_body = generate_summary_html(feed_name, entries)

    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[{feed_name}] デイリーレポート ({today_str}) - {len(entries)}件"
    msg['From'] = smtp_config['from_email']
    msg['To'] = smtp_config['to_email']

    # Text version
    text_body = f"{feed_name} - デイリーレポート ({today_str})\n\n"
    text_body += f"合計 {len(entries)} 件の論文\n\n"
    for i, entry in enumerate(entries, 1):
        title = entry.get('title', 'No title')
        link = entry.get('link', '')
        text_body += f"{i}. {title}\n   {link}\n\n"

    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Send email
    try:
        with smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port']) as server:
            server.starttls()
            server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
            server.send_message(msg)
        print(f"  Summary email sent for {feed_name} ({len(entries)} entries)")
    except Exception as e:
        print(f"  Failed to send summary email: {e}")
        raise


def main():
    # Load configuration
    config_path = Path(__file__).parent / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # SMTP configuration
    smtp_config = {
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_user': os.getenv('SENDER_EMAIL'),
        'smtp_password': os.getenv('GMAIL_APP_PASSWORD'),
        'from_email': os.getenv('SENDER_EMAIL'),
        'to_email': os.getenv('RECIPIENT_EMAIL'),
    }

    # Validate SMTP configuration
    if not all([smtp_config['smtp_user'], smtp_config['smtp_password'],
                smtp_config['to_email']]):
        print("Error: Required environment variables not set:")
        print("  - SENDER_EMAIL")
        print("  - RECIPIENT_EMAIL")
        print("  - GMAIL_APP_PASSWORD")
        sys.exit(1)

    print(f"Processing feeds...")
    print(f"From: {smtp_config['from_email']}")
    print(f"To: {smtp_config['to_email']}")
    print()

    # Process each feed
    all_feeds = {}

    # Fetch online feeds
    if 'online' in config.get('feeds', {}):
        for feed_name, feed_url in config['feeds']['online'].items():
            print(f"Processing online feed: {feed_name}")
            feed = fetch_online_feed(feed_url)
            all_feeds[feed_name] = feed
            print(f"  Found {len(feed.entries)} entries")

    # Fetch local feeds
    if 'local' in config.get('feeds', {}):
        for feed_name, script_path in config['feeds']['local'].items():
            print(f"Processing local feed: {feed_name}")
            feed = fetch_local_feed(script_path)
            all_feeds[feed_name] = feed
            print(f"  Found {len(feed.entries)} entries")

    print()

    # Process by-entry style feeds
    if 'by-entry' in config.get('style', {}):
        print("Processing by-entry style feeds...")
        for feed_name in config['style']['by-entry']:
            if feed_name not in all_feeds:
                print(f"  Warning: Feed '{feed_name}' not found, skipping")
                continue

            feed = all_feeds[feed_name]
            recent_entries = filter_recent_entries(feed.entries, days_back=1)

            print(f"  {feed_name}: {len(recent_entries)} recent entries")
            for entry in recent_entries:
                send_by_entry_email(feed_name, entry, smtp_config)
        print()

    # Process Summary style feeds
    if 'Summary' in config.get('style', {}):
        print("Processing Summary style feeds...")
        for feed_name in config['style']['Summary']:
            if feed_name not in all_feeds:
                print(f"  Warning: Feed '{feed_name}' not found, skipping")
                continue

            feed = all_feeds[feed_name]
            recent_entries = filter_recent_entries(feed.entries, days_back=1)

            print(f"  {feed_name}: {len(recent_entries)} recent entries")
            if recent_entries:
                send_summary_email(feed_name, recent_entries, smtp_config)
        print()

    print("All feeds processed successfully!")


if __name__ == "__main__":
    main()
