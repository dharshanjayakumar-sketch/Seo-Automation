from bs4 import BeautifulSoup
from urllib.parse import urlparse

GEO_KEYWORDS = [
    "expands to", "launch in", "rollout in",
    "now available in", "enters", "expansion"
]

COUNTRIES = ["US", "UK", "Canada", "Australia", "Europe"]


def detect_geo_expansion(text):
    text = text.lower()

    for keyword in GEO_KEYWORDS:
        if keyword in text:
            for country in COUNTRIES:
                if country.lower() in text:
                    return True
    return False


def extract_domains(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    links = soup.find_all("a", href=True)

    domains = set()

    for link in links:
        url = link["href"]
        parsed = urlparse(url)

        if parsed.netloc:
            domains.add(parsed.netloc.replace("www.", ""))

    return list(domains)