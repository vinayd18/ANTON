# -*- coding: utf-8 -*-
"""Search GitHub for additional antenna ML repositories."""
import urllib.request
import urllib.parse
import json

queries = [
    "patch antenna neural network",
    "microstrip antenna deep learning",
    "antenna surrogate model S11",
    "antenna inverse design",
    "pixel antenna deep learning",
]

found = {}
for q in queries:
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=10"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ANTON-Searcher)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get("items", []):
                full_name = item["full_name"]
                if full_name not in found:
                    lic = item.get("license") or {}
                    found[full_name] = {
                        "description": item.get("description"),
                        "stars": item.get("stargazers_count"),
                        "license": lic.get("name"),
                        "size": item.get("size"),
                        "url": item.get("html_url"),
                    }
    except Exception as e:
        print(f"Query error for {q}: {e}")

print(f"Total candidate repositories found: {len(found)}\n")
for name, info in sorted(found.items(), key=lambda x: x[1]["stars"] or 0, reverse=True)[:25]:
    print(f"* {name} (Stars: {info['stars']}, License: {info['license']})")
    print(f"   URL: {info['url']}")
    print(f"   Desc: {info['description']}\n")

