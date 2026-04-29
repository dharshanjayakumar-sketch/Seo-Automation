import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import html
import os
import re

# ---------------- CONFIG ---------------- #

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
    "https://techcrunch.com/feed/"
]

EMAIL_SENDER = "dharshan.jayakumar@joytechnologies.com"

EMAIL_RECEIVERS = [
    "dharshanofficial134@gmail.com",
    "dharshan.jayakumar@joytechnologies.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# ---------------- FETCH ---------------- #

def get_article_data(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text, r.text
    except:
        return "", ""

def get_articles():
    articles = []
    for feed in NEWS_FEEDS:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries[:3]:
            text, html_data = get_article_data(entry.link)
            if len(text) > 400:
                articles.append({
                    "title": entry.title,
                    "content": text[:1200],
                    "html": html_data
                })
    return articles

# ---------------- INTELLIGENCE ---------------- #

def clean_summary(text):
    text = re.sub(r"\s+", " ", text)
    sentences = text.split(".")
    return ". ".join([s.strip() for s in sentences if len(s) > 50][:2]) + "."

def detect_signal(text):
    keywords = [
        "expanding", "launch", "funding", "raised",
        "new market", "entered", "growth", "acquisition"
    ]
    return any(k in text.lower() for k in keywords)

def extract_domains(html):
    urls = re.findall(r"https?://[^\s\"']+", html)
    domains = []
    for url in urls:
        d = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        domains.append(d)
    return list(set(domains))

def generate_outreach_idea(text):
    if "expand" in text.lower():
        return "Pitch localized link-building for new region launch"
    elif "funding" in text.lower() or "raised" in text.lower():
        return "Target for brand authority + DR growth campaigns"
    elif "launch" in text.lower():
        return "Pitch product-led SEO + backlinks"
    else:
        return "Explore general SEO partnership opportunity"

# ---------------- MAIN ---------------- #

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found")
    exit()

insights = []
all_domains = []

for article in articles:
    if not detect_signal(article["content"]):
        continue

    summary = clean_summary(article["content"])
    domains = extract_domains(article["html"])
    idea = generate_outreach_idea(article["content"])

    company = article["title"]

    insights.append({
        "company": company,
        "summary": summary,
        "domains": domains[:3],
        "idea": idea
    })

    all_domains.extend(domains)

date = datetime.now().strftime("%A, %B %d, %Y")

# ---------------- EMAIL CONTENT ---------------- #

cards = ""

for item in insights[:5]:
    cards += f"""
    <div style="background:#f3f0ff;padding:14px;margin-bottom:12px;border-radius:10px;">
        <b>{html.escape(item['company'])}</b><br><br>
        {html.escape(item['summary'])}<br><br>
        🔗 Domains: {", ".join(item['domains'])}<br>
        💡 Idea: {item['idea']}
    </div>
    """

html_content = f"""
<div style="font-family:Arial;padding:20px;background:#efe9ff;">

<h2>Hi, this is Dharshan’s Automation Feed 🚀</h2>

<p>Here are today’s SEO + company movement signals you can use for LinkDoctor outreach:</p>

{cards if cards else "<p>No strong outreach signals today</p>"}

<br>

<h3>Why this helps LD outreach:</h3>
<ul>
<li>Identify companies entering new markets</li>
<li>Find fresh domains before competitors</li>
<li>Pitch SEO at the right timing (growth stage)</li>
</ul>

<br>

<p>I’ll be back tomorrow with new signals.</p>

<p>— Dharshan</p>

</div>
"""

# ---------------- EMAIL SEND ---------------- #

print("Sending email...")

msg = MIMEText(html_content, "html")
msg["Subject"] = "LD Outreach Signals"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(EMAIL_SENDER, EMAIL_PASSWORD)

server.sendmail(
    EMAIL_SENDER,
    EMAIL_RECEIVERS,
    msg.as_string()
)

server.quit()

print("✅ Email sent successfully")