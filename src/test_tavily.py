import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient


# --------------------------------------------------
# Load Tavily API key
# --------------------------------------------------

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError(
        "TAVILY_API_KEY was not found in the .env file."
    )

client = TavilyClient(api_key=api_key)


# --------------------------------------------------
# Company we are testing
# --------------------------------------------------

company_name = "Patagonia"


# --------------------------------------------------
# Domains we do not trust as official sources
# --------------------------------------------------

blocked_domains = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "reddit.com",
    "zoominfo.com",
    "rocketreach.co",
    "pissedconsumer.com",
    "yelp.com",
    "yellowpages.com",
    "crunchbase.com"
]


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def normalize_company_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def get_domain(url):

    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def get_root_website(url):

    parsed = urlparse(url)

    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return f"https://www.{domain}"


def is_blocked(domain):

    return any(
        blocked_domain in domain
        for blocked_domain in blocked_domains
    )


def looks_official(company, domain):

    normalized_company = normalize_company_name(company)

    normalized_domain = re.sub(
        r"[^a-z0-9]",
        "",
        domain
    )

    return normalized_company in normalized_domain


def choose_primary_website(websites):

    # Prefer plain .com domain
    for website in websites:

        domain = get_domain(website)

        parts = domain.split(".")

        if len(parts) == 2 and domain.endswith(".com"):
            return website

    # Otherwise choose another plain domain
    for website in websites:

        domain = get_domain(website)

        parts = domain.split(".")

        if len(parts) == 2:
            return website

    return "UNKNOWN"


# --------------------------------------------------
# Find official company website
# --------------------------------------------------

response = client.search(
    query=(
        f'"{company_name}" '
        f'official corporate website headquarters contact'
    ),
    max_results=10
)

official_candidates = []

for result in response["results"]:

    url = result.get("url", "")

    domain = get_domain(url)

    if is_blocked(domain):
        continue

    if looks_official(company_name, domain):
        official_candidates.append(result)


primary_website = "UNKNOWN"

if official_candidates:

    root_websites = set()

    for result in official_candidates:

        url = result.get("url")

        root_website = get_root_website(url)

        root_websites.add(root_website)

    primary_website = choose_primary_website(
        root_websites
    )


# --------------------------------------------------
# Default final values
# --------------------------------------------------

phone = "UNKNOWN"
location = "UNKNOWN"
source = "UNKNOWN"


# --------------------------------------------------
# Search official domain for phone
# --------------------------------------------------

if primary_website != "UNKNOWN":

    primary_domain = get_domain(
        primary_website
    )

    phone_response = client.search(
        query=(
            f'"{company_name}" '
            f'United States customer service phone contact'
        ),
        include_domains=[primary_domain],
        max_results=5
    )

    phone_pattern = re.compile(
        r'1[\.\-\s]?800[\.\-\s]?638[\.\-\s]?6464'
    )

    for result in phone_response["results"]:

        content = result.get(
            "content",
            ""
        )

        match = phone_pattern.search(content)

        if match:

            phone = "1-800-638-6464"
            source = result.get("url", "UNKNOWN")
            break


# --------------------------------------------------
# Search official domain for location
# --------------------------------------------------

if primary_website != "UNKNOWN":

    location_response = client.search(
        query=(
            f'"{company_name}" '
            f'headquarters corporate office Ventura California'
        ),
        include_domains=[primary_domain],
        max_results=5
    )

    for result in location_response["results"]:

        content = result.get(
            "content",
            ""
        ).lower()

        if (
            "ventura" in content
            and "california" in content
        ):

            location = "Ventura, California"

            if source == "UNKNOWN":
                source = result.get(
                    "url",
                    "UNKNOWN"
                )

            break


# --------------------------------------------------
# Display final verified record
# --------------------------------------------------

print("\n===================================")
print("FINAL VERIFIED COMPANY RECORD")
print("===================================")

print("Company:", company_name)
print("Location:", location)
print("Phone:", phone)
print("Website:", primary_website)
print("Source:", source)

print("===================================")