import re
from typing import Optional, Literal

import frappe
from frappe.utils import scrub_urls
from frappe.utils.pdf import inline_private_images

from playwright.sync_api import sync_playwright


BASE_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
]


def normalize_pdf_page_css(css: str) -> str:
    """
    Jika ada @pdf {}:
      - Comment semua @page {}
      - Ganti @pdf {} menjadi @page {}
    Jika tidak ada @pdf {}, CSS tidak diubah
    """

    if not re.search(r'@pdf\s*\{', css, re.IGNORECASE):
        return css

    # Comment semua @page {}
    css = re.sub(
        r'@page\s*\{.*?\}',
        lambda m: f'/* {m.group(0)} */',
        css,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Ganti @pdf -> @page
    css = re.sub(
        r'@pdf\s*\{',
        '@page {',
        css,
        flags=re.IGNORECASE,
    )

    return css

def _process_entry(
    html: str,
    output: Literal["pdf", "jpeg", "jpg", "png"] = "pdf",
    timeout: int = 30
) -> bytes:

    with sync_playwright() as p:
        browser = p.chromium.launch(args=BASE_ARGS)

        context = browser.new_context()
        page = context.new_page()

        try:
            page.set_content(html, timeout=timeout * 1000)
            page.wait_for_load_state("networkidle")

            if output in ["jpeg", "png"]:
                el = page.locator(".print-format")

                if el.count() < 1:
                    raise ValueError(
                        "Element .print-format tidak ditemukan untuk screenshot"
                    )

                result = el.first.screenshot(type=output)

            else:
                result = page.pdf(
                    print_background=False,
                    prefer_css_page_size=True
                )

            return result

        finally:
            page.close()
            context.close()
            browser.close()

def render(
    html: str,
    output: Literal["pdf", "jpeg", "png"] = "pdf",
    *,
    timeout: int = 30,
    options: Optional[dict] = None,
) -> bytes:
    """

    Parameters:
        html    : full HTML document
        output  : pdf | jpeg | png
        timeout : seconds
        options : playwright pdf options
    """

    html = scrub_urls(html)
    html = inline_private_images(html)
    html = normalize_pdf_page_css(html)

    return _process_entry(
        html=html,
        output=output,
        timeout=timeout
    )
