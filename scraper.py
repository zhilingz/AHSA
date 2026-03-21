"""
Purpose: Fetch skill metadata and SKILL.md files from ClawHub.
Input: CLI arguments and optional output paths.
Output: Local skill markdown files and metadata indexes.
"""

import argparse
import json
import time
from pathlib import Path

import requests


API_BASE = "https://wry-manatee-359.convex.site/api/v1"
PAGE_SIZE = 200


def ensure_dir(path):
    """
    Purpose: Create one directory if it does not exist.
    Input: A directory path.
    Output: A ready-to-use directory path.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_json(session, url, **kwargs):
    """
    Purpose: Send one GET request and parse its JSON body.
    Input: A requests session, one URL, and request options.
    Output: A parsed JSON object.
    """
    response = session.get(url, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def fetch_skill_list(session, count):
    """
    Purpose: Fetch ranked skill metadata from the list API.
    Input: A requests session and a target count.
    Output: A list of skill metadata objects.
    """
    skills = []
    cursor = None
    while len(skills) < count:
        params = {"limit": PAGE_SIZE, "sort": "stars"}
        if cursor:
            params["cursor"] = cursor
        data = get_json(session, f"{API_BASE}/skills", params=params)
        items = data.get("items", [])
        cursor = data.get("nextCursor")
        if not items:
            break
        for item in items:
            stats = item.get("stats", {})
            skills.append(
                {
                    "slug": item["slug"],
                    "display_name": item.get("displayName", item["slug"]),
                    "summary": item.get("summary", ""),
                    "stars": stats.get("stars", 0),
                    "downloads": stats.get("downloads", 0),
                    "installs_all_time": stats.get("installsAllTime", 0),
                    "installs_current": stats.get("installsCurrent", 0),
                    "comments": stats.get("comments", 0),
                    "versions": stats.get("versions", 0),
                    "created_at": item.get("createdAt"),
                    "updated_at": item.get("updatedAt"),
                    "latest_version": (item.get("latestVersion") or {}).get("version", ""),
                    "changelog": (item.get("latestVersion") or {}).get("changelog", ""),
                    "license": (item.get("latestVersion") or {}).get("license", ""),
                    "tags": item.get("tags", {}),
                    "metadata": item.get("metadata"),
                }
            )
            if len(skills) >= count:
                break
        if not cursor:
            break
        time.sleep(0.3)
    return skills[:count]


def fetch_skill_content(session, slug):
    """
    Purpose: Fetch one SKILL.md file from the file API.
    Input: A requests session and one skill slug.
    Output: Markdown text or an empty string when missing.
    """
    response = session.get(f"{API_BASE}/skills/{slug}/file", params={"path": "SKILL.md"}, timeout=30)
    if response.status_code == 404:
        return ""
    response.raise_for_status()
    return response.text


def write_outputs(base_dir, skills, skip_content):
    """
    Purpose: Write skill markdown files and metadata indexes to disk.
    Input: One output base directory, skill metadata list, and content flag.
    Output: Files in skills, descriptions, index.json, and index.csv.
    """
    output_dir = ensure_dir(base_dir / "output")
    skills_dir = ensure_dir(output_dir / "skills")
    descriptions_dir = ensure_dir(output_dir / "descriptions")
    session = requests.Session()
    session.headers.update({"User-Agent": "AHSA-Scraper/1.0"})
    index = []
    for rank, skill in enumerate(skills, start=1):
        slug = skill["slug"]
        if not skip_content:
            (skills_dir / f"{slug}.md").write_text(fetch_skill_content(session, slug), encoding="utf-8")
            time.sleep(0.1)
        desc = dict(skill)
        desc["rank"] = rank
        desc["clawhub_url"] = f"https://clawhub.ai/skills/{slug}"
        (descriptions_dir / f"{slug}.json").write_text(json.dumps(desc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append(
            {
                "rank": rank,
                "slug": slug,
                "display_name": skill["display_name"],
                "stars": skill["stars"],
                "downloads": skill["downloads"],
                "installs_all_time": skill["installs_all_time"],
            }
        )
    (output_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(output_dir / "index.csv", "w", encoding="utf-8") as f:
        f.write("rank,slug,display_name,stars,downloads,installs_all_time\n")
        for item in index:
            name = item["display_name"].replace('"', '""')
            f.write(f'{item["rank"]},"{item["slug"]}","{name}",{item["stars"]},{item["downloads"]},{item["installs_all_time"]}\n')


def main():
    """
    Purpose: Run the scraper from the command line.
    Input: CLI arguments.
    Output: Local skill content files and metadata files.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--count", type=int, default=1000)
    parser.add_argument("--output", default=".")
    parser.add_argument("--skip-content", action="store_true")
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": "AHSA-Scraper/1.0"})
    skills = fetch_skill_list(session, args.count)
    if not skills:
        raise RuntimeError("no skills fetched")
    write_outputs(Path(args.output).resolve(), skills, args.skip_content)
    print(json.dumps({"count": len(skills), "output": str(Path(args.output).resolve() / "output")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
