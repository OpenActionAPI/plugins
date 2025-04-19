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

def fill_missing_fields(data, update_description=False):
    for key, plugin in tqdm(data.items(), desc="Filling catalogue", unit="plugin"):
        repo_url = plugin.get("repository")
        if not repo_url or "github.com" not in repo_url:
            continue

        # Check what data is actually missing
        missing_name = "name" not in plugin
        missing_author = "author" not in plugin
        missing_description = update_description or "description" not in plugin
        missing_icon = not os.path.exists(os.path.join(ICON_DIR, f"{key}.png"))

        if not (missing_name or missing_author or missing_icon or missing_description):
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

        if "description" not in plugin:
            plugin["description"] = repo_info.get("description", "")

        if missing_icon:
            download_icon(owner_repo, key)

    return data

def main():
    with open(CATALOG_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)

    args = sys.argv[1:]
    plugin_key = None
    force_update_description = False

    for arg in args:
        if arg == '--update':
            force_update_description = True
        elif arg == '--help' or arg == '-h':
            print("Usage: python FillMissingData.py [plugin_key] [--update]")
            print("  --update: Force update the description field.")
            print("  plugin_key: Specify a plugin key to update only that plugin. Otherwise, all plugins will be updated.")
            return
        elif arg.startswith("--") or arg.startswith("-"):
            print(f"Unknown argument: {arg}")
            return
        elif arg in data:
            plugin_key = arg

    if plugin_key:
        subset = {plugin_key: data[plugin_key]}
        updated = fill_missing_fields(subset, update_description=force_update_description)
        data[plugin_key] = updated[plugin_key]
    else:
        data = fill_missing_fields(data, update_description=force_update_description)

    with open(CATALOG_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)

    print("Catalogue updated.")

if __name__ == "__main__":
    main()