import sys
import json
import time
import requests
from urllib.parse import urlparse
from tqdm import tqdm

# Constants
GITHUB_API = "https://api.github.com/repos"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

CATALOG_FILE = "catalogue.json"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CLEAR = "\033[0m"

# Parameters set by arguments to script
skip_update = False
wait_on_rate_limit = False

# Statistics
failed = 0
invalid_repo = 0
performed = 0
skipped = 0
succeeded = 0


def get_repo_info(owner_repo):
	response = requests.get(f"{GITHUB_API}/{owner_repo}", headers=HEADERS)
	response.encoding = "utf-8"
	return response


class RateLimitedException(BaseException):
	pass


def update_description(id, plugin):
	global failed
	global invalid_repo
	global performed
	global skipped
	global succeeded

	performed += 1

	if skip_update and "description" in plugin:
		tqdm.write(GREEN + id + ": Description already present. Skipping." + CLEAR)
		skipped += 1
		return

	repo_url = plugin.get("repository")
	if not repo_url or "github.com" not in repo_url:
		# TODO: add support for other Git providers like GitLab, Bitbucket, etc.
		tqdm.write(YELLOW + id + ": No GitHub repository found. Skipping." + CLEAR)
		invalid_repo += 1
		return

	owner_repo = "/".join(urlparse(repo_url).path.strip("/").split("/")[:2])

	repo_info = get_repo_info(owner_repo)

	if repo_info.status_code == 403 and wait_on_rate_limit:
		tqdm.write(YELLOW + "GitHub API rate limit reached. Waiting for 5 minutes..." + CLEAR)
		time.sleep(300)
		repo_info = get_repo_info(owner_repo)

	if repo_info.status_code < 200 or repo_info.status_code >= 300:
		tqdm.write(
			YELLOW + id + ": Failed to fetch repository info: unsuccessful HTTP request." + CLEAR
		)
		failed += 1
		if repo_info.status_code == 403:
			raise RateLimitedException
		else:
			return

	json = repo_info.json()
	if not json:
		tqdm.write(YELLOW + id + ": Failed to fetch repository info: no JSON response." + CLEAR)
		failed += 1
		return

	plugin["description"] = json.get("description", "")

	tqdm.write(id + ": Successfully updated description.")
	succeeded += 1

	return plugin


def update_descriptions(data, ids):
	progress_bar = tqdm(ids, desc="Filling catalogue", unit="plugin")

	for id in progress_bar:
		try:
			updated = update_description(id, data[id])
			if updated is not None:
				data[id] = updated
		except RateLimitedException:
			progress_bar.leave = False
			progress_bar.close()
			print(RED + "GitHub API rate limit reached. Stopping further requests." + CLEAR)
			print(YELLOW + "Stopped at plugin: " + id + CLEAR)
			break

	return data


def main():
	with open(CATALOG_FILE, "r", encoding="utf-8") as f:
		data = json.load(f)
	all_ids = list(data.keys())
	ids = []

	args = sys.argv[1:]
	start_from = False

	global skip_update
	global wait_on_rate_limit

	global failed
	global invalid_repo
	global performed
	global skipped
	global succeeded

	for arg in args:
		if arg.lower() == "--skip-update":
			skip_update = True
		elif arg.lower() == "--wait-on-rate-limit":
			wait_on_rate_limit = True
		elif arg.lower() == "--start-from":
			start_from = True
		elif arg in all_ids:
			if start_from:
				ids = all_ids[all_ids.index(arg) :]
			else:
				ids.append(arg)
		else:
			print(RED + "Unrecognised argument: " + arg + CLEAR)
			exit(1)

	if len(ids) == 0:
		if start_from:
			print(RED + "No plugins to be updated." + CLEAR)
			exit(1)
		ids = all_ids

	data = update_descriptions(data, ids)

	with open(CATALOG_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent="\t", ensure_ascii=False)
		f.write("\n")

	print("Catalogue updated.")
	print(f"Plugins checked: {performed}")
	print(f"Plugins skipped: {skipped}")
	print(f"Plugins failed: {failed}")
	print(f"Plugins with invalid repo: {invalid_repo}")
	print(f"Plugins succeeded: {succeeded}")
	print(
		"Plugins succeeded or skipped: "
		+ str(succeeded + skipped)
		+ " "
		+ "{:.2f}%".format((succeeded + skipped) / performed * 100)
	)


if __name__ == "__main__":
	main()
