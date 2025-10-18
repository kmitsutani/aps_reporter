#!/usr/bin/env python3
"""
Send RSS feed entries as email.
Alternative to r2e (rss2email) using standard SMTP.
"""
import argparse
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import os
from loguru import logger

def send_rss_email(
    rss_file: str,
    to_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str = None,
    days_back: int = 1
):
    """
    Parse RSS feed and send new entries via email.

    Args:
        rss_file: Path to RSS file
        to_email: Recipient email address
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username
        smtp_password: SMTP password
        from_email: Sender email (defaults to smtp_user)
        days_back: Only send entries from last N days
    """
    if from_email is None:
        from_email = smtp_user

    # Parse RSS feed
    if not Path(rss_file).exists():
        logger.error(f"RSS file not found: {rss_file}")
        return

    feed = feedparser.parse(rss_file)
    logger.info(f"Parsed RSS feed: {feed.feed.get('title', 'Unknown')} ({len(feed.entries)} entries)")

    # Filter recent entries
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_entries = []

    for entry in feed.entries:
        pub_date_str = entry.get('published', entry.get('updated', ''))
        try:
            # Try to parse the date
            from dateutil import parser as date_parser
            pub_date = date_parser.parse(pub_date_str)
            # Make timezone-naive for comparison
            if pub_date.tzinfo:
                pub_date = pub_date.replace(tzinfo=None)

            if pub_date >= cutoff_date:
                recent_entries.append(entry)
        except Exception as e:
            logger.debug(f"Could not parse date '{pub_date_str}': {e}")
            # Include entry if date parsing fails
            recent_entries.append(entry)

    if not recent_entries:
        logger.info("No recent entries to send")
        return

    logger.info(f"Found {len(recent_entries)} recent entries")

    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"{feed.feed.get('title', 'RSS Feed')} - {len(recent_entries)} new items"
    msg['From'] = from_email
    msg['To'] = to_email

    # Build email body
    text_parts = []
    html_parts = ['<html><body>']

    for i, entry in enumerate(recent_entries, 1):
        title = entry.get('title', 'No title')
        link = entry.get('link', '')
        summary = entry.get('summary', entry.get('description', ''))

        # Text version
        text_parts.append(f"{i}. {title}")
        text_parts.append(f"   {link}")
        text_parts.append(f"   {summary[:200]}...")
        text_parts.append("")

        # HTML version
        html_parts.append(f'<h3><a href="{link}">{title}</a></h3>')
        html_parts.append(f'<p>{summary}</p>')
        html_parts.append('<hr>')

    html_parts.append('</body></html>')

    # Attach both versions
    text_body = '\n'.join(text_parts)
    html_body = '\n'.join(html_parts)

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    # Send email
    try:
        logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send RSS feed as email")
    parser.add_argument("--rss-file", required=True, help="Path to RSS file")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--smtp-host", default=os.getenv('SMTP_HOST', 'smtp.gmail.com'), help="SMTP host")
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv('SMTP_PORT', '587')), help="SMTP port")
    parser.add_argument("--smtp-user", default=os.getenv('SMTP_USER'), help="SMTP username")
    parser.add_argument("--smtp-password", default=os.getenv('SMTP_PASSWORD'), help="SMTP password")
    parser.add_argument("--from", dest='from_email', help="From email address")
    parser.add_argument("--days-back", type=int, default=1, help="Only send entries from last N days")

    args = parser.parse_args()

    if not args.smtp_user or not args.smtp_password:
        logger.error("SMTP credentials required. Set SMTP_USER and SMTP_PASSWORD environment variables or use --smtp-user and --smtp-password")
        exit(1)

    send_rss_email(
        rss_file=args.rss_file,
        to_email=args.to,
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        smtp_user=args.smtp_user,
        smtp_password=args.smtp_password,
        from_email=args.from_email,
        days_back=args.days_back
    )
