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
    "dharshan.jayakumar@joytechnologies.com",
    "sakthi.abirami@joytechnologies.com",
    "shunmugamoorthy.s@joytechnologies.com",
    "vimal.munusamy@joytechnologies.com",
    "abinaya.velmurugan@joytechnologies.com",
    "rajkumar.rajendran@joytechnologies.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# ---------------- FETCH ---------------- #

def get_article_data(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text = " ".join(paragraphs)

        return text, r.text
    except:
        return "", ""

def get_articles():
    articles = []
    for feed in NEWS_FEEDS:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries[:3]:
            text, html_data = get_article_data(entry.link)
            if len(text) > 300:
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
    seen = set()
    clean = []

    for s in sentences:
        s = s.strip()

        if len(s) < 40:
            continue

        if s.lower() in seen:
            continue

        # remove promo junk
        if "workshop" in s.lower() or "register" in s.lower():
            continue

        seen.add(s.lower())
        clean.append(s)

    return ". ".join(clean[:2]) + "." if clean else text[:150] + "..."

def detect_signal(text):
    keywords = [
        "expanding", "launch", "funding", "raised",
        "new market", "entered", "growth", "acquisition"
    ]
    return any(k in text.lower() for k in keywords)

def extract_domains(html_data):
    urls = re.findall(r"https?://[^\s\"']+", html_data)
    domains = []

    for url in urls:
        d = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        domains.append(d)

    BAD = [
        "facebook.com", "twitter.com", "linkedin.com",
        "google.com", "youtube.com", "x.com",
        "cloudflare.com", "challenges.cloudflare.com"
    ]

    domains = [d for d in domains if not any(b in d for b in BAD)]

    return list(set(domains))

def generate_outreach_idea(text):
    text = text.lower()

    if "expand" in text or "new market" in text:
        return "Pitch localized SEO + country backlinks"
    elif "funding" in text or "raised" in text:
        return "Target for DR growth link-building"
    elif "launch" in text:
        return "Pitch product SEO + PR backlinks"
    elif "acquisition" in text:
        return "Offer backlink consolidation strategy"
    else:
        return "Explore SEO partnership opportunity"

# ---------------- MAIN ---------------- #

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found")
    exit()

insights = []

for article in articles:
    is_signal = detect_signal(article["content"])

    summary = article["title"] + " — " + clean_summary(article["content"])
    domains = extract_domains(article["html"])
    idea = generate_outreach_idea(article["content"])

    insights.append({
        "company": article["title"],
        "summary": summary,
        "domains": domains[:3],
        "idea": idea,
        "priority": "HIGH" if is_signal else "MEDIUM"
    })

# ---------------- EMAIL CONTENT ---------------- #

date = datetime.now().strftime("%A, %B %d, %Y")

cards = ""

for item in insights[:5]:
    color = "#e0f2fe" if item["priority"] == "HIGH" else "#f3f0ff"

    cards += f"""
    <div style="background:{color};padding:14px;margin-bottom:12px;border-radius:10px;">
        <b>{html.escape(item['company'])}</b> ({item['priority']})<br><br>
        {html.escape(item['summary'])}<br><br>
        🔗 Domains: {", ".join(item['domains']) if item['domains'] else "N/A"}<br>
        💡 Idea: {item['idea']}
    </div>
    """

html_content = f"""
<div style="font-family:Arial;padding:20px;background:#efe9ff;">

<h2>Hi, this is Dharshan’s Automation Feed 🚀</h2>

<p>Here are today’s SEO + company movement signals for LinkDoctor outreach:</p>

{cards}

<br>

<h3>Why this helps LD outreach:</h3>
<ul>
<li>Catch companies at growth stage</li>
<li>Find domains early before competitors</li>
<li>Pitch SEO when intent is highest</li>
</ul>

<br>

<p>I’ll be back tomorrow with fresh signals.</p>

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