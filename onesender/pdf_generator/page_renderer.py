import re
import json
import base64
from typing import Dict, Literal
from pypdf import PdfWriter

import frappe
from frappe.utils import get_url
from frappe.website.page_renderers.base_renderer import BaseRenderer
from frappe.www.printview import validate_print_permission
from frappe.translate import print_language
from werkzeug.wrappers import Response
from frappe.exceptions import DoesNotExistError, PermissionError
from onesender.pdf_generator.browser import render
ATTACH_PATTERN = re.compile(
    r"^/attach/[^/]+/[^/]+/[^/]+\.(pdf|jpeg)$"
)
ALLOWED_EXT = ["pdf", "jpeg"]
MIMES = {
    "pdf": "application/pdf",
    "jpeg": "image/jpeg"
}

class PageRenderer(BaseRenderer):

    def can_render(self):
        if getattr(frappe.local, "_attach_renderer_running", False):
            return False

        path = frappe.request.path
        return bool(ATTACH_PATTERN.match(path))

    def render(self):
        frappe.local._attach_renderer_running = True

        try:
            path = frappe.request.path.strip("/")
            _, doctype, options_b64, filename = path.split("/")

            name, ext = filename.rsplit(".", 1)
            if ext not in ALLOWED_EXT:
                return Response(
                    "404 Not Found",
                    status=404,
                    mimetype="text/plain"
                )

            options = decode_options(options_b64) if options_b64 else {}
            pdf_generator=options.get("pdf_generator")
            frappe.form_dict.key = options.get("key")

            # get document
            doc = frappe.get_doc(doctype, name)
            as_pdf = True
            if ext != "pdf":
                as_pdf = False
            # validate permission
            validate_print_permission(doc)

            with print_language(options.get("language")):
                bytes = frappe.get_print(
                    doctype,
                    name,
                    print_format=options.get("format"),
                    doc=doc,
                    as_pdf=as_pdf,
                    letterhead=options.get("letterhead"),
                    no_letterhead=options.get("no_letterhead"),
                    pdf_generator=pdf_generator,
                )
            if type(bytes) == str and as_pdf != True:
                bytes = render(bytes, ext)
            return Response(
                bytes,
                mimetype=MIMES[ext or "pdf"],
                headers={
                    "Content-Disposition": f'inline; filename="{name}.{ext}"'
                },
            )

        except DoesNotExistError:
            return Response(
                "404 Not Found",
                status=404,
                mimetype="text/plain"
            )

        except PermissionError:
            return Response(
                "403 Forbidden",
                status=403,
                mimetype="text/plain"
            )

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Attach Renderer Error")

            return Response(
                "500 Internal Server Error",
                status=500,
                mimetype="text/plain"
            )

        finally:
            # reset guard
            frappe.local._attach_renderer_running = False

###utils


def build_url(
    doctype: str,
    docname: str,
    options: Dict,
    ext: Literal["pdf", "jpeg"] = "pdf"
) -> str:

    if ext not in ALLOWED_EXT:
        raise ValueError("Invalid extension")

    token = encode_options(options)
    return get_url(
        f"/attach/{doctype}/{token}/{docname}.{ext}"
    )


def encode_options(options: Dict) -> str:
    raw = json.dumps(options, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_options(token: str) -> Dict:
    padding = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + padding)
    return json.loads(raw)
