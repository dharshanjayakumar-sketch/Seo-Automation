
"""SEO SIGNAL: SEO news and LinkDoctor outreach research newsletter.

Uses public RSS feeds and extracts article text. It does not send cold emails
or use a paid AI API. Any domains found in articles are unverified research leads.
"""

import html
import logging
import os
import re
import smtplib
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup

# ===================== EMAIL SETTINGS =====================
# Keep your existing sender and recipients.
EMAIL_SENDER = "dharshan.jayakumar@joytechnologies.com"

EMAIL_RECEIVERS = [
    "dharshanofficial134@gmail.com",
    "dharshan.jayakumar@joytechnologies.com",
    "sakthi.abirami@joytechnologies.com",
    "shunmugamoorthy.s@joytechnologies.com",
    "vimal.munusamy@joytechnologies.com",
    "abinaya.velmurugan@joytechnologies.com",
    "giri.prasath@joytechnologies.com",
]

# Set this in GitHub repository secrets. Never paste your password here.
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()

# ===================== NEWS SOURCES =====================
NEWS_FEEDS = [
    ("Search Engine Journal", "https://www.searchenginejournal.com/feed/"),
    ("Search Engine Land", "https://searchengineland.com/feed/"),
    (
        "Google Search Central",
        "https://developers.google.com/search/blog/feeds/posts/default?alt=rss",
    ),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Ahrefs Blog", "https://ahrefs.com/blog/feed/"),
]

MAX_PER_FEED = 4
MAX_EMAIL_ARTICLES = 8
REQUEST_TIMEOUT = 15
USER_AGENT = "DharshanSEOAutomation/2.0 (RSS reader)"
TIMEZONE = ZoneInfo("Asia/Kolkata")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "pinterest.com", "reddit.com", "google.com",
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "googletagmanager.com", "google-analytics.com", "cloudflare.com",
    "gravatar.com", "wordpress.org", "wordpress.com", "schema.org", "w3.org",
    "amazonaws.com", "gstatic.com", "googleapis.com", "taboola.com",
    "outbrain.com", "techcrunch.com", "searchenginejournal.com",
    "searchengineland.com", "ahrefs.com",
}

KEYWORD_GROUPS = {
    "Funding": (
        "funding", "raised $", "series a", "series b", "series c",
        "investment round", "venture capital",
    ),
    "Expansion": (
        "expands into", "expansion into", "new market",
        "enters the market", "international expansion",
    ),
    "Acquisition": (
        "acquires", "acquisition", "merger", "has acquired", "to acquire",
    ),
    "Product launch": (
        "launches", "launched", "new product", "product launch",
        "introduces a new",
    ),
    "Leadership / hiring": (
        "appoints ceo", "new ceo", "new cmo", "chief marketing officer",
        "vp of marketing", "head of marketing",
    ),
    "AI search": (
        "ai search", "ai overview", "ai mode", "generative search",
        "llm search", "answer engine",
    ),
    "SEO / search update": (
        "google search", "search ranking", "spam update", "organic traffic",
        "search engine", "seo", "backlink", "link building",
    ),
}


def clean_text(value):
    if not value:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normalize_domain(url):
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        host = (parsed.hostname or "").lower().strip(".")
        if host.startswith("www."):
            host = host[4:]
        if not host or "." not in host:
            return None
        return host
    except (ValueError, AttributeError):
        return None


def blocked_domain(domain):
    if not domain:
        return True
    return any(
        domain == blocked or domain.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def fetch_page(session, url):
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.select(
            "script,style,nav,footer,header,aside,form,noscript,iframe,svg"
        ):
            tag.decompose()

        article = soup.find("article") or soup.find("main") or soup
        paragraphs = [
            p.get_text(" ", strip=True) for p in article.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if len(p) > 45]
        text = re.sub(r"\s+", " ", " ".join(paragraphs)).strip()
        return text[:12000], soup

    except requests.RequestException as exc:
        logging.warning("Article fetch failed (%s): %s", url, exc)
        return "", None


def entry_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            try:
                return time.strftime("%Y-%m-%d", value)
            except (ValueError, TypeError, OverflowError):
                pass
    return ""


def summarize(text, max_sentences=3):
    text = clean_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result, seen = [], set()

    promotional_phrases = (
        "register now", "sign up today", "buy tickets",
        "sponsored content", "subscribe to our newsletter",
        "limited time offer",
    )

    for sentence in sentences:
        sentence = sentence.strip()
        key = sentence.lower()

        if (
            len(sentence) < 45
            or key in seen
            or any(phrase in key for phrase in promotional_phrases)
        ):
            continue

        seen.add(key)
        result.append(sentence)

        if len(result) >= max_sentences:
            break

    if result:
        return " ".join(result)

    return text[:450].rstrip() + ("…" if len(text) > 450 else "")


def classify(title, content):
    combined = (title + " " + content).lower()

    for category, words in KEYWORD_GROUPS.items():
        if any(word in combined for word in words):
            return category

    return "Industry news"


def score(title, content, category):
    text = (title + " " + content).lower()
    high_priority_words = (
        "series a", "series b", "series c", "raised $", "acquisition",
        "acquires", "expansion into", "expands into", "new market",
    )

    if (
        category in ("Funding", "Expansion", "Acquisition")
        or any(word in text for word in high_priority_words)
    ):
        return "HIGH"

    return "MEDIUM"


def outreach_angle(category):
    angles = {
        "Funding": (
            "Check whether growth plans include organic acquisition. "
            "If relevant, explore authority-building editorial links."
        ),
        "Expansion": (
            "Verify target geographies and localized pages. "
            "Assess whether relevant regional editorial links could help."
        ),
        "Acquisition": (
            "Verify the companies and domains involved. "
            "Investigate brand consolidation and organic visibility needs."
        ),
        "Product launch": (
            "Review the product landing page and search demand. "
            "Consider relevant editorial coverage and digital PR."
        ),
        "Leadership / hiring": (
            "Check whether the new leader owns marketing or growth. "
            "Tailor an SEO question to the company's priorities."
        ),
        "AI search": (
            "Assess how the change affects discovery. Focus on useful content, "
            "credible mentions and earned editorial citations—not guaranteed rankings."
        ),
        "SEO / search update": (
            "Use the specific update as a conversation starter about "
            "organic visibility and authoritative, relevant links."
        ),
        "Industry news": (
            "Research the company and confirm a real SEO need before outreach."
        ),
    }
    return angles.get(category, angles["Industry news"])


def extract_external_domains(soup, article_url):
    """Find a few external domains; these are not confirmed prospects."""
    if soup is None:
        return []

    article_domain = normalize_domain(article_url)
    found = set()

    for link in soup.find_all("a", href=True):
        domain = normalize_domain(link["href"])

        if not domain or domain == article_domain or blocked_domain(domain):
            continue

        if domain.startswith(("cdn.", "img.", "static.", "pixel.", "ads.")):
            continue

        found.add(domain)

    return sorted(found)[:3]


def collect_articles():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results = []
    seen_urls = set()
    seen_titles = set()

    try:
        for publisher, feed_url in NEWS_FEEDS:
            logging.info("Reading %s", publisher)

            try:
                response = session.get(feed_url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
            except requests.RequestException as exc:
                logging.warning("RSS feed failed (%s): %s", publisher, exc)
                continue

            if not parsed.entries:
                logging.warning("No entries found for %s", publisher)
                continue

            count = 0

            for entry in parsed.entries:
                if count >= MAX_PER_FEED:
                    break

                title = clean_text(entry.get("title", ""))
                url = entry.get("link", "").strip()

                if not title or not url:
                    continue

                canonical = url.split("#", 1)[0].rstrip("/")
                title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

                if canonical in seen_urls or title_key in seen_titles:
                    continue

                feed_content = clean_text(entry.get("summary", ""))

                if entry.get("content"):
                    feed_content = (
                        clean_text(entry.content[0].get("value", ""))
                        or feed_content
                    )

                page_text, soup = fetch_page(session, url)
                content = page_text if len(page_text) >= 150 else feed_content

                if len(content) < 80:
                    logging.info("Skipping article with insufficient text: %s", title)
                    continue

                seen_urls.add(canonical)
                seen_titles.add(title_key)

                category = classify(title, content)

                results.append({
                    "title": title,
                    "url": url,
                    "publisher": publisher,
                    "date": entry_date(entry),
                    "content": content[:12000],
                    "summary": summarize(content),
                    "category": category,
                    "priority": score(title, content, category),
                    "domains": extract_external_domains(soup, url),
                    "angle": outreach_angle(category),
                })

                count += 1

    finally:
        session.close()

    # Prefer recent articles, then high-priority research items.
    results.sort(key=lambda item: item["date"] or "0000-00-00", reverse=True)
    results.sort(key=lambda item: item["priority"] != "HIGH")

    logging.info("Collected %d unique articles", len(results))
    return results[:MAX_EMAIL_ARTICLES]


def e(value):
    return html.escape(str(value or ""), quote=True)


def render_card(item):
    accent = "#22d3ee" if item["priority"] == "HIGH" else "#60a5fa"
    domains = (
        ", ".join(item["domains"])
        if item["domains"]
        else "No relevant external domains found in the article body."
    )
    date_text = f" · {e(item['date'])}" if item["date"] else ""

    return f"""
    <article style="background:#0c1d3d;border:1px solid #183e72;
      border-left:4px solid {accent};border-radius:12px;padding:20px;margin:16px 0;">
      <div style="font-size:12px;letter-spacing:.5px;color:{accent};font-weight:bold;">
        {e(item['category']).upper()} · {e(item['priority'])} ·
        {e(item['publisher'])}{date_text}
      </div>
      <h2 style="font-size:20px;line-height:1.35;margin:10px 0 12px;color:#f8fafc;">
        <a href="{e(item['url'])}" style="color:#f8fafc;text-decoration:none;">
          {e(item['title'])}
        </a>
      </h2>
      <p style="color:#dbeafe;line-height:1.65;margin:0 0 14px;">
        {e(item['summary'])}
      </p>
      <p style="color:#cbd5e1;line-height:1.55;margin:0 0 10px;">
        <strong style="color:#67e8f9;">Domains to verify:</strong> {e(domains)}
      </p>
      <p style="color:#cbd5e1;line-height:1.55;margin:0;">
        <strong style="color:#67e8f9;">LinkDoctor angle:</strong> {e(item['angle'])}
      </p>
      <p style="margin:14px 0 0;">
        <a href="{e(item['url'])}" style="color:#67e8f9;text-decoration:underline;">
          Read original source ↗
        </a>
      </p>
    </article>
    """


def build_email(articles):
    today = datetime.now(TIMEZONE).strftime("%A, %d %B %Y")

    if not articles:
        raise RuntimeError("No articles were collected; no email will be sent.")

    cards = "".join(render_card(item) for item in articles)
    high_count = sum(item["priority"] == "HIGH" for item in articles)

    return f"""<!doctype html>
<html>
<body style="margin:0;background:#061735;color:#eaf2ff;
font-family:Arial,Helvetica,sans-serif;padding:22px;">
<div style="max-width:900px;margin:0 auto;background:#071b40;
border:1px solid #123c79;border-radius:18px;overflow:hidden;">

<header style="padding:34px 28px 28px;
background:linear-gradient(135deg,#073f87,#071b40);">
<div style="font-size:12px;letter-spacing:3px;color:#67e8f9;font-weight:bold;">
DHARSHAN'S AUTOMATION FEED · {e(today.upper())}
</div>
<h1 style="font-size:42px;line-height:1.1;margin:20px 0 12px;color:#ffffff;">
SEO <span style="color:#22d3ee;">SIGNAL</span>
</h1>
<p style="font-size:18px;color:#dbeafe;margin:0;line-height:1.5;">
Your search intelligence brief for LinkDoctor outreach.
</p>
<div style="margin-top:24px;color:#67e8f9;font-size:12px;letter-spacing:1px;line-height:2;">
ALGORITHM UPDATES | AI SEARCH | LINK BUILDING | ACTIONABLE INSIGHTS
</div>
</header>

<section style="padding:0 28px 10px;">
<div style="background:#102c56;padding:14px 16px;border-radius:9px;margin:16px 0;">
<span style="color:#93c5fd;">ARTICLES:</span>
<strong style="font-size:22px;color:#fff;">{len(articles)}</strong>
&nbsp;&nbsp; | &nbsp;&nbsp;
<span style="color:#67e8f9;">HIGH PRIORITY:</span>
<strong style="font-size:22px;color:#fff;">{high_count}</strong>
</div>

<p style="color:#dbeafe;line-height:1.6;">
Today's selected SEO, AI-search and company-movement stories.
Summaries are extracted from publisher text; open the source before using a claim.
</p>

{cards}

<section style="background:#0a274c;border:1px solid #155e75;
border-radius:12px;padding:20px;margin:22px 0;">
<h2 style="color:#67e8f9;font-size:20px;margin:0 0 12px;">
Cold Email &amp; Deliverability Watch
</h2>
<p style="color:#dbeafe;line-height:1.65;">
Check SPF, DKIM and DMARC authentication for your sending domain.
Keep prospect lists relevant and accurate, honor opt-outs, and monitor bounces
and spam complaints. News alone does not prove a company is ready to buy.
</p>
<a href="https://support.google.com/mail/answer/81126" style="color:#67e8f9;">
Google's official email sender guidelines ↗
</a>
</section>

<h2 style="font-size:20px;color:#fff;">Why this helps LinkDoctor</h2>
<ul style="color:#dbeafe;line-height:1.8;padding-left:22px;">
<li>Spot developments that may create a timely SEO conversation.</li>
<li>Verify claims by opening the original source.</li>
<li>Research official domains instead of assuming every linked domain is a prospect.</li>
<li>Prioritize relevance and credible editorial links over generic promises.</li>
</ul>

<p style="color:#94a3b8;font-size:12px;line-height:1.6;">
Priority is a keyword-based research hint, not a verified buying-intent score.
Mentioned domains are unverified research leads. This automation sends an internal
newsletter; it does not send cold emails.
</p>
<p style="color:#dbeafe;margin-top:26px;">
See you on the next scheduled weekday.<br><strong style="color:#fff;">— Dharshan</strong>
</p>
</section>

<footer style="padding:18px 28px;background:#05132c;border-top:1px solid #123c79;
color:#64748b;font-size:11px;">
SEO SIGNAL · Automated with public RSS feeds · Verify sources before outreach.
</footer>
</div>
</body>
</html>"""


def send_email(html_content):
    if not EMAIL_PASSWORD:
        raise RuntimeError(
            "EMAIL_PASSWORD is missing from GitHub Actions repository secrets."
        )

    now = datetime.now(TIMEZONE).strftime("%d %b %Y")
    message = MIMEMultipart("alternative")
    message["Subject"] = f"SEO SIGNAL | LinkDoctor Outreach Brief | {now}"
    message["From"] = EMAIL_SENDER
    message["To"] = ", ".join(EMAIL_RECEIVERS)

    message.attach(MIMEText(
        "Your email client needs HTML support to display the SEO SIGNAL newsletter.",
        "plain",
        "utf-8",
    ))
    message.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, message.as_string())

    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "Gmail authentication failed. Check EMAIL_PASSWORD and use the "
            "correct Gmail App Password if your account requires one."
        ) from exc

    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(f"Email delivery failed: {exc}") from exc


def main():
    logging.info("Starting SEO SIGNAL newsletter")
    articles = collect_articles()

    if not articles:
        raise RuntimeError(
            "No usable stories were found. Check the GitHub Actions logs and RSS feeds."
        )

    logging.info("Preparing newsletter with %d stories", len(articles))
    send_email(build_email(articles))
    logging.info("Newsletter sent successfully to %d recipients", len(EMAIL_RECEIVERS))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("SEO SIGNAL workflow failed")
        sys.exit(1)
