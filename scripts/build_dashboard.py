"""raw_issues.json -> site/index.html (+ site/data.json)"""
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
JIRA_SITE = os.environ.get("JIRA_SITE", "mobiledrivetech.atlassian.net")


def main():
    with open("raw_issues.json", encoding="utf-8") as f:
        raw = json.load(f)
    issues = []
    for it in raw:
        f = it.get("fields", {}) or {}
        st = f.get("status") or {}
        ext = str(f.get("customfield_10599") or f.get("customfield_10595") or "").strip()
        m = re.search(r"[?&#]id=(\d+)", ext)
        issues.append({
            "key": it["key"],
            "summary": (f.get("summary") or "").strip(),
            "status": st.get("name", ""),
            "category": (st.get("statusCategory") or {}).get("key", "indeterminate"),
            "ext": ext,
            "extId": m.group(1) if m else ("link" if ext else ""),
        })
    data = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "site": JIRA_SITE,
        "filter": "12811",
        "issues": issues,
    }
    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    os.makedirs("site", exist_ok=True)
    with open("site/data.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    gpath = os.path.join(HERE, "giscus.json")   # comments config (repo / category ids for giscus)
    giscus = "null"
    if os.path.exists(gpath):
        with open(gpath, encoding="utf-8") as fh:
            giscus = json.dumps(json.load(fh), ensure_ascii=False)
    with open("site/index.html", "w", encoding="utf-8") as fh:
        fh.write(html.replace("/*__DATA__*/null", payload).replace("/*__GISCUS__*/null", giscus))
    print(f"{len(issues)} issues -> site/index.html")


if __name__ == "__main__":
    main()
