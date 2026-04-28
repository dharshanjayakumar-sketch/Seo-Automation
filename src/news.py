import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import html
import os
import re
import time

# ---------------- CONFIG ---------------- #

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
    "https://techcrunch.com/feed/"
]

EMAIL_SENDER = "dharshan.jayakumar@joytechnologies.com"

EMAIL_RECEIVERS = [
    "sakthi.abirami@joytechnologies.com",
    "dharshanofficial134@gmail.com",
    "dharshan.jayakumar@joytechnologies.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

MAX_API_CALLS = 3
api_calls_made = 0

# ---------------- SIMPLE FETCH ---------------- #

def get_article_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))
    except:
        return ""

def get_articles():
    articles = []
    for feed_url in NEWS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:2]:
            text = get_article_text(entry.link)
            if len(text) > 300:
                articles.append(text[:1000])
    return articles

# ---------------- MAIN ---------------- #

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found")
    exit()

print("Articles fetched:", len(articles))

date = datetime.now().strftime("%A, %B %d, %Y")

html_content = f"""
<h2>SEO News - {date}</h2>
<ul>
{''.join(f"<li>{a[:200]}...</li>" for a in articles)}
</ul>
"""

# ---------------- EMAIL ---------------- #

print("Sending email...")

print("EMAIL_PASSWORD exists:", EMAIL_PASSWORD is not None)

if not EMAIL_PASSWORD:
    raise ValueError("EMAIL_PASSWORD missing in GitHub secrets")

msg = MIMEText(html_content, "html")
msg["Subject"] = "Morning SEO Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.ehlo()

    server.login(EMAIL_SENDER, EMAIL_PASSWORD)

    server.sendmail(
        EMAIL_SENDER,
        EMAIL_RECEIVERS,
        msg.as_string()
    )

    server.quit()

    print("✅ Email sent successfully")

except Exception as e:
    print("❌ Email failed:", str(e))
    raise