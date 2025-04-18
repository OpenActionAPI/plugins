import sys
import json
import os
import re
import requests
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO
from tqdm import tqdm

GITHUB_API = "https://api.github.com/repos"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

CATALOG_FILE = "catalogue.json"
ICON_DIR = "icons"
os.makedirs(ICON_DIR, exist_ok=True)

def format_name(repo_name):
    base = repo_name.lower()
    base = re.sub(r"^streamdeck[-_]", "", base)
    base = re.sub(r"[-_]", " ", base)
    base = base.title()
    return base

def get_repo_info(owner_repo):
    response = requests.get(f"{GITHUB_API}/{owner_repo}", headers=HEADERS)
    response.encoding = 'utf-8'
    return response.json()

def find_download_url(owner_repo):
    releases = requests.get(f"{GITHUB_API}/{owner_repo}/releases", headers=HEADERS)
    if releases.status_code != 200:
        return None
    for release in releases.json():
        for asset in release.get("assets", []):
            if asset["name"].endswith(".streamDeckPlugin"):
                return asset["browser_download_url"]

    # fallback to raw master if a known file exists
    raw_url = f"https://github.com/{owner_repo}/raw/master/Release/"
    filename = f"{owner_repo.split('/')[-1]}.streamDeckPlugin"
    test_url = raw_url + filename
    if requests.head(test_url).status_code == 200:
        return test_url
    return None

def download_icon(owner_repo, json_key):
    try:
        owner = owner_repo.split("/")[0]
        user_info = requests.get(f"https://api.github.com/users/{owner}", headers=HEADERS)
        if user_info.status_code != 200:
            return

        avatar_url = user_info.json().get("avatar_url")
        if not avatar_url:
            return


        response = requests.get(avatar_url)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            icon_path = os.path.join(ICON_DIR, f"{json_key}.png")
            img.save(icon_path)
    except Exception as e:
        tqdm.write(f"Could not fetch icon for {json_key}: {e}")

def fill_missing_fields(data):
    for key, plugin in tqdm(data.items(), desc="Filling catalogue", unit="plugin"):
        repo_url = plugin.get("repository")
        if not repo_url or "github.com" not in repo_url:
            continue

        # Check what data is actually missing
        missing_name = "name" not in plugin
        missing_author = "author" not in plugin
        missing_download = "download_url" not in plugin
        missing_description = "description" not in plugin
        missing_icon = not os.path.exists(os.path.join(ICON_DIR, f"{key}.png"))

        if not (missing_name or missing_author or missing_download or missing_icon or missing_description):
            continue  # All good, skip this plugin

        owner_repo = "/".join(urlparse(repo_url).path.strip("/").split("/")[:2])
        repo_info = get_repo_info(owner_repo)

        # Check for rate limit error (HTTP 403)
        if repo_info is None and "403" in repo_info.get("message", ""):
            tqdm.write("GitHub API rate limit reached. Stopping further requests.")
            break  # Stop processing further

        if not repo_info:
            continue

        if missing_name:
            plugin["name"] = format_name(repo_info["name"])

        if missing_author:
            plugin["author"] = repo_info["owner"]["login"]

        if missing_download:
            dl_url = find_download_url(owner_repo)
            if dl_url:
                plugin["download_url"] = dl_url

        if "description" not in plugin:
            plugin["description"] = repo_info.get("description", "")

        if missing_icon:
            download_icon(owner_repo, key)

    return data

def main():
    with open(CATALOG_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)

        # Get optional plugin key from command-line
    if len(sys.argv) > 1:
        plugin_key = sys.argv[1]
        if plugin_key in data:
            subset = {plugin_key: data[plugin_key]}
            updated = fill_missing_fields(subset)
            data[plugin_key] = updated[plugin_key]
        else:
            print(f"Plugin '{plugin_key}' not found in catalogue.")
            return
    else:
        data = fill_missing_fields(data)

    with open(CATALOG_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)
    print("Catalogue updated.")

if __name__ == "__main__":
    main()