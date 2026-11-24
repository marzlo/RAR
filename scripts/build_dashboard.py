"""raw_issues.json -> site/index.html (+ site/data.json)"""
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
JIRA_SITE = os.environ.get("JIRA_SITE", "mobiledrivetech.atlassian.net")


def adf_text(node):
    """Atlassian Document Format -> plain text."""
    if isinstance(node, list):
        return "".join(adf_text(n) for n in node)
    if not isinstance(node, dict):
        return str(node or "")
    t = node.get("type")
    a = node.get("attrs") or {}
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    if t == "mention":
        return a.get("text") or "@user"
    if t == "emoji":
        return a.get("text") or a.get("shortName") or ""
    if t in ("inlineCard", "blockCard"):
        return a.get("url", "")
    if t in ("mediaSingle", "mediaGroup", "media"):
        return "[image]"
    inner = adf_text(node.get("content") or [])
    if t in ("paragraph", "heading", "codeBlock", "blockquote", "rule", "table", "tableRow"):
        return inner + "\n"
    if t == "listItem":
        return "• " + inner
    if t in ("tableCell", "tableHeader"):
        return inner.strip() + " | "
    return inner


REL_RE = re.compile(r"(?<![A-Za-z0-9])R([1-9][0-9]?)(?![A-Za-z0-9])")


def release_of(f):
    """BSP Release field first, else an R<n> tag in the summary (R1..R99; not R1L / SR26 / R07)."""
    for cf in ("customfield_10560", "customfield_10830"):
        v = f.get(cf)
        if isinstance(v, list):
            v = v[0] if v else None
        if isinstance(v, dict):
            v = v.get("value") or v.get("name")
        if v:
            return str(v).strip(), "bsp"
    m = REL_RE.search(f.get("summary") or "")
    return ("R" + m.group(1), "sum") if m else ("", "")


def latest_jira_comment(f):
    lst = ((f.get("comment") or {}).get("comments")) or []
    if not lst:
        return None
    c = sorted(lst, key=lambda x: x.get("created", ""))[-1]
    body = c.get("body")
    text = adf_text(body) if isinstance(body, (dict, list)) else str(body or "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > 600:
        text = text[:600].rstrip() + "…"
    return {"by": (c.get("author") or {}).get("displayName", ""), "at": c.get("created", ""), "text": text}


def main():
    with open("raw_issues.json", encoding="utf-8") as f:
        raw = json.load(f)
    issues = []
    for it in raw:
        f = it.get("fields", {}) or {}
        st = f.get("status") or {}
        ext = str(f.get("customfield_10599") or f.get("customfield_10595") or "").strip()
        m = re.search(r"[?&#]id=(\d+)", ext)
        rel, rel_src = release_of(f)
        issues.append({
            "key": it["key"],
            "relAuto": rel,
            "relSrc": rel_src,
            "summary": (f.get("summary") or "").strip(),
            "status": st.get("name", ""),
            "category": (st.get("statusCategory") or {}).get("key", "indeterminate"),
            "assignee": ((f.get("assignee") or {}).get("displayName") or ""),
            "labels": f.get("labels") or [],
            "ext": ext,
            "extId": m.group(1) if m else ("link" if ext else ""),
            "jc": latest_jira_comment(f),
        })
    # STLA prsse export (scripts/prsse.json): External Link id -> STLA status / Other Specification
    ppath = os.path.join(HERE, "prsse.json")
    prsse, stla_meta = {}, {}
    if os.path.exists(ppath):
        with open(ppath, encoding="utf-8") as fh:
            pj = json.load(fh)
        prsse = pj.get("items", {})
        stla_meta = {k: v for k, v in pj.items() if k != "items"}
    for i in issues:
        p = prsse.get(i["extId"]) or {}
        i["stla"] = p.get("status", "")
        i["spec"] = p.get("spec", "")
    cpath = os.path.join(HERE, "..", "comments.json")   # per-ticket comments written by the page
    comments = {"comments": {}}
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as fh:
            comments = json.load(fh)
    lpath = os.path.join(HERE, "..", "releases.json")   # Release values typed on the page
    releases = {"releases": {}}
    if os.path.exists(lpath):
        with open(lpath, encoding="utf-8") as fh:
            releases = json.load(fh)
    rpath = os.path.join(HERE, "..", "remarks.json")    # per-ticket "Status remark" (one editable text each)
    remarks = {"remarks": {}}
    if os.path.exists(rpath):
        with open(rpath, encoding="utf-8") as fh:
            remarks = json.load(fh)
    data = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "site": JIRA_SITE,
        "filter": "12811",
        "issues": issues,
        "comments": comments,
        "remarks": remarks,
        "releases": releases,
        "stla_meta": stla_meta,
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
