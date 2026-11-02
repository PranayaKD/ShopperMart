import urllib.request
import json
import re
import os
import sys

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

queries = {
    # Laundry
    "beco-front-load-laundry-detergent-liquid-refill": "Beco Front Load Laundry Detergent Liquid Refill",
    "surf-excel-matic-liquid-detergent-5-kg-for-top-l": "Surf Excel Matic Liquid Detergent Top Load 5 kg",
    "morelight-detergent-liquid-pouch": "Morelight Detergent Liquid Pouch 5 L",
    "beco-top-load-laundry-detergent-liquid-refill": "Beco Top Load Laundry Detergent Liquid Refill 2 L",
    "beco-top-load-laundry-detergent-liquid": "Beco Top Load Laundry Detergent Liquid 960 ml",
    "ariel-power-gel-liquid-detergent-for-front-load": "Ariel Power Gel Front Load Liquid Detergent",
    "surf-excel-easy-wash-detergent-powder": "Surf Excel Easy Wash Detergent Powder 1.5 kg",
    "ariel-power-gel-liquid-detergent-for-top-load-wa": "Ariel Power Gel Top Load Liquid Detergent",
    # Cleaning
    "mr-muscle-kitchen-cleaner-spray-fresh-lemon": "Mr Muscle Kitchen Cleaner Spray Fresh Lemon 450 ml",
    "ezee-everyday-ultra-clean-bathroom-floor-cleaner": "Ezee Everyday Bathroom Floor Cleaner 1 L",
    "beco-max-kitchen-cleaner-liquid": "BECO Max Kitchen Cleaner Liquid 500 ml",
    "lizol-kitchen-cleaner-degreaser-spray": "Lizol Kitchen Cleaner & Degreaser Spray 450 ml",
    "ezee-everyday-ultra-clean-toilet-cleaner-instant": "Ezee Everyday Toilet Cleaner 1 L",
    "koparo-magic-foam-cleaner-spray-for-kitchen-tyre": "Koparo Magic Foam Cleaner Spray 460 ml",
    "harpic-original-toilet-cleaner-liquid": "Harpic Original Toilet Cleaner Liquid 1 L",
    "urbanwipe-kitchen-cleaning-spray": "Urbanwipe Kitchen Cleaning Spray 500 ml",
    # Rice
    "bestvalue-sona-masoori-raw-rice": "BestValue Sona Masoori Raw Rice 1 kg",
    "daily-good-sona-masoori-raw-rice": "Daily Good Sona Masoori Raw Rice 1 kg",
    "gts-original-kolam-rice": "GTS Original Kolam Rice 5 kg",
    "daily-good-idli-rice": "Daily Good Idli Rice 1 kg",
    "daily-good-dosa-rice": "Daily Good Dosa Rice 1 kg",
    "india-gate-dubar-basmati-rice-long-slender-grain": "India Gate Dubar Basmati Rice 1 kg",
    "daawat-rozana-super-basmati-rice-medium-grain": "Daawat Rozana Super Basmati Rice 1 kg",
    "india-gate-everyday-basmati-rice-fluffy-medium-g": "India Gate Everyday Basmati Rice 1 kg",
}

print("Testing direct Zepto search or BigBasket search for clean images...")
for slug, query in list(queries.items())[:3]:
    encoded = urllib.parse.quote(query)
    # Search DDG HTML
    url = f"https://html.duckduckgo.com/html/?q=site:zepto.com+{encoded}"
    req = urllib.request.Request(url, headers=headers)
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        # Find Zepto product page
        links = re.findall(r'https://www\.zepto\.com/pn/[^\s\"\'&]+', html)
        print(f"{slug} -> Found {len(links)} Zepto links: {links[:1]}")
    except Exception as e:
        print(f"Error {slug}: {e}")

