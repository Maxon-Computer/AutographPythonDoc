#!/usr/bin/env python3
"""Inject a version switcher into the sidebar of an assembled multi-version site.

Usage: inject_version_switcher.py <site_dir> <branches_file>

<branches_file> is a newline-delimited list of branch names. "main" is served
from the site root, every other branch from a directory of the same name. The
switcher is inserted into the sphinx_rtd_theme sidebar, just above the search
box, and is skipped entirely when there is only one version to choose from.
"""

import html
import os
import sys

ANCHOR = '<div role="search">'
MARKER = "<!-- version-switcher -->"

STYLE = """
<style>
.version-switcher{margin:.5em 0 .809em;text-align:left}
.version-switcher label{display:block;margin-bottom:.3em;font-size:80%;
  text-transform:uppercase;letter-spacing:.08em;opacity:.75;color:inherit}
.version-switcher select{width:100%;padding:.35em .5em;font-size:90%;
  border:1px solid rgba(255,255,255,.25);border-radius:2px;
  background-color:rgba(255,255,255,.12);color:#fcfcfc;cursor:pointer}
.version-switcher select option{color:#404040;background-color:#fcfcfc}
html[data-theme="dark"] .version-switcher select{border-color:#111;
  background-color:#141414;color:#ddd}
html[data-theme="dark"] .version-switcher select option{color:#ddd;
  background-color:#141414}
</style>
"""

SCRIPT = """
<script>
(function(){
  var sel=document.getElementById("version-switcher-select");
  if(!sel){return;}
  sel.addEventListener("change",function(){
    var base=sel.getAttribute("data-site-root")+sel.value;
    var target=base+sel.getAttribute("data-page-path")+window.location.hash;
    var fallback=base+"index.html";
    // Keep the reader on the same page when that page exists in the chosen
    // version; otherwise land on that version's index.
    fetch(target,{method:"HEAD"}).then(function(r){
      window.location.href=r.ok?target:fallback;
    }).catch(function(){window.location.href=fallback;});
  });
})();
</script>
"""


def order(branches):
    """main first, then the rest newest-looking first (reverse alphabetical)."""
    rest = sorted((b for b in branches if b != "main"), reverse=True)
    return (["main"] if "main" in branches else []) + rest


def widget(versions, current, site_root, page_path):
    options = []
    for name, directory in versions:
        selected = " selected" if name == current else ""
        options.append(
            '<option value="%s"%s>%s</option>'
            % (html.escape(directory), selected, html.escape(name))
        )
    return (
        '%s<div class="version-switcher">'
        '<label for="version-switcher-select">Version</label>'
        '<select id="version-switcher-select" data-site-root="%s" data-page-path="%s">'
        "%s</select></div>%s%s"
        % (
            MARKER,
            html.escape(site_root),
            html.escape(page_path),
            "".join(options),
            STYLE,
            SCRIPT,
        )
    )


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: inject_version_switcher.py <site_dir> <branches_file>")
    site_dir, branches_file = sys.argv[1], sys.argv[2]

    with open(branches_file) as fh:
        branches = [line.strip() for line in fh if line.strip()]

    if len(branches) < 2:
        print("Only %d version(s); skipping version switcher." % len(branches))
        return

    versions = [(b, "" if b == "main" else b + "/") for b in order(branches)]
    # Longest directory first so "Autograph-2027/" wins over main's "".
    lookup = sorted(versions, key=lambda v: len(v[1]), reverse=True)

    injected = skipped = 0
    for dirpath, _, filenames in os.walk(site_dir):
        for filename in filenames:
            if not filename.endswith(".html"):
                continue
            path = os.path.join(dirpath, filename)
            rel = os.path.relpath(path, site_dir).replace(os.sep, "/")

            current, directory = next(
                (v for v in lookup if rel.startswith(v[1])), (None, None)
            )
            if current is None:
                continue

            page_path = rel[len(directory):]
            site_root = "../" * rel.count("/") or "./"

            with open(path, encoding="utf-8") as fh:
                doc = fh.read()
            if MARKER in doc or ANCHOR not in doc:
                skipped += 1
                continue

            doc = doc.replace(
                ANCHOR, widget(versions, current, site_root, page_path) + ANCHOR, 1
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(doc)
            injected += 1

    print(
        "Version switcher: %d page(s) updated, %d skipped, %d version(s): %s"
        % (injected, skipped, len(versions), ", ".join(n for n, _ in versions))
    )


if __name__ == "__main__":
    main()
