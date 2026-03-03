__version__ = "0.0.1"

import frappe
from onesender.pdf_generator.browser import render

def generate(print_format, html, options, output, pdf_generator=None):
    if pdf_generator == "tekma":
        return _tekma(print_format, html, options, output, pdf_generator)
    return None

def _tekma(print_format, html, options, output, pdf_generator=None):
    """
    Frappe PDF generator hook (SYNC)
    Must return bytes or None
    """

    if pdf_generator != "tekma":
        return None

    frappe.logger().info("Rendering PDF using Tekma (Playwright)")

    bytes = render(
        html,
        output
    )

    return bytes

def _wkhtmltopdf(print_format, html, options, output, pdf_generator=None):
    """
    Frappe patch default PDF generator hook (SYNC)
    Must return bytes or None
    """

    if pdf_generator != "wkhtmltopdf":
        return None
    
    if output == "jpeg":
        return render(html, output)
    else:
        from frappe.utils.pdf import get_pdf
        return get_pdf(html=html, options=options)
    # else if