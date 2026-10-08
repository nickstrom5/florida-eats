"""playbook/06-app-store-listing.md -> playbook/app-store/listing.json (the fields App Store Connect takes, for ../scripts/asc_listing.py).
Run after editing the listing; it checks Apple's length limits."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
md = open(f"{ROOT}/playbook/06-app-store-listing.md").read()


def section(title):
    m = re.search(rf"^## {re.escape(title)}.*?$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1) if m else ""


def first_code(title):
    s = section(title)
    m = re.search(r"```\n(.*?)\n```", s, re.S) or re.search(r"`([^`]+)`", s)
    return m.group(1).strip()


site = "https://nickstrom5.github.io/florida-eats/"
out = {
    "name": first_code("Name"),
    "subtitle": first_code("Subtitle"),
    "privacyPolicyUrl": site + "privacy.html",
    "primaryCategory": "FOOD_AND_DRINK",
    "secondaryCategory": "TRAVEL",
    "description": first_code("Description"),
    "keywords": first_code("Keywords"),
    "promotionalText": first_code("Promotional text"),
    "whatsNew": first_code("What's New (1.0)"),
    "supportUrl": site,
    "marketingUrl": site,
}
for k, limit in (("name", 30), ("subtitle", 30), ("keywords", 100), ("promotionalText", 170), ("description", 4000), ("whatsNew", 4000)):
    assert len(out[k]) <= limit, f"{k} is {len(out[k])} characters (limit {limit})"
os.makedirs(f"{ROOT}/playbook/app-store", exist_ok=True)
json.dump(out, open(f"{ROOT}/playbook/app-store/listing.json", "w"), indent=1, ensure_ascii=False)
print({k: len(v) for k, v in out.items() if isinstance(v, str)})
