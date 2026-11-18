"""
Pull the RAR issues of Jira filter 12811 from Jira Cloud -> raw_issues.json

Required environment variables: JIRA_EMAIL, JIRA_API_TOKEN
Optional: JIRA_SITE (default mobiledrivetech.atlassian.net), JIRA_JQL (default filter=12811 ORDER BY key ASC)
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

JIRA_SITE = os.environ.get("JIRA_SITE", "mobiledrivetech.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JQL = os.environ.get("JIRA_JQL", "filter=12811 ORDER BY key ASC")
# External Link: NR1L uses customfield_10599, NR1LD uses customfield_10595
FIELDS = ["summary", "status", "customfield_10595", "customfield_10599"]

_auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
_HEADERS = {"Authorization": f"Basic {_auth}", "Content-Type": "application/json",
            "Accept": "application/json"}


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Jira API error {e.code} for {url}:\n{e.read().decode(errors='replace')}") from e


def _get(url):
    req = urllib.request.Request(url, headers=_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def diagnose():
    """Print which Jira account the secrets log in as and whether it can open the filter."""
    code, me = _get(f"https://{JIRA_SITE}/rest/api/3/myself")
    if code == 401:
        sys.exit("Jira rejected JIRA_EMAIL / JIRA_API_TOKEN (401). Check that the email matches the account "
                 "that created the API token, and that the token has not expired or been revoked.")
    if code != 200:
        print(f"/myself returned HTTP {code}: {me}")
    else:
        print(f"Authenticated as: {me.get('displayName')} (active={me.get('active')})")
    m = re.search(r"filter\s*=\s*(\d+)", JQL)
    if m:
        fcode, f = _get(f"https://{JIRA_SITE}/rest/api/3/filter/{m.group(1)}")
        if fcode == 200:
            print(f"Filter {m.group(1)} '{f.get('name')}' owner: {(f.get('owner') or {}).get('displayName')}")
        else:
            print(f"This account cannot open filter {m.group(1)} (HTTP {fcode}). Share the filter with this "
                  "account (or with the organization), or use secrets of an account that can open it.")


def search(jql, fields):
    url = f"https://{JIRA_SITE}/rest/api/3/search/jql"
    issues, token = [], None
    while True:
        body = {"jql": jql, "maxResults": 100, "fields": fields}
        if token:
            body["nextPageToken"] = token
        data = _post(url, body)
        page = data.get("issues", [])
        issues.extend(page)
        token = data.get("nextPageToken")
        if not token or not page:
            return issues


def main():
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        sys.exit("JIRA_EMAIL / JIRA_API_TOKEN are empty. Add both under "
                 "Settings > Secrets and variables > Actions, then re-run.")
    diagnose()
    issues = search(JQL, FIELDS)
    print(f"'{JQL}': {len(issues)} issues")
    if not issues:
        # Jira answers an unauthorised search with 200 and no issues: do not publish an empty page.
        sys.exit(f"'{JQL}' returned 0 issues. Check that the secrets belong to an account that can open the filter.")
    with open("raw_issues.json", "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
