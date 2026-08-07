import os
import re
import difflib
from urllib.parse import urlparse

import pandas as pd
from dotenv import load_dotenv
from tavily import TavilyClient


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/starter-companies.csv"
OUTPUT_FILE = "output/augmented-companies-test.xlsx"

# Keep this as "unresolved" for the next live run.
# Change to "all" only after the limited run looks good.
PROCESS_MODE = "unresolved"

UNRESOLVED_COMPANIES = [
    "Arc'teryx",
    "Cotopaxi",
    "Black Diamond Equipment",
    "Marmot",
    "Mountain Hardwear",
    "Outdoor Research",
]

MAX_API_CALLS = 30 if PROCESS_MODE == "unresolved" else 220


# ============================================================
# LOAD API KEY
# ============================================================

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError("TAVILY_API_KEY was not found in the .env file.")

client = TavilyClient(api_key=api_key)

API_CALL_COUNT = 0


def tavily_search(**kwargs):
    """Single wrapper so the script cannot accidentally run away with API calls."""
    global API_CALL_COUNT

    if API_CALL_COUNT >= MAX_API_CALLS:
        print("WARNING: Local API call safety limit reached.")
        return {"results": []}

    API_CALL_COUNT += 1

    try:
        return client.search(**kwargs)
    except Exception as exc:
        print(f"Search error: {exc}")
        return {"results": []}


# ============================================================
# CONSTANTS
# ============================================================

BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "wikipedia.org",
    "zoominfo.com",
    "rocketreach.co",
    "pissedconsumer.com",
    "yelp.com",
    "yellowpages.com",
    "crunchbase.com",
    "bbb.org",
    "glassdoor.com",
    "amazon.com",
    "walmart.com",
    "ebay.com",
}

REGIONAL_SUFFIXES = (
    ".eu",
    ".id",
    ".ca",
    ".co.in",
    ".co.uk",
    ".de",
    ".fr",
    ".it",
    ".jp",
    ".au",
)

GENERIC_WORDS = {
    "the",
    "co",
    "coop",
    "company",
    "companies",
    "inc",
    "llc",
    "corp",
    "corporation",
    "group",
    "product",
    "products",
    "sportswear",
    "equipment",
    "packs",
    "footwear",
}

REGION_ABBREVIATIONS = {
    # United States
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
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",

    # Canada
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
    "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia", "ON": "Ontario", "PE": "Prince Edward Island",
    "QC": "Quebec", "SK": "Saskatchewan",
}

FULL_REGIONS = sorted(set(REGION_ABBREVIATIONS.values()), key=len, reverse=True)

COUNTRIES = sorted([
    "United States",
    "United States of America",
    "Canada",
    "Sweden",
    "Germany",
    "France",
    "Italy",
    "Switzerland",
    "Norway",
    "Finland",
    "Austria",
    "United Kingdom",
    "Denmark",
    "Netherlands",
    "Belgium",
    "Spain",
    "Czech Republic",
    "Japan",
    "Australia",
    "New Zealand",
], key=len, reverse=True)


# ============================================================
# TEXT / BRAND HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize(value):
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def company_words(company_name):
    return re.findall(r"[A-Za-z0-9]+", company_name.lower())


def meaningful_words(company_name):
    return [
        word
        for word in company_words(company_name)
        if word not in GENERIC_WORDS
    ]


def brand_variants(company_name):
    all_words = company_words(company_name)
    important = meaningful_words(company_name)

    variants = set()

    if all_words:
        variants.add("".join(all_words))

    if important:
        variants.add("".join(important))
        variants.add(important[0])

    if len(important) >= 2:
        variants.add("".join(important[:2]))

    return {normalize(value) for value in variants if value}


# ============================================================
# DOMAIN HELPERS
# ============================================================

def get_domain(url):
    if not url:
        return ""

    domain = urlparse(url).netloc.lower()

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

    # Handles domains such as company.co.uk or company.co.in
    if (
        len(pieces[-1]) == 2
        and pieces[-2] in {"co", "com", "org", "net", "ac"}
    ):
        return ".".join(pieces[-3:])

    return ".".join(pieces[-2:])


def domain_label(domain):
    return normalize(domain.split(".")[0])


def root_website(domain):
    return f"https://www.{domain}"


def is_blocked(domain):
    """
    Block exact third-party domains or their subdomains only.

    Do NOT use substring matching here:
    "x.com" must not accidentally block "arcteryx.com".
    """
    domain = domain.lower().strip(".")

    return any(
        domain == blocked
        or domain.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def is_regional(domain):
    return any(domain.endswith(suffix) for suffix in REGIONAL_SUFFIXES)


def domain_relation_score(company_name, domain):
    """
    Domain/company relationship.

    The threshold is intentionally moderate because legitimate domains include:
      MSR -> msrgear.com
      Stanley -> stanley1913.com
      Keen -> keenfootwear.com
      Gregory Mountain Products -> gregorypacks.com
    """
    label = domain_label(domain)
    variants = brand_variants(company_name)

    if not variants:
        return 0

    if label in variants:
        return 100

    similarities = [
        difflib.SequenceMatcher(None, label, variant).ratio()
        for variant in variants
    ]

    return int(max(similarities) * 100)


def generate_dot_com_candidates(company_name):
    """Generate likely primary .com domains without using a search credit."""
    return sorted({
        f"{variant}.com"
        for variant in brand_variants(company_name)
    })


# ============================================================
# WEBSITE EVIDENCE SCORING
# ============================================================

def website_result_evidence(company_name, title, content):
    combined = f"{title} {content}"
    lower = combined.lower()

    normalized_company = normalize(company_name)
    normalized_title = normalize(title)
    normalized_content = normalize(content)

    score = 0

    if normalized_company and normalized_company in normalized_title:
        score += 20

    if normalized_company and normalized_company in normalized_content:
        score += 12

    for word in meaningful_words(company_name):
        if word.lower() in lower:
            score += 2

    official_terms = [
        "customer service",
        "customer care",
        "contact us",
        "about us",
        "privacy",
        "terms",
        "careers",
        "headquarters",
    ]

    official_signal_count = sum(
        1 for term in official_terms if term in lower
    )

    score += min(official_signal_count, 2) * 8

    third_party_terms = [
        "review",
        "magazine",
        "news article",
        "retailer",
        "dealer",
    ]

    score -= sum(
        8 for term in third_party_terms if term in lower
    )

    return score, official_signal_count > 0


def select_verified_domain(company_name, results, allowed_domains=None):
    """
    Select the strongest first-party domain.

    A moderate domain-name match must also have first-party page signals.
    This blocks unrelated retailers while still allowing msrgear.com,
    stanley1913.com, gregorypacks.com, etc.
    """
    best_by_domain = {}

    for result in results:
        url = clean_text(result.get("url", ""))
        domain = get_base_domain(url)

        if not domain or is_blocked(domain):
            continue

        if allowed_domains is not None and domain not in allowed_domains:
            continue

        relation = domain_relation_score(company_name, domain)

        if relation < 45:
            continue

        title = str(result.get("title", ""))
        content = str(result.get("content", ""))

        evidence, has_official_signal = website_result_evidence(
            company_name,
            title,
            content,
        )

        if evidence < 25:
            continue

        # Moderate relation requires explicit first-party context.
        if relation < 90 and not has_official_signal:
            continue

        score = (
            evidence
            + relation * 0.35
            + (15 if domain.endswith(".com") else 0)
            - (20 if is_regional(domain) else 0)
        )

        candidate = (
            score,
            relation,
            evidence,
            -len(domain),
            domain,
            url,
        )

        existing = best_by_domain.get(domain)

        if existing is None or candidate > existing:
            best_by_domain[domain] = candidate

    if not best_by_domain:
        return "UNKNOWN", "UNKNOWN"

    winner = max(best_by_domain.values())

    return root_website(winner[4]), winner[5]


# ============================================================
# FIND OFFICIAL WEBSITE
# ============================================================

def find_official_website(company_name):
    """
    Stage 1: verify generated .com candidates in ONE Tavily call.
    Stage 2: only if that fails, perform discovery + one grouped verification call.

    This prevents regional sites from beating a valid .com and reduces quota use.
    """
    generated_domains = generate_dot_com_candidates(company_name)

    # ---------- Stage 1: generated primary .com candidates ----------
    if generated_domains:
        response = tavily_search(
            query=(
                f'"{company_name}" official company '
                f'customer service contact about'
            ),
            include_domains=generated_domains,
            max_results=8,
        )

        website, source = select_verified_domain(
            company_name,
            response.get("results", []),
            allowed_domains=set(generated_domains),
        )

        if website != "UNKNOWN":
            return website, source

    # ---------- Stage 2A: discover candidate domains ----------
    discovery = tavily_search(
        query=f'"{company_name}" official website company',
        max_results=8,
    )

    discovered = set()

    for result in discovery.get("results", []):
        domain = get_base_domain(
            clean_text(result.get("url", ""))
        )

        if not domain or is_blocked(domain):
            continue

        relation = domain_relation_score(company_name, domain)

        if relation >= 45:
            discovered.add(domain)

    if not discovered:
        return "UNKNOWN", "UNKNOWN"

    # Prefer strong relationship and non-regional domains for verification.
    top_domains = sorted(
        discovered,
        key=lambda domain: (
            domain_relation_score(company_name, domain),
            0 if is_regional(domain) else 1,
            1 if domain.endswith(".com") else 0,
        ),
        reverse=True,
    )[:4]

    # ---------- Stage 2B: grouped verification ----------
    verification = tavily_search(
        query=(
            f'"{company_name}" official company '
            f'customer service contact about'
        ),
        include_domains=top_domains,
        max_results=10,
    )

    return select_verified_domain(
        company_name,
        verification.get("results", []),
        allowed_domains=set(top_domains),
    )


# ============================================================
# PHONE EXTRACTION / RANKING
# ============================================================

NANP_PHONE_PATTERN = re.compile(
    r"""
    (?<!\d)
    (?:\+?1[\s\.\-]?)?
    \(?
    (\d{3})
    \)?
    [\s\.\-]
    (\d{3})
    [\s\.\-]
    (\d{4})
    (?!\d)
    """,
    re.VERBOSE,
)

INTERNATIONAL_PHONE_PATTERN = re.compile(
    r"""
    (?<!\d)
    (
        \+
        \d{1,3}
        (?:
            [\s\.\-\(\)]*
            \d
        ){6,14}
    )
    (?!\d)
    """,
    re.VERBOSE,
)


def valid_nanp_phone(area, prefix):
    """
    Reject invalid NANP values such as the bad Patagonia 045-435-6100 result.
    Area code and exchange cannot start with 0 or 1.
    """
    return (
        bool(area)
        and bool(prefix)
        and area[0] in "23456789"
        and prefix[0] in "23456789"
    )


def sentence_context(text, start, end):
    """
    Score a phone using its own sentence rather than a large text window.
    This prevents a Warranty label from contaminating Customer Care.
    """
    left = max(
        text.rfind(".", 0, start),
        text.rfind("\n", 0, start),
        text.rfind(";", 0, start),
    )

    right_candidates = [
        value
        for value in (
            text.find(".", end),
            text.find("\n", end),
            text.find(";", end),
        )
        if value != -1
    ]

    right = min(right_candidates) if right_candidates else len(text)

    return text[left + 1:right].strip().lower()


def score_phone_context(context, toll_free=False):
    score = 0

    positive_terms = {
        "customer service": 25,
        "customer care": 25,
        "contact us": 12,
        "support": 10,
        "north america": 10,
        "united states": 8,
        "call": 4,
    }

    negative_terms = {
        "warranty": -25,
        "fax": -30,
        "retail": -12,
        "store": -10,
        "sales": -10,
        "media": -15,
        "press": -15,
    }

    for term, points in positive_terms.items():
        if term in context:
            score += points

    for term, points in negative_terms.items():
        if term in context:
            score += points

    if toll_free:
        score += 10

    return score


def extract_ranked_phones(text, source):
    candidates = []

    # North American numbers
    for match in NANP_PHONE_PATTERN.finditer(text):
        area, prefix, line = match.groups()

        if not valid_nanp_phone(area, prefix):
            continue

        phone = f"{area}-{prefix}-{line}"
        context = sentence_context(text, match.start(), match.end())

        score = score_phone_context(
            context,
            toll_free=area in {"800", "833", "844", "855", "866", "877", "888"},
        )

        candidates.append((score, phone, source, context))

    # Explicit +country-code international numbers
    for match in INTERNATIONAL_PHONE_PATTERN.finditer(text):
        raw_phone = clean_text(match.group(1))

        # NANP numbers are already handled more carefully above.
        digits = re.sub(r"\D", "", raw_phone)
        if digits.startswith("1") and len(digits) == 11:
            continue

        context = sentence_context(text, match.start(), match.end())
        score = score_phone_context(context, toll_free=False)

        candidates.append((score, raw_phone, source, context))

    return candidates


def find_phone(company_name, website):
    if website == "UNKNOWN":
        return "UNKNOWN", "UNKNOWN"

    domain = get_base_domain(website)

    response = tavily_search(
        query=(
            f'"{company_name}" customer service customer care '
            f'contact phone North America'
        ),
        include_domains=[domain],
        max_results=6,
    )

    all_candidates = []

    for result in response.get("results", []):
        url = clean_text(result.get("url", ""))
        title = str(result.get("title", ""))
        content = str(result.get("content", ""))

        text = title + "\n" + content

        all_candidates.extend(
            extract_ranked_phones(text, url)
        )

    if not all_candidates:
        return "UNKNOWN", "UNKNOWN"

    # Keep the strongest evidence for each distinct phone.
    best_by_phone = {}

    for candidate in all_candidates:
        score, phone, source, context = candidate

        if phone not in best_by_phone or score > best_by_phone[phone][0]:
            best_by_phone[phone] = candidate

    ranked = sorted(
        best_by_phone.values(),
        key=lambda item: item[0],
        reverse=True,
    )

    best_score, best_phone, best_source, _ = ranked[0]

    # Do not accept a number without useful customer-contact evidence.
    if best_score < 12:
        return "UNKNOWN", "UNKNOWN"

    return best_phone, best_source


# ============================================================
# LOCATION EXTRACTION
# ============================================================

def clean_city_candidate(city):
    city = clean_text(city).strip(" ,.;:-")

    prose_prefixes = [
        "are located in ",
        "is located in ",
        "located in ",
        "the heart of downtown ",
        "heart of downtown ",
        "downtown ",
        "the city of ",
        "city of ",
    ]

    changed = True

    while changed:
        changed = False

        for prefix in prose_prefixes:
            if city.lower().startswith(prefix):
                city = city[len(prefix):].strip()
                changed = True

    tokens = city.split()

    street_suffixes = {
        "street", "st", "st.",
        "avenue", "ave", "ave.",
        "road", "rd", "rd.",
        "boulevard", "blvd", "blvd.",
        "drive", "dr", "dr.",
        "lane", "ln", "ln.",
        "way",
        "highway", "hwy", "hwy.",
    }

    last_street_suffix = -1

    for index, token in enumerate(tokens):
        if token.lower().strip(",") in street_suffixes:
            last_street_suffix = index

    if 0 <= last_street_suffix < len(tokens) - 1:
        tokens = tokens[last_street_suffix + 1:]

        if (
            tokens
            and tokens[0].lower() in {
                "north", "south", "east", "west",
                "n", "s", "e", "w",
            }
            and len(tokens) > 1
        ):
            tokens = tokens[1:]

    # Address pattern such as "3900 South Salt Lake City"
    # can leave "South Salt Lake City" after the street number is removed.
    if (
        len(tokens) >= 4
        and tokens[0].lower() in {"north", "south", "east", "west"}
        and tokens[-1].lower() == "city"
    ):
        tokens = tokens[1:]

    return " ".join(tokens)


def reject_bad_location_context(text):
    lower = text.lower()

    bad_terms = [
        "distribution center",
        "distribution centre",
        "warehouse",
        "retail store",
        "store location",
        "factory",
        "manufacturing facility",
    ]

    return any(term in lower for term in bad_terms)


def extract_location(text, allow_corporate=False):
    if not text:
        return "UNKNOWN"

    if reject_bad_location_context(text):
        # We still continue if explicit HQ wording is present.
        lower = text.lower()
        if "headquarter" not in lower and "hq address" not in lower:
            return "UNKNOWN"

    text = clean_text(text)

    region_pattern = "|".join(
        re.escape(region)
        for region in FULL_REGIONS
    )

    abbreviation_pattern = "|".join(
        REGION_ABBREVIATIONS.keys()
    )

    country_pattern = "|".join(
        re.escape(country)
        for country in COUNTRIES
    )

    # --------------------------------------------------------
    # Explicit: headquartered in City, State/Province
    # --------------------------------------------------------

    explicit_region = re.compile(
        rf"""
        headquartered
        (?:\s+\w+){{0,4}}
        \s+
        (in|at|near)
        \s+
        ([A-Z][A-Za-z\.\'\- ]{{1,50}})
        ,\s*
        (
            {region_pattern}
            |
            {abbreviation_pattern}
        )
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    match = explicit_region.search(text)

    if match:
        relation = match.group(1).lower()
        city = clean_city_candidate(match.group(2))
        raw_region = match.group(3)

        region = REGION_ABBREVIATIONS.get(
            raw_region.upper(),
            raw_region,
        )

        if relation == "near" and city.lower() == "seattle":
            return "Seattle area, Washington"

        return f"{city}, {region}"

    # --------------------------------------------------------
    # Explicit: headquartered in City, Country
    # --------------------------------------------------------

    explicit_country = re.compile(
        rf"""
        headquartered
        (?:\s+\w+){{0,4}}
        \s+
        (?:in|at)
        \s+
        ([A-Z][A-Za-z\.\'\- ]{{1,50}})
        ,\s*
        ({country_pattern})
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    match = explicit_country.search(text)

    if match:
        city = clean_city_candidate(match.group(1))
        country = match.group(2)

        return f"{city}, {country}"

    # --------------------------------------------------------
    # Labeled HQ/corporate address blocks
    # --------------------------------------------------------

    labels = [
        "hq address",
        "headquarters address",
        "global headquarters",
        "corporate headquarters",
        "headquarters and design centre",
        "headquarters and design center",
        "headquarters",
    ]

    if allow_corporate:
        labels.extend([
            "corporate address",
            "company address",
            "mailing address",
            "office info",
            "corporate office",
        ])

    lower = text.lower()

    for label in labels:
        position = lower.find(label)

        if position < 0:
            continue

        block = text[position:position + 320]

        region_regex = re.compile(
            rf"""
            (
                [A-Z]
                [A-Za-z\.\'\- ]{{2,60}}
            )
            ,\s*
            (
                {region_pattern}
                |
                {abbreviation_pattern}
            )
            \b
            """,
            re.VERBOSE,
        )

        country_regex = re.compile(
            rf"""
            (
                [A-Z]
                [A-Za-z\.\'\- ]{{2,60}}
            )
            ,\s*
            ({country_pattern})
            \b
            """,
            re.VERBOSE,
        )

        matches = list(region_regex.finditer(block))
        matches.extend(country_regex.finditer(block))

        if not matches:
            continue

        # Last city/region pair in the local address block is usually the address,
        # not company-name prose appearing before it.
        match = sorted(matches, key=lambda value: value.start())[-1]

        city = clean_city_candidate(match.group(1))
        raw_region = match.group(2)

        region = REGION_ABBREVIATIONS.get(
            raw_region.upper(),
            raw_region,
        )

        if city:
            return f"{city}, {region}"

    return "UNKNOWN"


def find_location(company_name, website):
    if website == "UNKNOWN":
        return "UNKNOWN", "UNKNOWN"

    domain = get_base_domain(website)

    # First search: explicit headquarters.
    response = tavily_search(
        query=(
            f'"{company_name}" headquarters '
            f'"HQ Address" "headquartered in"'
        ),
        include_domains=[domain],
        max_results=6,
    )

    for result in response.get("results", []):
        url = clean_text(result.get("url", ""))
        text = (
            str(result.get("title", ""))
            + "\n"
            + str(result.get("content", ""))
        )

        location = extract_location(
            text,
            allow_corporate=False,
        )

        if location != "UNKNOWN":
            return location, url

    # Second search only if headquarters evidence failed.
    # Since the assignment asks for "Location", an official corporate/contact
    # address is a reasonable fallback, while stores/warehouses remain rejected.
    fallback = tavily_search(
        query=(
            f'"{company_name}" corporate address '
            f'company address contact office'
        ),
        include_domains=[domain],
        max_results=6,
    )

    for result in fallback.get("results", []):
        url = clean_text(result.get("url", ""))
        text = (
            str(result.get("title", ""))
            + "\n"
            + str(result.get("content", ""))
        )

        location = extract_location(
            text,
            allow_corporate=True,
        )

        if location != "UNKNOWN":
            return location, url

    return "UNKNOWN", "UNKNOWN"


# ============================================================
# LOAD / PRESERVE OUTPUT
# ============================================================

if os.path.exists(OUTPUT_FILE):
    print("Loading existing results so completed rows are preserved.")
    df = pd.read_excel(OUTPUT_FILE)
else:
    print("Creating a new test output file.")
    df = pd.read_csv(INPUT_FILE)

for column in ["Location", "Phone", "Website", "Source"]:
    if column not in df.columns:
        df[column] = "UNKNOWN"


# ============================================================
# SELECT COMPANIES
# ============================================================

if PROCESS_MODE == "all":
    indices_to_process = df.index.tolist()
else:
    indices_to_process = df[
        df["company_name"].isin(UNRESOLVED_COMPANIES)
    ].index.tolist()


print()
print("=" * 60)
print(f"PROCESS MODE: {PROCESS_MODE.upper()}")
print("=" * 60)

for index in indices_to_process:
    print(" -", df.at[index, "company_name"])

print()
print("Companies to process:", len(indices_to_process))
print("API safety limit:", MAX_API_CALLS)


# ============================================================
# PROCESS
# ============================================================

for number, index in enumerate(indices_to_process, start=1):
    company_name = clean_text(
        df.at[index, "company_name"]
    )

    print()
    print("=" * 60)
    print(
        f"Processing {number}/{len(indices_to_process)}: "
        f"{company_name}"
    )
    print("=" * 60)

    website, website_source = find_official_website(company_name)
    print("Website:", website)

    phone, phone_source = find_phone(company_name, website)
    print("Phone:", phone)

    location, location_source = find_location(company_name, website)
    print("Location:", location)

    sources = []

    for source in [
        website_source,
        phone_source,
        location_source,
    ]:
        if (
            source
            and source != "UNKNOWN"
            and source not in sources
        ):
            sources.append(source)

    df.at[index, "Website"] = website
    df.at[index, "Phone"] = phone
    df.at[index, "Location"] = location
    df.at[index, "Source"] = (
        " | ".join(sources)
        if sources
        else "UNKNOWN"
    )

    # Save after every row so progress is never lost.
    df.to_excel(
        OUTPUT_FILE,
        index=False,
    )

    print("Record saved.")
    print("API calls used so far:", API_CALL_COUNT)


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 60)
print("RUN COMPLETE")
print("=" * 60)
print("Companies processed:", len(indices_to_process))
print("Tavily API calls used:", API_CALL_COUNT)
print("Output:", OUTPUT_FILE)
print("Unverified values remain UNKNOWN.")
