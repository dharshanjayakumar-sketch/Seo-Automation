import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

from filters import detect_geo_expansion, extract_domains

# ---------------- CONFIG ---------------- #

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
]

EMAIL_SENDER = "dharshanofficial134@gmail.com"

EMAIL_RECEIVERS = [
    "sakthi.abirami@joytechnologies.com",
    "dharshanofficial134@gmail.com"
]

EMAIL_PASSWORD = "abcdefghijklmnop"

# ---------------- FETCH ---------------- #

def get_article_data(url):
    try:
        r = requests.get(url, timeout=10)
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text, html
    except Exception as e:
        print("Error fetching article:", str(e))
        return "", ""


def get_articles():
    articles = []

    for feed in NEWS_FEEDS:
        parsed = feedparser.parse(feed)

        for entry in parsed.entries[:3]:
            text, html = get_article_data(entry.link)

            if len(text) > 300:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "content": text,
                    "html": html
                })

    return articles


# ---------------- PROCESS ---------------- #

def generate_summary(text):
    sentences = text.split(".")
    return ".".join(sentences[:2]) + "."


BAD_DOMAINS = [
    "facebook.com", "twitter.com", "linkedin.com",
    "youtube.com", "google.com"
]

# ---------------- MAIN ---------------- #

print("Fetching news...")
articles = get_articles()

if not articles:
    raise ValueError("No articles fetched")

geo_updates = []
domains = []

for article in articles:
    content = article["content"]

    if detect_geo_expansion(content):
        geo_updates.append(article["title"])

    domains.extend(extract_domains(article["html"]))

# clean domains
domains = [
    d for d in domains
    if not any(bad in d for bad in BAD_DOMAINS)
]

domains = sorted(set(domains))[:15]

# ---------------- EMAIL ---------------- #

date = datetime.now().strftime("%A, %d %B %Y")

html_content = f"""
<h2>SEO News - {date}</h2>

<h3>Updates</h3>
<ul>
{''.join(f"<li><a href='{a['link']}'>{a['title']}</a><br>{generate_summary(a['content'])}</li>" for a in articles)}
</ul>

<h3>Geo Expansion</h3>
<ul>
{''.join(f"<li>{g}</li>" for g in geo_updates) or "<li>No major geo signals</li>"}
</ul>

<h3>Outreach Domains</h3>
<ul>
{''.join(f"<li>{d}</li>" for d in domains) or "<li>No domains found</li>"}
</ul>
"""

msg = MIMEText(html_content, "html")
msg["Subject"] = "Morning SEO Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

print("Sending email...")

# 🔍 DEBUG CHECK
print("EMAIL_PASSWORD value:", EMAIL_PASSWORD)

if EMAIL_PASSWORD is None:
    raise ValueError("❌ EMAIL_PASSWORD not found. Fix GitHub Secrets.")

try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
    server.quit()

    print("✅ Email sent successfully")

except Exception as e:
    print("❌ Email failed:", str(e))
    raise