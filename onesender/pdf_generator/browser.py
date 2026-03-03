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


def normalize_pdf_page_css(styles: str) -> str:
    """
    Jika ada @pdf {}:
      - Comment semua @page {}
      - Ganti @pdf {} menjadi @page {}
    Jika tidak ada @pdf {}, CSS tidak diubah
    """
    for index, css in enumerate(styles):

        if not re.search(r'@pdf\s*\{', css, re.IGNORECASE):
            continue
    
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
        styles[index] = css
    return styles

def _process_entry(
    html: str,
    output: Literal["pdf", "jpeg"] = "pdf",
    timeout: int = 30
) -> bytes:

    with sync_playwright() as p:
        browser = p.chromium.launch(args=BASE_ARGS)

        context = browser.new_context()
        page = context.new_page()

        try:
            page.set_content(html, timeout=timeout * 1000)
            page.wait_for_load_state("networkidle")

            if output in ["jpeg"]:
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
    output: Literal["pdf", "jpeg"] = "pdf",
    *,
    timeout: int = 30,
    options: Optional[dict] = None,
) -> bytes:
    """

    Parameters:
        html    : full HTML document
        output  : pdf | jpeg
        timeout : seconds
        options : playwright pdf options
    """

    html = scrub_urls(html)
    html = inline_private_images(html)

    styles = extract_style_blocks(html)
    if output != "jpeg":
        styles = normalize_pdf_page_css(styles)
    styles = watermark(styles, mode=output)
    html = replace_style_blocks(html, styles)
    return _process_entry(
        html=html,
        output=output,
        timeout=timeout
    )


# Watermarks engine

def parse_watermark_blocks(css_text):
    pattern = r'@watermark-([a-zA-Z0-9_-]+)\s*\{([^}]*)\}'
    matches = re.findall(pattern, css_text, re.DOTALL)

    blocks = []

    for target, content in matches:
        props = {}
        for line in content.split(";"):
            if ":" in line:
                k, v = line.split(":", 1)
                props[k.strip()] = v.strip().strip('"')
        blocks.append({
            "target": target.strip(),
            "props": props
        })

    # remove watermark blocks from original CSS
    cleaned_css = re.sub(pattern, '', css_text, flags=re.DOTALL)

    return cleaned_css, blocks

def extract_class_properties(css_text, class_name):
    pattern = rf'\{class_name}\s*\{{([^}}]*)\}}'
    match = re.search(pattern, css_text, re.DOTALL)

    if not match:
        return {}

    props = {}
    for line in match.group(1).split(";"):
        if ":" in line:
            k, v = line.split(":", 1)
            props[k.strip()] = v.strip()

    return props

def generate_watermark_css(base_props, override_props, mode="pdf"):
    props = base_props.copy()
    props.update(override_props)

    text = props.pop("text", "")
    selector = props.pop("selector", "body::before")

    css_lines = []

    for k, v in props.items():
        css_lines.append(f"{k}: {v};")

    block = f"""
    {selector} {{
        content: "{text}";
        {' '.join(css_lines)}
    }}
    """

    if mode == "pdf":
        return f"@media print {{{block}}}"
    return block


def extract_style_blocks(html: str):
    pattern = r"<style[^>]*>(.*?)</style>"
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    return matches

def replace_style_blocks(html: str, new_styles: list[str]):
    pattern = r"<style[^>]*>.*?</style>"
    return re.sub(pattern, lambda m: f"<style>{new_styles.pop(0)}</style>", html, flags=re.DOTALL | re.IGNORECASE)

def watermark(styles: str, mode="pdf"):
    if mode != "pdf":
        mode = "image"

    processed_styles = []

    for css_text in styles:
        cleaned_css, blocks = parse_watermark_blocks(css_text)
        final_watermark_css = ""

        for block in blocks:
            if block["target"] != mode:
                continue

            props = block["props"]

            if "use" in props:
                class_props = extract_class_properties(cleaned_css, props["use"])
                class_props.update(props)
                props = class_props

            final_watermark_css += generate_watermark_css(props, class_props, mode=mode)

        processed_styles.append(cleaned_css + final_watermark_css)

    return processed_styles


