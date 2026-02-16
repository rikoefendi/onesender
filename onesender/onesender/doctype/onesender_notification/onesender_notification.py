import re
import frappe

from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.utils.jinja import render_template
from frappe.utils import add_to_date, nowdate


class OnesenderNotification(Document):

    def format_number(self, number: str) -> str:
        if not number:
            return None

        number = number.strip()

        if number.startswith("+"):
            number = number[1:]

        return number

    def get_phone_from_recipients(self, doc=None):
        recipients = []

        for recipient in self.recipients or []:
            if not recipient:
                continue

            if recipient.is_field and doc:
                phone_value = doc.get(recipient.phone)
                if phone_value:
                    recipients.append(self.format_number(phone_value))

            elif not recipient.is_field:
                recipients.append(self.format_number(recipient.phone))

        for recipient in self._recipients or []:
            recipients.append(self.format_number(recipient))

        return list({r for r in recipients if r})

    def trigger_notify_event(self, doc: Document):
        self.notify_message(doc)

    def trigger_notify_scheduler(self) -> dict:
        if self.condition:
            # execute condition for scheduler
            safe_exec(
                self.condition,
                get_safe_globals(),
                dict(self=self, extract_phone=extract_phone),
            )

            data_list = self.get("_data_list") or []

            for dl in data_list:
                doc = frappe.get_doc(self.reference_doctype, dl.get("name"))
                self.notify_message(doc, ignore_condition=True)

            return {"doc": self}

        self.notify_message(ignore_condition=True)
        return {"doc": self}

    def notify_message(self, doc: Document = None, ignore_condition=False):
        if self.disabled:
            return

        # execute condition if exists
        if self.condition and not ignore_condition:
            safe_exec(
                self.condition,
                get_safe_globals(),
                dict(
                    self=self,
                    doc=doc.as_dict() if doc else None,
                    extract_phone=extract_phone,
                ),
            )

            # stop execution if _stop set in condition
            if self.get("_stop"):
                return

        phones = self.get_phone_from_recipients(doc)

        if not phones:
            return

        attach_doctype = doc.doctype if doc else ""
        attach_docname = doc.name if doc else ""

        rendered_message = render_template(self.message or "", {"doc": doc})

        content_type = "Text"

        if self.attach_document_print:
            content_type = (
                "Image" if self.attach_document_print_as_image else "Document"
            )

        frappe.get_doc(
            {
                "doctype": "Onesender Message",
                "to": ",".join(phones),
                "device": self.device,
                "message": rendered_message,
                "content_type": content_type,
                "attach_with_doctype": self.attach_document_print,
                "attach_doctype": attach_doctype,
                "attach_docname": attach_docname,
                "attach_document_name": render_template(
                    self.attach_document_name or "", {"doc": doc}
                ),
                "caption": render_template(self.caption or "", {"doc": doc}),
                "onesender_notification": self.name,
                "is_event": True,
            }
        ).insert(ignore_permissions=True)

    def get_notifications_today(self):
        diff_days = self.days_in

        if self.doctype_event == "Days After":
            diff_days = -diff_days

        reference_date = add_to_date(nowdate(), days=diff_days)

        reference_date_start = reference_date + " 00:00:00.000000"
        reference_date_end = reference_date + " 23:59:59.000000"

        doc_list = frappe.get_all(
            self.reference_doctype,
            fields=["name"],
            filters=[
                {self.reference_date: (">=", reference_date_start)},
                {self.reference_date: ("<=", reference_date_end)},
            ],
        )

        for d in doc_list:
            doc = frappe.get_doc(self.reference_doctype, d.name)
            self.notify_message(doc)


def extract_phone(text: str):
    if not text:
        return None

    match = re.search(r"phone\s*:\s*([0-9+]+)", text, re.IGNORECASE)

    if match:
        return match.group(1)

    return None
