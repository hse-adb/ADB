from __future__ import annotations

import hashlib
import os
import re
import shutil
from collections import deque
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import subprocess
import time
from urllib.request import urlopen

OUTPUT = Path("static-site")

# Anything with one of these suffixes is a file/resource rather
# than an HTML page.
NON_HTML_SUFFIXES = {
    ".css", ".js", ".json", ".geojson",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff", ".woff2",
    ".ttf", ".otf", ".eot",
    ".pdf", ".csv", ".txt", ".xml",
    ".zip",
}


def strip_build_query(url: str) -> str:
    """
    Convert a URL to its canonical public form.

    Examples:
    
        /frames/1?static=1
            -> /frames/1

        /frames/1?static=1#foo
            -> /frames/1#foo
    """
    parts = urlsplit(url)

    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key != "static"
    ]

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path or "/",
        urlencode(query),
        parts.fragment,
    ))


def with_static(url: str) -> str:
    """
    Add ?static=1 to a canonical application URL.
    """
    parts = urlsplit(url)

    path = normalize_page_path(
        parts.path
    )

    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key != "static"
    ]

    query.append(("static", "1"))

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        path,
        urlencode(query),
        "",
    ))


def build_request_url(
    origin: str,
    path: str,
) -> str:
    """
    Convert a root-relative site path into the URL used for
    the temporary local CLLD server.
    """
    return urljoin(
        origin.rstrip("/") + "/",
        path.lstrip("/"),
    )


def remove_fragment(url: str) -> str:
    parts = urlsplit(url)

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        parts.query,
        "",
    ))


def is_same_origin(url: str, origin: str) -> bool:
    a = urlsplit(url)
    b = urlsplit(origin)

    return (
        a.scheme in ("http", "https")
        and a.scheme == b.scheme
        and a.netloc == b.netloc
    )


def is_probable_html(url: str) -> bool:
    path = urlsplit(url).path.lower()

    suffix = Path(path).suffix

    return suffix not in NON_HTML_SUFFIXES


def html_output_dir(public_url: str) -> Path:
    """
    Filesystem directory corresponding to an HTML page.

    /                  -> static-site/
    /languages         -> static-site/languages/
    /frames/1          -> static-site/frames/1/
    """
    path = urlsplit(public_url).path.strip("/")

    if not path:
        return OUTPUT

    return OUTPUT / path


def html_output_path(public_url: str) -> Path:
    """
    Map a page URL to:

        /                 -> static-site/index.html
        /languages        -> static-site/languages/index.html
        /languages/abc    -> static-site/languages/abc/index.html
    """
    return html_output_dir(public_url) / "index.html"


def resource_output_path(url: str) -> Path:
    """
    Preserve the URL path for assets.

        /static/css/site.css
            -> static-site/static/css/site.css
    """
    path = urlsplit(url).path.lstrip("/")

    return OUTPUT / path


def output_path_for_url(url: str) -> Path:
    if is_probable_html(url):
        return html_output_path(url)

    return resource_output_path(url)


def relative_link(
    source_file: Path,
    target_file: Path,
    fragment: str = "",
) -> str:
    rel = os.path.relpath(
        target_file,
        start=source_file.parent,
    ).replace(os.sep, "/")

    if not rel:
        rel = "."

    if fragment:
        rel += f"#{fragment}"

    return rel


def relative_page_link(
    source_file: Path,
    public_url: str,
    fragment: str = "",
) -> str:
    """
    Link to the directory URL of an HTML page rather than
    to its index.html file.
    """
    target_dir = html_output_dir(public_url)

    rel = os.path.relpath(
        target_dir,
        start=source_file.parent,
    ).replace(os.sep, "/")

    if rel == ".":
        rel = "./"
    elif not rel.endswith("/"):
        rel += "/"

    if fragment:
        rel += f"#{fragment}"

    return rel


def normalize_page_path(path: str) -> str:
    """
    Canonical form for application page URLs.

    Pyramid routes in this app use paths without trailing slashes,
    while the static site represents pages as directories.
    """
    if not path:
        return "/"

    if path != "/":
        path = path.rstrip("/")

    return path or "/"


def canonical_public_url(
    discovered_url: str,
    origin: str,
) -> str | None:
    """
    Convert an arbitrary href into the canonical URL used by
    the crawler.

    The canonical URL:
      - is same-origin
      - has no ?static=1
      - has no trailing slash (except /)
      - retains genuine query parameters
    """
    absolute = urljoin(
        origin.rstrip("/") + "/",
        discovered_url,
    )

    if not is_same_origin(
        absolute,
        origin,
    ):
        return None

    parts = urlsplit(
        remove_fragment(absolute)
    )

    path = normalize_page_path(
        parts.path
    )

    query = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key != "static"
    ]

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        path,
        urlencode(query),
        "",
    ))


def extract_normal_links(
    page,
    current_public_url: str,
    origin: str,
) -> set[str]:
    """
    Discover navigational HTML pages.

    Only <a href> links are treated as crawl targets.
    Resources such as <link href>, <script src>, <img src>, etc.
    are handled separately by the asset-saving code.

    Relative links are resolved against the URL that the page
    will have in the static site, e.g.

        /frames
            -> /frames/

    so that:

        href="9/language/1/"
            -> /frames/9/language/1/
    """
    result = set()

    html = page.content()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # The generated static page lives at:
    #
    #   /frames/index.html
    #
    # and therefore relative links must be resolved as if the
    # page URL were /frames/.
    current_path = urlsplit(
        current_public_url
    ).path

    if not current_path.endswith("/"):
        current_path += "/"

    static_base = (
        origin.rstrip("/")
        + current_path
    )

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        absolute = urljoin(
            static_base,
            href,
        )

        public_url = canonical_public_url(
            absolute,
            origin,
        )

        if (
            public_url
            and is_probable_html(public_url)
        ):
            result.add(public_url)

    return result


DATATABLE_LINK_SCRIPT = r"""
() => {
    const urls = new Set();

    if (!window.jQuery || !jQuery.fn.dataTable) {
        return [];
    }

    document.querySelectorAll('table').forEach((table) => {
        let api = null;

        try {
            // DataTables 1.10+
            if (jQuery.fn.DataTable) {
                api = jQuery(table).DataTable();
            } else {
                // Older DataTables API
                api = jQuery(table).dataTable().api();
            }
        } catch (e) {
            return;
        }

        if (!api || !api.rows) {
            return;
        }

        let rows;

        try {
            rows = api
                .rows({
                    page: 'all',
                    search: 'none',
                    order: 'current',
                })
                .data()
                .toArray();
        } catch (e) {
            return;
        }

        rows.forEach((row) => {
            if (!Array.isArray(row)) {
                return;
            }

            row.forEach((cell) => {
                if (typeof cell !== 'string') {
                    return;
                }

                const wrapper =
                    document.createElement('div');

                wrapper.innerHTML = cell;

                wrapper
                    .querySelectorAll('[href], [src]')
                    .forEach((element) => {
                        const href =
                            element.getAttribute('href');

                        const src =
                            element.getAttribute('src');

                        if (href) {
                            urls.add(href);
                        }

                        if (src) {
                            urls.add(src);
                        }
                    });
            });
        });
    });

    return Array.from(urls);
}
"""


def extract_datatable_links(
    page,
    current_public_url: str,
    origin: str,
) -> set[str]:
    """
    Important: this reads DataTables' complete client-side data,
    not merely the currently visible rows.
    """
    try:
        raw_urls = page.evaluate(
            DATATABLE_LINK_SCRIPT
        )
    except Exception:
        return set()

    current_path = urlsplit(
        current_public_url
    ).path

    if not current_path.endswith("/"):
        current_path += "/"

    static_base = (
        origin.rstrip("/")
        + current_path
    )

    result = set()

    for raw_url in raw_urls:
        absolute = urljoin(
            static_base,
            raw_url,
        )

        public_url = canonical_public_url(
            absolute,
            origin,
        )

        if (
            public_url
            and is_probable_html(public_url)
        ):
            result.add(public_url)

    return result


def resolve_site_url(
    public_path: str,
    value: str,
    origin: str,
) -> str:
    """
    Resolve a link relative to a canonical root-relative
    page path, returning an absolute local-server URL.
    """
    page_url = urljoin(
        origin.rstrip("/") + "/",
        public_path.lstrip("/"),
    )

    return urljoin(
        page_url,
        value,
    )


def is_asset_reference(tag, attr: str) -> bool:
    """
    Determine whether an HTML URL attribute refers to a static
    resource rather than another HTML page.

    Some CLLD resources, notably /_js, have no filename extension,
    so URL suffix detection is not sufficient.
    """
    name = tag.name.lower()

    if name == "script" and attr == "src":
        return True

    if name == "link" and attr == "href":
        rel = {
            x.lower()
            for x in tag.get("rel", [])
        }

        if rel & {
            "stylesheet",
            "icon",
            "shortcut",
            "apple-touch-icon",
            "manifest",
            "preload",
            "modulepreload",
            "mask-icon",
        }:
            return True

    if name in {
        "img",
        "source",
        "audio",
        "video",
        "iframe",
        "embed",
        "object",
    } and attr in {
        "src",
        "poster",
        "data",
    }:
        return True

    return False


def rewrite_html(
    html: str,
    current_public_url: str,
    origin: str,
) -> str:
    """
    Rewrite same-origin absolute/root-relative URLs into
    relative links to the generated static files.
    """
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    source_file = html_output_path(
        current_public_url
    )

    for tag in soup.find_all(True):
        for attr in ("href", "src", "action", "poster"):
            value = tag.get(attr)

            if not value:
                continue

            # Preserve fragments-only links.
            if value.startswith("#"):
                continue

            absolute = resolve_site_url(
                current_public_url,
                value,
                origin,
            )

            if not is_same_origin(
                absolute,
                origin,
            ):
                continue

            parsed = urlsplit(absolute)

            public_url = strip_build_query(
                remove_fragment(absolute)
            )

            if is_asset_reference(tag, attr):
                target_file = resource_output_path(
                    public_url
                )

                tag[attr] = relative_link(
                    source_file,
                    target_file,
                    parsed.fragment,
                )

            elif is_probable_html(public_url):
                tag[attr] = relative_page_link(
                    source_file,
                    public_url,
                    parsed.fragment,
                )

            else:
                target_file = resource_output_path(
                    public_url
                )

                tag[attr] = relative_link(
                    source_file,
                    target_file,
                    parsed.fragment,
                )

    return str(soup)


def rewrite_css(
    css: str,
    current_url: str,
    origin: str,
) -> str:
    """
    Rewrite same-origin URLs in CSS url(...) and @import
    declarations.

    This is needed for fonts/images/backgrounds referenced
    from stylesheets.
    """

    current_public_url = strip_build_query(
        current_url
    )

    source_file = resource_output_path(
        current_public_url
    )

    url_pattern = re.compile(
        r"url\(\s*(['\"]?)(.*?)\1\s*\)",
        re.IGNORECASE,
    )

    def replace_url(match):
        quote_char = match.group(1)
        raw_url = match.group(2)

        if (
            not raw_url
            or raw_url.startswith("data:")
            or raw_url.startswith("#")
        ):
            return match.group(0)

        absolute = urljoin(
            current_public_url,
            raw_url,
        )

        if not is_same_origin(
            absolute,
            origin,
        ):
            return match.group(0)

        parsed = urlsplit(absolute)

        public_url = strip_build_query(
            remove_fragment(absolute)
        )

        target_file = resource_output_path(
            public_url
        )

        relative = relative_link(
            source_file,
            target_file,
            parsed.fragment,
        )

        return f"url({quote_char}{relative}{quote_char})"

    return url_pattern.sub(
        replace_url,
        css,
    )

def rewrite_saved_css(output_dir: Path, origin):
    for css_file in output_dir.rglob("*.css"):
        rel = css_file.relative_to(output_dir).as_posix()
        public_url = "/" + rel

        css = css_file.read_text(encoding="utf-8")

        css = rewrite_css(
            css,
            public_url,
            origin,
        )

        css_file.write_text(
            css,
            encoding="utf-8",
        )

def reset_datatables(page):
    """
    Destroy every currently initialized DataTable so that the
    saved HTML contains the original table markup.

    The initialization script remains in the HTML and will run
    exactly once when the static page is subsequently opened.
    """
    result = page.evaluate(
        """
        () => {
            const $ = window.jQuery;

            if (!$ || !$.fn || !$.fn.dataTable) {
                return {
                    found: false,
                    tables: 0,
                    destroyed: 0,
                };
            }

            const tables = Array.from(
                document.querySelectorAll('table')
            );

            let destroyed = 0;

            tables.forEach((table) => {
                try {
                    let initialized = false;

                    // DataTables 1.10+
                    if (
                        typeof $.fn.dataTable.isDataTable === 'function'
                    ) {
                        initialized =
                            $.fn.dataTable.isDataTable(table);
                    }

                    // Older DataTables versions.
                    if (
                        !initialized &&
                        typeof $.fn.dataTable.fnIsDataTable === 'function'
                    ) {
                        initialized =
                            $.fn.dataTable.fnIsDataTable(table);
                    }

                    // Last-resort check for the legacy global settings
                    // collection.
                    if (
                        !initialized &&
                        Array.isArray($.fn.dataTableSettings)
                    ) {
                        initialized =
                            $.fn.dataTableSettings.some(
                                settings =>
                                    settings.nTable === table
                            );
                    }

                    if (!initialized) {
                        return;
                    }

                    // Use the legacy API where available, since CLLD
                    // uses the legacy DataTables API.
                    if (
                        typeof $(table).dataTable === 'function'
                    ) {
                        $(table)
                            .dataTable()
                            .fnDestroy();
                    } else if (
                        typeof $(table).DataTable === 'function'
                    ) {
                        $(table)
                            .DataTable()
                            .destroy();
                    }

                    destroyed += 1;

                } catch (error) {
                    console.warn(
                        'Could not destroy DataTable',
                        table,
                        error
                    );
                }
            });

            return {
                found: true,
                tables: tables.length,
                destroyed: destroyed,
            };
        }
        """
    )

    print(
        "DataTables reset:",
        result,
    )

class StaticBuilder:
    def __init__(self, origin: str):
        self.origin = origin.rstrip("/")
        self.queue = deque(["/"])
        self.seen = set()

        # Maps canonical URL -> generated file.
        self.generated = {}

        # Used to detect asset path collisions.
        self.asset_hashes = {}

    def canonical_url(
        self,
        url: str,
    ) -> str | None:
        return canonical_public_url(
            url,
            self.origin,
        )

    def save_response_asset(
        self,
        response,
    ):
        """
        Save non-HTML same-origin network responses.
        This catches CSS, JS, fonts, images, GeoJSON, etc.
        """
        if not is_same_origin(
            response.url,
            self.origin,
        ):
            return

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
            .lower()
        )

        if "text/html" in content_type:
            return

        try:
            body = response.body()
        except Exception:
            return

        public_url = strip_build_query(
            remove_fragment(response.url)
        )

        target = resource_output_path(
            public_url
        )

        if not target.name:
            return

        digest = hashlib.sha256(body).hexdigest()

        previous = self.asset_hashes.get(
            str(target)
        )

        if previous and previous != digest:
            raise RuntimeError(
                "Two different responses map to the "
                f"same static file: {target}"
            )

        self.asset_hashes[str(target)] = digest

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_bytes(body)

    def save_explicit_asset(
        self,
        page,
        url: str,
    ):
        """
        Save a same-origin asset referenced by the page,
        even if the browser did not happen to request it.
        """
        absolute = urljoin(
            page.url,
            url,
        )

        if not is_same_origin(
            absolute,
            self.origin,
        ):
            return

        public_url = strip_build_query(
            remove_fragment(absolute)
        )

        target = resource_output_path(
            public_url
        )

        if not target.name:
            return

        try:
            response = page.request.get(
                absolute,
                timeout=30_000,
            )

            if not response.ok:
                return

            body = response.body()

        except Exception:
            return

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_bytes(body)

    def discover_assets_from_page(self, page):
        urls = page.evaluate(
            """
            () => {
                const result = [];

                document.querySelectorAll(
                    'link[href], script[src], img[src], ' +
                    'source[src], audio[src], video[src], ' +
                    'video[poster], iframe[src], embed[src], object[data]'
                ).forEach((element) => {
                    if (element.href) {
                        result.push({
                            url: element.href,
                            kind: element.tagName.toLowerCase(),
                            attr: 'href'
                        });
                    }

                    if (element.src) {
                        result.push({
                            url: element.src,
                            kind: element.tagName.toLowerCase(),
                            attr: 'src'
                        });
                    }

                    if (element.poster) {
                        result.push({
                            url: element.poster,
                            kind: element.tagName.toLowerCase(),
                            attr: 'poster'
                        });
                    }

                    if (element.data) {
                        result.push({
                            url: element.data,
                            kind: element.tagName.toLowerCase(),
                            attr: 'data'
                        });
                    }
                });

                return result;
            }
            """
        )

        for item in urls:
            url = item["url"]

            if is_probable_html(url):
                # For things with page-like URLs, only the known
                # resource-bearing elements should get downloaded.
                is_asset = (
                    item["kind"] == "script"
                    or item["kind"] == "link"
                    or item["kind"] in {
                        "img",
                        "source",
                        "audio",
                        "video",
                        "iframe",
                        "embed",
                        "object",
                    }
                )

                if not is_asset:
                    continue

            self.save_explicit_asset(
                page,
                url,
            )

    def enqueue(
        self,
        urls: set[str],
    ):
        for url in urls:
            canonical = self.canonical_url(url)

            if (
                canonical
                and canonical not in self.seen
            ):
                self.queue.append(canonical)

    def run(self):
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)

        OUTPUT.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
            )

            context = browser.new_context()

            page = context.new_page()

            # Capture every same-origin CSS/JS/image/font/etc.
            context.on(
                "response",
                self.save_response_asset,
            )

            while self.queue:
                public_url = self.queue.popleft()

                if public_url in self.seen:
                    continue

                self.seen.add(public_url)

                request_path = with_static(public_url)
                build_url = build_request_url(
                    self.origin,
                    request_path,
                )

                print(
                    f"[{len(self.seen)}] {public_url}"
                )

                print(
                    f"    GET {build_url}"
                )

                try:
                    response = page.goto(
                        build_url,
                        wait_until="networkidle",
                        timeout=60_000,
                    )

                    if response is None:
                        print("  no response")
                        continue

                    if response.status >= 400:
                        print(
                            f"  HTTP {response.status}"
                        )
                        continue

                    # Let DataTables/map initialization settle.
                    page.wait_for_timeout(250)

                except Exception as exc:
                    print(
                        f"  ERROR: {exc}"
                    )
                    continue

                final_public_url = self.canonical_url(
                    page.url
                )

                if not final_public_url:
                    raise RuntimeError(
                        "Page navigated off-site: "
                        + page.url
                    )

                # Save explicitly referenced assets.
                self.discover_assets_from_page(
                    page
                )

                # Normal DOM links.
                links = extract_normal_links(
                    page,
                    final_public_url,
                    self.origin,
                )

                # Links hidden in all client-side
                # DataTables rows.
                links |= extract_datatable_links(
                    page,
                    final_public_url,
                    self.origin,
                )

                self.enqueue(links)

                # Remove the runtime-generated DataTables DOM before saving.
                # The original initialization script remains in the page.
                reset_datatables(page)

                html = page.content()

                html = rewrite_html(
                    html,
                    final_public_url,
                    self.origin,
                )

                target = html_output_path(
                    final_public_url
                )

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                target.write_text(
                    html,
                    encoding="utf-8",
                )

            browser.close()

        rewrite_saved_css(
            OUTPUT,
            self.origin,
        )

        # GitHub Pages: bypass Jekyll processing.
        (
            OUTPUT / ".nojekyll"
        ).write_text(
            "",
            encoding="utf-8",
        )

        print()
        print(
            f"Built {len(self.seen)} pages "
            f"into {OUTPUT}/"
        )


def wait_for_server(
    url: str,
    process: subprocess.Popen,
    timeout: float = 30,
):
    deadline = time.time() + timeout

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "pserve exited before the server became available"
            )

        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.25)

    raise RuntimeError(
        f"Server did not become available at {url}"
    )


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default="development.ini",
    )

    parser.add_argument(
        "--origin",
        default="http://127.0.0.1:6543",
    )

    args = parser.parse_args()

    server = subprocess.Popen(
        [
            "pserve",
            args.config,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        print("Starting CLLD server...")
        wait_for_server(
            args.origin + "/?static=1",
            server,
        )

        print("Server is ready.")

        builder = StaticBuilder(
            args.origin
        )

        builder.run()

    finally:
        print("Stopping CLLD server...")

        server.terminate()

        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == "__main__":
    main()
