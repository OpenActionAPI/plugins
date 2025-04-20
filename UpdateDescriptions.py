import sys
import json
import time
import numbers
import requests
from urllib.parse import urlparse
from tqdm import tqdm

# Constants
GITHUB_API = "https://api.github.com/repos"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

CATALOG_FILE = "catalogue.json"

# Configurations set in args
skipUpdate = False
waitOnRateLimit = False
log = False

# stats
failed = 0
invalid_repo = 0
performed = 0
skiped = 0
success = 0

def get_repo_info(owner_repo):
    response = requests.get(f"{GITHUB_API}/{owner_repo}", headers=HEADERS)
    response.encoding = 'utf-8'
    return response

def UpdateDescription(key, plugin):

    global failed
    global invalid_repo
    global performed
    global skiped
    global success

    performed += 1

    if skipUpdate and "description" in plugin:
        if log:
            tqdm.write(key + ": \033[94mSkipping update for plugin\033[0m")
        skiped += 1
        return 208
    repo_url = plugin.get("repository")
    if not repo_url or "github.com" not in repo_url:
        if log:
            # TODO: add a support for other git providers like gitlab, bitbucket, etc.
            tqdm.write(key + ": \033[93mNo GitHub repository found. Skipping.\033[0m")
        invalid_repo += 1
        return 404

    repo_info = 403

    timesFailed = 0

    # Do while loop
    while True:
        owner_repo = "/".join(urlparse(repo_url).path.strip("/").split("/")[:2])
        repo_info = get_repo_info(owner_repo)

        if repo_info.status_code == 403:
            timesFailed += 1

            if log and timesFailed == 1:
                tqdm.write(key + ": \033[91mFailed to fetch repository info.\033[0m")

            if waitOnRateLimit:
                tqdm.write("\033[93mGitHub API rate limit reached. Waiting for 5 minutes...\033[0m")
                try:
                    time.sleep(300)
                except KeyboardInterrupt:
                    tqdm.write("\033[93mProcess interrupted by user.\033[0m")
                    failed += 1
                    return 403
                continue
            else:
                failed += 1
                return 403
        break

    json = repo_info.json()
    if not json:
        if log:
            tqdm.write(key + ": No JSON response. Skipping update.")
        failed += 1
        return 204
    
    if log:
        tqdm.write(key + ": \033[92mDone.\033[0m")

    plugin["description"] = json.get("description", "")

    success += 1
    return plugin

def UpdateDescriptions(data):

    # if its only one plugin, we can skip the for loop
    if len(data) == 1:
        key, plugin = list(data.items())[0]
        plugin = UpdateDescription(key, plugin)

        if plugin == 403:
            print("\033[91mGitHub API rate limit reached. Stopping further requests.\033[0m")
            return 403
        
        elif not isinstance(plugin, numbers.Number):
            data[key] = plugin

        return data

    progress_bar = tqdm(data.items(), desc="Filling catalogue", unit="plugin")
    # if we have multiple plugins, we need to loop through them while displaying a progress bar
    for key, plugin in progress_bar:
        updatedPlugin = UpdateDescription(key, plugin)

        if updatedPlugin == 403:
            progress_bar.leave = False
            progress_bar.close()
            print("\033[91mGitHub API rate limit reached. Stopping further requests.\033[0m")
            print("Stoped at plugin: " + key)
            break

        elif isinstance(plugin, numbers.Number):
            continue

        plugin = updatedPlugin

    return data

def main():
    with open(CATALOG_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)

    args = sys.argv[1:]
    updateAll = True
    startFrom = False

    global skipUpdate
    global waitOnRateLimit
    global log

    global failed
    global invalid_repo
    global performed
    global skiped
    global success

    for arg in args:
        if arg == '--help' or arg == '-h':
            print("Usage: python --skip-update --wait-on-rate-limit UpdateDescriptions.py [plugin_key1] [plugin_key2] ...")
            print("  plugin_key: Specify a plugin key to update only that plugin. If non are provided, all plugins will be updated. (Configs will only be applied of writen before the plugin_key)")
            print("  --skip-update: Skip updating the description if it already exists.")
            print("  --wait-on-rate-limit: In the case you get API rate limited, the program will retry until requests are allowed again.")
            print("  --log: Logs the plugins and some info about them to the console.")
            print("  --start-from [plugin_key]: Specify a plugin key to start updating from. (Useful for when you want to resume a full update from a specific plugin)")
            return
        elif arg == '--skip-update':
            skipUpdate = True
            continue
        elif arg == '--wait-on-rate-limit':
            waitOnRateLimit = True
            continue
        elif arg == '--log':
            log = True
            continue
        elif arg.startswith('--start-from'):
            startFrom = True
            continue
        elif arg.startswith("--") or arg.startswith("-"):
            print(f"Unknown argument: {arg}")
            return
        elif arg in data:
            updateAll = False

            if startFrom:
                startFrom = False
                
                # if startFrom is true, we need to update all plugins starting at arg
                updateKeys = list(data.keys())
                startIndex = updateKeys.index(arg)
                for key in updateKeys[startIndex:]:
                    subset = {key: data[key]}
                    updated = UpdateDescriptions(subset)
                    if updated == 403:
                        return
                    data[key] = updated[key]
                continue

            subset = {arg: data[arg]}
            updated = UpdateDescriptions(subset)
            if (updated == 403):
                return
            data[arg] = updated[arg]

    if updateAll:
        data = UpdateDescriptions(data,)

    with open(CATALOG_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)

    print("Catalogue updated.")
    print("Plugins checked: " + str(performed))
    print("Plugins skipped: " + str(skiped))
    print("Plugins failed: " + str(failed))
    print("Plugins with invalid repo: " + str(invalid_repo))
    print("Plugins success: " + str(success))

    print("Plugins succeded or skiped: " + str(success + skiped) + " " + "{:.2f}%".format((success + skiped) / performed * 100))

if __name__ == "__main__":
    main()