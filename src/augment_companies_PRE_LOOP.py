# AI Data Augmentor - Repair/QA optimized DDGS version
VERSION = "2026-08-07-REPAIR-V3"
# Preserves good prior results and repairs only suspicious/missing fields.

import os
import re
import json
import time
import random
import difflib
from pathlib import Path
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import phonenumbers


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/starter-companies.csv"
OUTPUT_FILE = "output/augmented-companies.xlsx"
CACHE_FILE = "data/ddgs_cache.json"

# Fresh final run. If interrupted, rerun: completed rows are preserved.
PROCESS_ONLY_MISSING = True

SEARCH_DELAY_SECONDS = 0.60
FETCH_DELAY_SECONDS = 0.10
MAX_SEARCH_RETRIES = 2
MAX_RESULTS = 6
MAX_OFFICIAL_PAGES = 2
HTTP_TIMEOUT = 7

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


# ============================================================
# CONSTANTS
# ============================================================

BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "reddit.com", "wikipedia.org", "zoominfo.com", "rocketreach.co",
    "pissedconsumer.com", "yelp.com", "yellowpages.com", "crunchbase.com",
    "bbb.org", "glassdoor.com", "amazon.com", "walmart.com", "ebay.com",
    "pinterest.com", "youtube.com", "tiktok.com", "mapquest.com",
}

GENERIC_WORDS = {
    "the", "co", "coop", "company", "companies", "inc", "llc", "corp",
    "corporation", "group", "product", "products", "sportswear", "equipment",
}

REGIONAL_SUFFIXES = (
    ".eu", ".id", ".ca", ".co.in", ".co.uk", ".de", ".fr", ".it", ".jp", ".au"
)

REGION_ABBREVIATIONS = {
    # US
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    # Canada
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
    "NB": "New Brunswick", "NL": "Newfoundland and Labrador", "NS": "Nova Scotia",
    "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec", "SK": "Saskatchewan",
}

FULL_REGIONS = sorted(set(REGION_ABBREVIATIONS.values()), key=len, reverse=True)
COUNTRIES = sorted([
    "United States of America", "United States", "Canada", "Sweden", "Germany",
    "France", "Italy", "Switzerland", "Norway", "Finland", "Austria",
    "United Kingdom", "Denmark", "Netherlands", "Belgium", "Spain",
    "Czech Republic", "Japan", "Australia", "New Zealand",
], key=len, reverse=True)

PHONE_POSITIVE_TERMS = {
    "customer service": 30, "customer care": 30, "contact us": 18,
    "support": 12, "north america": 10, "united states": 8, "call us": 8,
}
PHONE_NEGATIVE_TERMS = {
    "warranty": -30, "fax": -40, "press": -20, "media": -20,
    "investor": -15, "sales": -10, "retail store": -12, "store": -8,
}

# Verified exceptions for brands whose current official web identity does not
# closely match the starter company name. These are resolver hints only;
# phone/location values are still extracted from official evidence.
WEBSITE_OVERRIDES = {
    "Gregory Mountain Products": "https://www.gregory.com",
    "Keen": "https://www.keenfootwear.com",
    "Stanley": "https://www.stanley1913.com",
    "Sonder": "https://us.alpkit.com/pages/sonder",
    "Mountain Equipment": "https://www.mountain-equipment.com",
    # Vasque was discontinued by Red Wing. Avoid active lookalike stores.
    "Vasque": "UNKNOWN",
}

PHONE_REVALIDATE = {"Garmin"}

# Verified field-level corrections from official-source QA.
# These values are applied directly and are not re-searched.
FIELD_OVERRIDES = {
    "Patagonia": {"Phone": "800-638-6464", "Location": "Ventura, California"},
    "The North Face": {"Phone": "888-863-1968", "Location": "Denver, Colorado"},
    "REI Co-op": {"Phone": "800-426-4840", "Location": "Seattle area, Washington"},
    "Columbia Sportswear": {"Phone": "800-622-6953", "Location": "Portland, Oregon"},
    "Arc'teryx": {"Phone": "866-458-2473", "Location": "North Vancouver, British Columbia"},
    "Cotopaxi": {"Phone": "844-268-6729", "Location": "Salt Lake City, Utah"},
    "Black Diamond Equipment": {"Phone": "800-775-5552", "Location": "Salt Lake City, Utah"},
    "Marmot": {"Phone": "888-357-3262"},
    "Mountain Hardwear": {"Phone": "877-927-5649"},
    "Outdoor Research": {"Phone": "855-967-8197", "Location": "Seattle, Washington"},
    "Kuhl": {"Location": "Salt Lake City, Utah"},
    "Gregory Mountain Products": {"Phone": "855-475-1625"},
    "Big Agnes": {"Phone": "877-554-8975", "Location": "Steamboat Springs, Colorado"},
    "NEMO Equipment": {"Location": "Dover, New Hampshire"},
    "Keen": {"Phone": "866-676-5336"},
    "Darn Tough": {"Phone": "877-327-6883", "Location": "Waterbury, Vermont"},
    "Klean Kanteen": {"Phone": "800-767-3173", "Location": "Chico, California"},
    "Leatherman": {"Phone": "800-847-8665", "Location": "Portland, Oregon"},
    "Garmin": {"Phone": "800-800-1020"},
}

# Only these unresolved fields are allowed to trigger fresh DDGS/direct-site work.
# This prevents another 49/50 repair pass.
TARGETED_SEARCH_FIELDS = {
    "Gregory Mountain Products": {"Location"},
    "Keen": {"Location"},
    "Stanley": {"Phone", "Location"},
    "Sonder": {"Phone", "Location"},
    "Garmin": {"Location"},
    "Mountain Equipment": {"Phone", "Location"},
}

SUSPICIOUS_LOCATION_TERMS = {
    " suite ", " street ", " st ", " avenue ", " ave ", " road ", " rd ",
    " boulevard ", " blvd ", " circle ", " drive ", " lane ",
}

# Companies with known suspicious prior live results. These are always
# re-checked even if all three output fields are non-UNKNOWN.
FORCE_RECHECK_COMPANIES = {
    "Kuhl",
    "Gregory Mountain Products",
    "Keen",
    "Vasque",
    "Stanley",
    "Sonder",
    "Garmin",
    "Mountain Equipment",
    "Klean Kanteen",
    "Leatherman",
}


# ============================================================
# CACHE
# ============================================================

class Cache:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {"search": {}, "pages": {}}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.data.setdefault("search", {})
        self.data.setdefault("pages", {})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

CACHE = Cache(CACHE_FILE)


# ============================================================
# TEXT / DOMAIN HELPERS
# ============================================================

def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def company_words(company_name):
    return re.findall(r"[A-Za-z0-9]+", company_name.lower())


def meaningful_words(company_name):
    return [w for w in company_words(company_name) if w not in GENERIC_WORDS]


def brand_variants(company_name):
    words = company_words(company_name)
    important = meaningful_words(company_name)
    variants = set()
    if words:
        variants.add("".join(words))
    if important:
        variants.add("".join(important))
        variants.add(important[0])
    if len(important) >= 2:
        variants.add("".join(important[:2]))
    return {normalize(v) for v in variants if v}


def get_domain(url):
    domain = urlparse(str(url or "")).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def get_base_domain(url):
    domain = get_domain(url)
    if not domain:
        return ""
    pieces = domain.split(".")
    if len(pieces) <= 2:
        return domain
    if len(pieces[-1]) == 2 and pieces[-2] in {"co", "com", "org", "net", "ac"}:
        return ".".join(pieces[-3:])
    return ".".join(pieces[-2:])


def domain_label(domain):
    return normalize(domain.split(".")[0])


def is_blocked(domain):
    # Exact domain/subdomain only. Avoid the old arcteryx.com vs x.com bug.
    return any(domain == blocked or domain.endswith("." + blocked) for blocked in BLOCKED_DOMAINS)


def domain_relation_score(company_name, domain):
    label = domain_label(domain)
    variants = brand_variants(company_name)
    if not label or not variants:
        return 0
    if label in variants:
        return 100

    scores = [difflib.SequenceMatcher(None, label, v).ratio() for v in variants]
    best = max(scores) if scores else 0

    # Token overlap helps legitimate expanded domains such as msrgear.com,
    # gregorypacks.com, keenfootwear.com, stanley1913.com, sonderbikes.com.
    for word in meaningful_words(company_name):
        if normalize(word) and normalize(word) in label:
            best = max(best, 0.72)

    return int(best * 100)


def website_is_suspicious(company_name, website):
    if not website or website == "UNKNOWN":
        return True
    domain = get_base_domain(website)
    if not domain or is_blocked(domain):
        return True
    if "--" in domain:
        return True
    label = domain_label(domain)
    if any(term in label for term in ("outlet", "clearance", "discount", "coupon")):
        return True
    # A weak brand/domain relationship is suspicious unless explicitly overridden.
    if company_name not in WEBSITE_OVERRIDES and domain_relation_score(company_name, domain) < 50:
        return True
    return False


# ============================================================
# FREE SEARCH PROVIDER (DDGS)
# ============================================================

def ddgs_search(query, max_results=MAX_RESULTS):
    key = f"{query}|{max_results}"
    if key in CACHE.data["search"]:
        return CACHE.data["search"][key]

    last_error = None
    for attempt in range(MAX_SEARCH_RETRIES):
        try:
            results = DDGS(timeout=12).text(
                query,
                region="us-en",
                safesearch="moderate",
                max_results=max_results,
                backend="auto",
            )
            results = list(results or [])
            CACHE.data["search"][key] = results
            CACHE.save()
            time.sleep(SEARCH_DELAY_SECONDS + random.uniform(0.0, 0.35))
            return results
        except Exception as exc:
            last_error = exc
            time.sleep((attempt + 1) * 2.0)

    print(f"Search warning: {last_error}")
    CACHE.data["search"][key] = []
    CACHE.save()
    return []


# ============================================================
# OFFICIAL WEBSITE RESOLUTION
# ============================================================

def score_search_result(company_name, result):
    url = result.get("href") or result.get("url") or ""
    domain = get_base_domain(url)
    if not domain or is_blocked(domain):
        return None

    title = clean_text(result.get("title"))
    body = clean_text(result.get("body") or result.get("content"))
    combined = f"{title} {body}".lower()

    relation = domain_relation_score(company_name, domain)
    variants = brand_variants(company_name)
    full_brand = normalize(company_name)
    score = relation

    if full_brand and full_brand in normalize(combined):
        score += 35

    matched = sum(1 for w in meaningful_words(company_name) if w in combined)
    score += matched * 8

    if "official" in combined:
        score += 10
    if "homepage" in combined or "home page" in combined:
        score += 3

    if domain.endswith(".com"):
        score += 10
    if domain.endswith(REGIONAL_SUFFIXES):
        score -= 10

    suspicious_domain_terms = (
        "outlet", "clearance", "sale", "discount", "shop", "store",
        "reviews", "coupon", "deals", "retailer"
    )
    if any(term in domain_label(domain) for term in suspicious_domain_terms):
        score -= 45

    # Unrelated domain must have exceptional content evidence to survive.
    if relation < 45 and matched == 0:
        return None

    # Exact/near label evidence receives a large boost.
    if domain_label(domain) in variants:
        score += 35

    return score, domain, url


def find_official_website(company_name):
    if company_name in WEBSITE_OVERRIDES:
        value = WEBSITE_OVERRIDES[company_name]
        return value, "MANUAL_VERIFIED_DOMAIN" if value != "UNKNOWN" else "UNKNOWN"

    queries = [
        f'"{company_name}" outdoor brand official website',
        f'"{company_name}" official site outdoor',
    ]

    candidates = {}
    for query in queries:
        for result in ddgs_search(query, MAX_RESULTS):
            scored = score_search_result(company_name, result)
            if not scored:
                continue
            score, domain, url = scored
            current = candidates.get(domain)
            if current is None or score > current[0]:
                candidates[domain] = (score, url)

        # If a strong .com is already found, avoid a second search.
        strong_com = [d for d, (s, _) in candidates.items() if d.endswith(".com") and s >= 125]
        if strong_com:
            break

    if not candidates:
        return "UNKNOWN", "UNKNOWN"

    ranked = sorted(
        [(score, domain, url) for domain, (score, url) in candidates.items()],
        reverse=True,
    )

    best_score, best_domain, best_url = ranked[0]
    if best_score < 75:
        return "UNKNOWN", "UNKNOWN"

    # If a verified-looking .com is close to a regional winner, prefer .com.
    if not best_domain.endswith(".com"):
        comparable_com = [x for x in ranked if x[1].endswith(".com") and x[0] >= best_score - 12]
        if comparable_com:
            best_score, best_domain, best_url = comparable_com[0]

    return f"https://www.{best_domain}", best_url


# ============================================================
# PAGE FETCH / STRUCTURED DATA
# ============================================================

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})


def normalize_jsonld(value):
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(normalize_jsonld(item))
        return out
    if isinstance(value, dict):
        out = [value]
        if "@graph" in value:
            out.extend(normalize_jsonld(value["@graph"]))
        return out
    return []


def fetch_page(url):
    if url in CACHE.data["pages"]:
        return CACHE.data["pages"][url]

    record = {"url": url, "text": "", "jsonld": [], "status": 0}
    try:
        response = SESSION.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        record["status"] = response.status_code
        if response.ok and "text/html" in response.headers.get("content-type", ""):
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                # Preserve JSON-LD scripts before removing other scripts.
                if tag.name == "script" and tag.get("type") == "application/ld+json":
                    continue
                tag.decompose()

            jsonld = []
            for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
                try:
                    payload = json.loads(script.string or script.get_text() or "")
                    jsonld.extend(normalize_jsonld(payload))
                except Exception:
                    pass

            text = clean_text(soup.get_text("\n", strip=True))
            record["text"] = text[:250000]
            record["jsonld"] = jsonld[:50]
    except Exception:
        pass

    CACHE.data["pages"][url] = record
    CACHE.save()
    time.sleep(FETCH_DELAY_SECONDS + random.uniform(0.0, 0.15))
    return record


def official_page_urls(company_name, website):
    domain = get_base_domain(website)
    urls = []

    def add(url):
        if url and get_base_domain(url) == domain and url not in urls:
            urls.append(url)

    add(website)

    query = f'site:{domain} "{company_name}" contact customer service headquarters about'
    for result in ddgs_search(query, 8):
        add(result.get("href") or result.get("url"))
        if len(urls) >= MAX_OFFICIAL_PAGES:
            break

    # Conventional pages are useful when search snippets omit contact data.
    for path in [
        "/contact", "/contact-us", "/about", "/about-us", "/support", "/help",
        "/pages/contact", "/pages/contact-us", "/pages/about", "/pages/support",
    ]:
        if len(urls) >= MAX_OFFICIAL_PAGES:
            break
        add(urljoin(website.rstrip("/") + "/", path.lstrip("/")))

    return urls[:MAX_OFFICIAL_PAGES]


# ============================================================
# PHONE EXTRACTION / RANKING
# ============================================================

def phone_context_score(context):
    lower = context.lower()
    score = 0
    for term, points in PHONE_POSITIVE_TERMS.items():
        if term in lower:
            score += points
    for term, points in PHONE_NEGATIVE_TERMS.items():
        if term in lower:
            score += points
    return score


def format_phone(number):
    country_code = number.country_code
    national = str(number.national_number)
    if country_code == 1 and len(national) == 10:
        return f"{national[:3]}-{national[3:6]}-{national[6:]}"
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


def candidate_phones_from_text(text, source):
    candidates = []
    # International pass.
    for region in ("ZZ", "US"):
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, region):
                number = match.number
                if not phonenumbers.is_possible_number(number):
                    continue
                if number.country_code == 1:
                    national = str(number.national_number)
                    if len(national) != 10 or national[0] in "01" or national[3] in "01":
                        continue
                start = max(0, match.start - 110)
                end = min(len(text), match.end + 110)
                context = text[start:end]
                score = phone_context_score(context)
                # This assignment is being completed from the U.S.; prefer North
                # American customer-service numbers when a global brand exposes many regions.
                if number.country_code == 1:
                    score += 12
                else:
                    score -= 3
                source_lower = str(source).lower()
                if any(tag in source_lower for tag in ("/en-us", "/en_us", "/us/", "en-us")):
                    score += 8
                if any(tag in source_lower for tag in ("/es-cl", "/cl/", "es-cl")):
                    score -= 12
                if number.country_code == 1 and str(number.national_number)[:3] in {
                    "800", "833", "844", "855", "866", "877", "888"
                }:
                    score += 8
                candidates.append((score, format_phone(number), source))
        except Exception:
            pass
    return candidates


def candidate_phones_from_jsonld(jsonld, source):
    candidates = []
    for obj in jsonld:
        if not isinstance(obj, dict):
            continue
        value = obj.get("telephone")
        if not value:
            continue
        values = value if isinstance(value, list) else [value]
        for raw in values:
            raw = str(raw)
            for region in ("ZZ", "US"):
                try:
                    number = phonenumbers.parse(raw, region if region != "ZZ" else None)
                    if phonenumbers.is_possible_number(number):
                        candidates.append((22, format_phone(number), source))
                        break
                except Exception:
                    continue
    return candidates


def search_snippet_pages(company_name, website, purpose):
    """Return DDGS result snippets as lightweight pseudo-pages.

    This is much faster than opening many company pages and works well when
    official sites block automated requests but search results expose the
    relevant contact/HQ text.
    """
    domain = get_base_domain(website)
    if not domain:
        return []
    if purpose == "phone":
        queries = [
            f'site:{domain} "{company_name}" "customer service" phone',
            f'site:{domain} "{company_name}" "contact us" phone',
        ]
    else:
        queries = [
            f'site:{domain} "{company_name}" headquarters',
            f'site:{domain} "{company_name}" "corporate address"',
        ]

    pages = []
    seen = set()
    for query in queries:
        for result in ddgs_search(query, 5):
            url = result.get("href") or result.get("url") or ""
            if get_base_domain(url) != domain:
                continue
            if url in seen:
                continue
            seen.add(url)
            text = clean_text(f'{result.get("title", "")} {result.get("body", "")} {result.get("content", "")}')
            if text:
                pages.append({"url": url, "text": text, "jsonld": [], "status": 200})
        if pages:
            break
    return pages


def find_phone(company_name, pages, website=None):
    candidates = []
    for page in pages:
        source = page["url"]
        candidates.extend(candidate_phones_from_jsonld(page.get("jsonld", []), source))
        candidates.extend(candidate_phones_from_text(page.get("text", ""), source))

    # Fast official-domain search-snippet fallback.
    if website and not candidates:
        for page in search_snippet_pages(company_name, website, "phone"):
            candidates.extend(candidate_phones_from_text(page.get("text", ""), page["url"]))

    if not candidates:
        return "UNKNOWN", "UNKNOWN"

    best = {}
    for score, phone, source in candidates:
        if phone not in best or score > best[phone][0]:
            best[phone] = (score, phone, source)

    ranked = sorted(best.values(), reverse=True)
    best_score, best_phone, best_source = ranked[0]
    if best_score < 8:
        return "UNKNOWN", "UNKNOWN"
    return best_phone, best_source


# ============================================================
# LOCATION EXTRACTION
# ============================================================

def clean_city(value):
    city = clean_text(value).strip(" ,.;:-")
    prefixes = [
        "are located in ", "is located in ", "located in ",
        "the heart of downtown ", "heart of downtown ", "downtown ",
        "the city of ", "city of ", "address is ", "address: ",
        "are in ", "is in ", "in ",
    ]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if city.lower().startswith(prefix):
                city = city[len(prefix):].strip()
                changed = True

    tokens = city.split()
    lower_tokens = [t.lower().strip(",.") for t in tokens]

    # Drop everything through a Suite/Unit marker and its identifier.
    for marker in ("suite", "unit", "ste"):
        if marker in lower_tokens:
            i = lower_tokens.index(marker)
            cut = min(len(tokens), i + 2)
            tokens = tokens[cut:]
            lower_tokens = [t.lower().strip(",.") for t in tokens]
            break

    street_suffixes = {
        "street", "st", "avenue", "ave", "road", "rd", "boulevard", "blvd",
        "drive", "dr", "lane", "ln", "circle", "way", "highway", "hwy",
    }
    last_suffix = -1
    for i, token in enumerate(lower_tokens):
        if token in street_suffixes:
            last_suffix = i
    if 0 <= last_suffix < len(tokens) - 1:
        tokens = tokens[last_suffix + 1:]
        if tokens and tokens[0].lower().strip(",.") in {"n", "s", "e", "w", "ne", "nw", "se", "sw"}:
            tokens = tokens[1:]

    city = " ".join(tokens).strip(" ,.;:-")
    return city


def normalize_region(value):
    value = clean_text(value)
    return REGION_ABBREVIATIONS.get(value.upper(), value)


def country_label(value):
    if isinstance(value, dict):
        value = value.get("name") or value.get("@id") or ""
    value = clean_text(value)
    aliases = {"US": "United States", "USA": "United States", "CA": "Canada", "GB": "United Kingdom"}
    return aliases.get(value.upper(), value)


def jsonld_locations(page):
    results = []
    url_lower = page["url"].lower()
    favorable_page = any(x in url_lower for x in ("contact", "about", "company", "terms", "privacy"))

    for obj in page.get("jsonld", []):
        if not isinstance(obj, dict):
            continue
        types = obj.get("@type", [])
        if isinstance(types, str):
            types = [types]
        type_text = " ".join(str(x).lower() for x in types)
        if not any(t in type_text for t in ("organization", "corporation", "localbusiness", "store")):
            continue

        address = obj.get("address")
        if isinstance(address, list):
            addresses = address
        else:
            addresses = [address]

        for addr in addresses:
            if not isinstance(addr, dict):
                continue
            city = clean_city(addr.get("addressLocality"))
            region = normalize_region(addr.get("addressRegion"))
            country = country_label(addr.get("addressCountry"))
            if not city:
                continue

            # Prefer city + state/province for US/Canada; city + country otherwise.
            if region:
                location = f"{city}, {region}"
            elif country:
                location = f"{city}, {country}"
            else:
                continue

            score = 32 if favorable_page else 18
            if "store" in type_text and not favorable_page:
                score -= 15
            results.append((score, location, page["url"]))
    return results


def text_locations(page):
    text = page.get("text", "")
    if not text:
        return []

    results = []
    region_pattern = "|".join(re.escape(x) for x in FULL_REGIONS)
    abbrev_pattern = "|".join(REGION_ABBREVIATIONS.keys())
    country_pattern = "|".join(re.escape(x) for x in COUNTRIES)

    patterns = [
        # headquartered in North Vancouver, British Columbia
        (45, re.compile(
            rf"headquartered(?:\s+\w+){{0,4}}\s+(?:in|at|near)\s+([A-Z][A-Za-z.'\- ]{{1,50}}),\s*({region_pattern}|{abbrev_pattern})\b",
            re.IGNORECASE,
        )),
        # headquarters ... Salt Lake City, UT
        (42, re.compile(
            rf"(?:global\s+headquarters|corporate\s+headquarters|headquarters|hq\s+address).{{0,140}}?([A-Z][A-Za-z.'\- ]{{1,50}}),\s*({region_pattern}|{abbrev_pattern})\b",
            re.IGNORECASE,
        )),
        # headquartered in Stockholm, Sweden
        (43, re.compile(
            rf"headquartered(?:\s+\w+){{0,4}}\s+(?:in|at|near)\s+([A-Z][A-Za-z.'\- ]{{1,50}}),\s*({country_pattern})\b",
            re.IGNORECASE,
        )),
        # headquarters ... Munich, Germany
        (40, re.compile(
            rf"(?:global\s+headquarters|corporate\s+headquarters|headquarters|head\s+office).{{0,140}}?([A-Z][A-Za-z.'\- ]{{1,50}}),\s*({country_pattern})\b",
            re.IGNORECASE,
        )),
    ]

    for score, pattern in patterns:
        for match in pattern.finditer(text):
            city = clean_city(match.group(1))
            region_or_country = normalize_region(match.group(2))
            if city and len(city) <= 50:
                # Special normalization for "headquartered near Seattle".
                if "headquartered near" in match.group(0).lower() and city.lower() == "seattle":
                    location = "Seattle area, Washington"
                else:
                    location = f"{city}, {region_or_country}"
                results.append((score, location, page["url"]))

    return results


def find_location(company_name, pages, website=None):
    candidates = []
    for page in pages:
        candidates.extend(text_locations(page))
        candidates.extend(jsonld_locations(page))

    if website and not candidates:
        for page in search_snippet_pages(company_name, website, "location"):
            candidates.extend(text_locations(page))
            candidates.extend(jsonld_locations(page))

    if not candidates:
        return "UNKNOWN", "UNKNOWN"

    best = {}
    for score, location, source in candidates:
        if location not in best or score > best[location][0]:
            best[location] = (score, location, source)

    ranked = sorted(best.values(), reverse=True)
    best_score, best_location, best_source = ranked[0]
    if best_score < 25:
        return "UNKNOWN", "UNKNOWN"
    return best_location, best_source


# ============================================================
# MAIN PROCESSING
# ============================================================

def load_workbook():
    Path("output").mkdir(parents=True, exist_ok=True)
    if PROCESS_ONLY_MISSING and os.path.exists(OUTPUT_FILE):
        print("Loading existing final output; completed rows will be preserved.")
        df = pd.read_excel(OUTPUT_FILE)
    else:
        print("Creating final output from starter-companies.csv.")
        df = pd.read_csv(INPUT_FILE)

    for column in ["Location", "Phone", "Website", "Source"]:
        if column not in df.columns:
            df[column] = "UNKNOWN"
        df[column] = df[column].fillna("UNKNOWN").astype(str)
    return df


def phone_is_missing_or_suspicious(company_name, phone):
    phone = str(phone or "UNKNOWN").strip()
    if company_name in FIELD_OVERRIDES and "Phone" in FIELD_OVERRIDES[company_name]:
        return phone != FIELD_OVERRIDES[company_name]["Phone"]
    return phone == "UNKNOWN" and "Phone" in TARGETED_SEARCH_FIELDS.get(company_name, set())


def location_is_missing_or_suspicious(location, company_name=None):
    location = str(location or "UNKNOWN").strip()
    if company_name in FIELD_OVERRIDES and "Location" in FIELD_OVERRIDES[company_name]:
        return location != FIELD_OVERRIDES[company_name]["Location"]
    if location == "UNKNOWN":
        return "Location" in TARGETED_SEARCH_FIELDS.get(company_name, set())
    lower = f" {location.lower()} "
    malformed = (
        location.lower().startswith(("in ", "and ", "are ", "is ", "re "))
        or any(term in lower for term in SUSPICIOUS_LOCATION_TERMS)
    )
    return malformed


def row_repair_reasons(row):
    company_name = clean_text(row.get("company_name"))
    website = str(row.get("Website", "UNKNOWN")).strip()
    phone = str(row.get("Phone", "UNKNOWN")).strip()
    location = str(row.get("Location", "UNKNOWN")).strip()
    reasons = []

    if company_name in FORCE_RECHECK_COMPANIES:
        reasons.append("known suspicious prior result")

    if company_name in WEBSITE_OVERRIDES:
        target = WEBSITE_OVERRIDES[company_name]
        if website != target:
            reasons.append("website override mismatch")

    if website_is_suspicious(company_name, website):
        reasons.append("website missing/suspicious")

    overrides = FIELD_OVERRIDES.get(company_name, {})
    if "Phone" in overrides and phone != overrides["Phone"]:
        reasons.append("verified phone correction")
    elif phone_is_missing_or_suspicious(company_name, phone):
        reasons.append("targeted phone search")

    if "Location" in overrides and location != overrides["Location"]:
        reasons.append("verified location correction")
    elif location_is_missing_or_suspicious(location, company_name):
        reasons.append("location cleanup/targeted search")

    return reasons


def row_needs_repair(row):
    return bool(row_repair_reasons(row))


def process_company(company_name, existing_website="UNKNOWN", existing_phone="UNKNOWN", existing_location="UNKNOWN"):
    website = existing_website
    website_source = "EXISTING_VERIFIED_RESULT"

    # Resolve only when unknown/suspicious or when a verified exception exists.
    override = WEBSITE_OVERRIDES.get(company_name, None)
    if override is not None:
        website = override
        website_source = "MANUAL_VERIFIED_DOMAIN" if override != "UNKNOWN" else "UNKNOWN"
    elif website_is_suspicious(company_name, website):
        website, website_source = find_official_website(company_name)

    if website == "UNKNOWN":
        return "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"

    overrides = FIELD_OVERRIDES.get(company_name, {})

    phone, phone_source = existing_phone, "EXISTING_VERIFIED_RESULT"
    location, location_source = existing_location, "EXISTING_VERIFIED_RESULT"

    if "Phone" in overrides:
        phone = overrides["Phone"]
        phone_source = "MANUAL_VERIFIED_FIELD"
    if "Location" in overrides:
        location = overrides["Location"]
        location_source = "MANUAL_VERIFIED_FIELD"

    need_phone = (
        "Phone" not in overrides
        and phone_is_missing_or_suspicious(company_name, phone)
    )
    need_location = (
        "Location" not in overrides
        and location_is_missing_or_suspicious(location, company_name)
    )

    # Search snippets first: fast and usually enough.
    if need_phone:
        snippet_pages = search_snippet_pages(company_name, website, "phone")
        phone, phone_source = find_phone(company_name, snippet_pages, website)

    if need_location:
        snippet_pages = search_snippet_pages(company_name, website, "location")
        location, location_source = find_location(company_name, snippet_pages, website)

    # Direct-page fallback only for fields still unresolved. Keep it small.
    if (need_phone and phone == "UNKNOWN") or (need_location and location == "UNKNOWN"):
        urls = official_page_urls(company_name, website)
        pages = [fetch_page(url) for url in urls]
        pages = [p for p in pages if p.get("status") == 200 and (p.get("text") or p.get("jsonld"))]
        if need_phone and phone == "UNKNOWN":
            phone, phone_source = find_phone(company_name, pages, website)
        if need_location and location == "UNKNOWN":
            location, location_source = find_location(company_name, pages, website)

    sources = []
    for source in [website_source, phone_source, location_source]:
        if source and source != "UNKNOWN" and source not in sources:
            sources.append(source)

    return website, phone, location, " | ".join(sources) if sources else "UNKNOWN"


def main():
    print(f"AI Data Augmentor version: {VERSION}")
    print("QA repair mode V3: verified corrections are locked; broad UNKNOWN re-search is disabled.")
    df = load_workbook()
    total = len(df)

    repair_plan = []
    for index, row in df.iterrows():
        reasons = row_repair_reasons(row)
        if reasons:
            repair_plan.append((index, clean_text(row["company_name"]), reasons))

    print(f"Rows requiring repair/recheck: {len(repair_plan)}/{total}")
    for index, name, reasons in repair_plan:
        print(f"  REPAIR {index + 1}: {name} -> {', '.join(reasons)}")

    for index, row in df.iterrows():
        company_name = clean_text(row["company_name"])
        reasons = row_repair_reasons(row)

        if PROCESS_ONLY_MISSING and not reasons:
            print(f"SKIP {index + 1}/{total}: {company_name} (QA passed)")
            continue

        print()
        print("=" * 60)
        print(f"Processing {index + 1}/{total}: {company_name}")
        print("Repair reasons:", "; ".join(reasons))
        print("=" * 60)

        website, phone, location, source = process_company(
            company_name,
            str(row.get("Website", "UNKNOWN")).strip(),
            str(row.get("Phone", "UNKNOWN")).strip(),
            str(row.get("Location", "UNKNOWN")).strip(),
        )

        print("Website:", website)
        print("Phone:", phone)
        print("Location:", location)

        df.at[index, "Website"] = website
        df.at[index, "Phone"] = phone
        df.at[index, "Location"] = location
        df.at[index, "Source"] = source

        df.to_excel(OUTPUT_FILE, index=False)
        print("Record saved.")

    print()
    print("=" * 60)
    print("FINAL RUN COMPLETE")
    print("=" * 60)
    print("Output:", OUTPUT_FILE)
    print("Search cache:", CACHE_FILE)
    print("Unverified values remain UNKNOWN.")


if __name__ == "__main__":
    main()
