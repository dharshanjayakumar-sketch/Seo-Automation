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

EMAIL_SENDER = "dharshan.jayakumar@joytechnologies.com"

EMAIL_RECEIVERS = [
    "sakthi.abirami@joytechnologies.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# ---------------- FETCH ---------------- #

def get_article_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))
    except:
        return ""


def get_articles():
    articles = []

    for feed in NEWS_FEEDS:
        parsed = feedparser.parse(feed)

        for entry in parsed.entries[:3]:
            text = get_article_text(entry.link)

            if len(text) > 300:
                articles.append(text)

    return articles


# ---------------- PROCESS ---------------- #

def generate_summary(text):
    return text[:200] + "..."


# ---------------- MAIN ---------------- #

print("Fetching news...")
articles = get_articles()

geo_updates = []
domains = []

for article in articles:
    if detect_geo_expansion(article):
        geo_updates.append(article[:150])

    domains.extend(extract_domains(article))

domains = list(set(domains))[:10]

# ---------------- EMAIL ---------------- #

date = datetime.now().strftime("%A, %d %B %Y")

html_content = f"""
<h2>SEO News - {date}</h2>

<h3>Updates</h3>
<ul>
{''.join(f"<li>{generate_summary(a)}</li>" for a in articles)}
</ul>

<h3>Geo Expansion</h3>
<ul>
{''.join(f"<li>{g}</li>" for g in geo_updates)}
</ul>

<h3>Outreach Domains</h3>
<ul>
{''.join(f"<li>{d}</li>" for d in domains)}
</ul>
"""

msg = MIMEText(html_content, "html")
msg["Subject"] = "Morning SEO Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

print("Sending email...")

server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(EMAIL_SENDER, EMAIL_PASSWORD)
server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
server.quit()

print("Done ✅")