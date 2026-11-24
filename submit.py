"""Links that open the community list's GitHub forms, already filled in."""
import re
from urllib.parse import urlencode

INDEX_REPO = "Cheeto35/ATTModIndex"
_NAME = r"[A-Za-z0-9_.-]+"
_REPO_RE = re.compile(r"^(?:(?:https?://)?(?:www\.)?github\.com/)?(" + _NAME + r")/(" + _NAME + r")(?:/.*)?$")


def parse_repo(text):
    """'https://github.com/Owner/Repo/...' or 'Owner/Repo' -> 'Owner/Repo', else None."""
    text = (text or "").strip()
    if not text or " " in text:
        return None
    if "://" in text or "." in text.split("/")[0]:
        if not re.match(r"^(?:https?://)?(?:www\.)?github\.com/", text, re.I):
            return None
    elif text.count("/") != 1:
        return None
    m = _REPO_RE.match(text)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}" if repo else None


def _new_issue(params):
    return f"https://github.com/{INDEX_REPO}/issues/new?" + urlencode(params)


def issue_url(repo, name, description, side, tags):
    return _new_issue({"template": "submit-mod.yml", "labels": "submission", "title": "Add mod: " + name,
                       "repo": "https://github.com/" + repo, "name": name, "description": description,
                       "side": side, "tags": tags})


def remove_url(repo, name):
    return _new_issue({"template": "remove-mod.yml", "labels": "removal", "title": "Remove mod: " + name,
                       "mod": "https://github.com/" + repo})


def owner_names(repo, submitted_by):
    """Who may remove a listing, for showing: the person who added it, then the repo's owner."""
    out = []
    for n in (submitted_by, repo.split("/")[0]):
        if n and n.lower() not in {o.lower() for o in out}:
            out.append(n)
    return " or ".join(out)


def report_url(mod_id):
    return _new_issue({"template": "report-mod.yml", "labels": "report", "title": "Report: " + mod_id,
                       "mod": mod_id})
