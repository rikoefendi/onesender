
import re
import json
from typing import TYPE_CHECKING, Optional

import frappe
from frappe import _, cstr
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import escape_html
from frappe.utils.jinja_globals import is_rtl
from frappe.www.printview import set_link_titles, get_print_format_doc, get_rendered_template, trigger_print_script, get_font
if TYPE_CHECKING:
	from frappe.printing.doctype.print_format.print_format import PrintFormat

no_cache = 1


def get_context(context):
	"""Build context for print"""
	if not ((frappe.form_dict.doctype and frappe.form_dict.name) or frappe.form_dict.doc):
		return {
			"body": f"""
				<h1>Error</h1>
				<p>Parameters doctype and name required</p>
				<pre>{escape_html(frappe.as_json(frappe.form_dict, indent=2))}</pre>
				"""
		}

	if frappe.form_dict.doc:
		doc = frappe.form_dict.doc
	else:
		doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)

	set_link_titles(doc)

	settings = frappe.parse_json(frappe.form_dict.settings)

	letterhead = frappe.form_dict.letterhead or None

	meta = frappe.get_meta(doc.doctype)

	print_format = get_print_format_doc(None, meta=meta)

	if print_format and print_format.get("print_format_builder_beta"):
		from frappe.utils.weasyprint import get_html

		body = get_html(
			doctype=frappe.form_dict.doctype, name=frappe.form_dict.name, print_format=print_format.name
		)
		body += trigger_print_script
	else:
		body = get_rendered_template(
			doc,
			print_format=print_format,
			meta=meta,
			trigger_print=frappe.form_dict.trigger_print,
			no_letterhead=frappe.form_dict.no_letterhead,
			letterhead=letterhead,
			settings=settings,
		)

	# Include selected print format name in access log
	print_format_name = getattr(print_format, "name", "Standard")

	make_access_log(
		doctype=frappe.form_dict.doctype,
		document=frappe.form_dict.name,
		file_type="PDF",
		method="Print",
		page=f"Print Format: {print_format_name}",
	)

	return {
		"body": body,
		"print_style": get_print_style(frappe.form_dict.style, print_format),
		"comment": frappe.session.user,
		"title": frappe.utils.strip_html(cstr(doc.get_title() or doc.name)),
		"lang": frappe.local.lang,
		"layout_direction": "rtl" if is_rtl() else "ltr",
		"doctype": frappe.form_dict.doctype,
		"name": frappe.form_dict.name,
		"key": frappe.form_dict.get("key"),
		"print_format": print_format_name,
		"letterhead": letterhead,
		"no_letterhead": frappe.form_dict.no_letterhead,
		"pdf_generator": frappe.form_dict.get("pdf_generator", "wkhtmltopdf"),
	}


def get_print_style(
	style: str | None = None, print_format: Optional["PrintFormat"] = None, for_legacy: bool = False
):
	print_settings = frappe.get_doc("Print Settings")

	if not style:
		style = print_settings.print_style or ""

	context = {
		"print_settings": print_settings,
		"print_style": style,
		"font": get_font(print_settings, print_format, for_legacy),
	}
	pdf_generator = print_format.get("pdf_generator", "wkhtmltopdf")
	css = ""
	if pdf_generator == "tekma":
		css += frappe.get_template("pdf_generator/tekma.css").render(context)
	else:
		css += frappe.get_template("templates/styles/standard.css").render(context)
		if style and frappe.db.exists("Print Style", style):
			css = css + "\n" + frappe.db.get_value("Print Style", style, "css")

	# move @import to top
	for at_import in list(set(re.findall(r"(@import url\([^\)]+\)[;]?)", css))):
		css = css.replace(at_import, "")

		# prepend css with at_import
		css = at_import + css

	if print_format and print_format.css:
		css += "\n\n" + print_format.css

	return css

@frappe.whitelist()
def get_html_and_style(
	doc: str,
	name: str | None = None,
	print_format: str | None = None,
	no_letterhead: bool | None = None,
	letterhead: str | None = None,
	trigger_print: bool = False,
	style: str | None = None,
	settings: str | None = None,
):
	"""Returns `html` and `style` of print format, used in PDF etc"""

	if isinstance(name, str):
		document = frappe.get_doc(doc, name)
	else:
		document = frappe.get_doc(json.loads(doc))

	document.check_permission()

	print_format = get_print_format_doc(print_format, meta=document.meta)
	set_link_titles(document)

	try:
		html = get_rendered_template(
			doc=document,
			print_format=print_format,
			meta=document.meta,
			no_letterhead=no_letterhead,
			letterhead=letterhead,
			trigger_print=trigger_print,
			settings=frappe.parse_json(settings),
		)
	except frappe.TemplateNotFoundError:
		frappe.clear_last_message()
		html = None

	return {"html": html, "style": get_print_style(style=style, print_format=print_format)}