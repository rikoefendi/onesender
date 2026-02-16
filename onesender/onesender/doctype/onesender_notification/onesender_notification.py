"""Notification."""

import frappe

from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.utils.jinja import render_template
from frappe.utils import add_to_date, nowdate

class OnesenderNotification(Document):
    """Notification."""

    # def validate(self):
    #     """Validate."""
    #     if self.notification_type == "DocType Event":
    #         fields = frappe.get_doc("DocType", self.reference_doctype).fields
    #         if not any(field.fieldname == self.field_name for field in fields): # noqa
    #             frappe.throw(_("Field name {0} does not exists").format(self.field_name))

    def get_phone_from_recipients(self, doc = None):
        recipients = []
        for recipient in self.recipients:
            if recipient:
                if recipient.is_field and doc:
                    fp = doc.get(recipient.phone)
                    if fp:
                        recipients.append(fp)
                        
                elif not recipient.is_field:
                    recipients.append(recipient.phone)
        return list(set(recipients))
    
    def trigger_notify_scheduler(self) -> dict:
        """Specific to API endpoint Server Scripts."""
        if self.condition:
            safe_exec(
                self.condition, get_safe_globals(), dict(doc=self)
            )
            data_list = self.get("_data_list") or []
            for dl in data_list:
                doc = frappe.get_doc(self.reference_doctype, dl.get("name"))
                recipients = self.get_phone_from_recipients(doc)
                if not len(recipients):
                    continue
                phone = ",".join(recipients)
                self.notify_message(doc,phone_no=phone, ignore_condition=True)
            return dict(doc=self)
        

        recipients = self.get_phone_from_recipients()
        phone = ",".join(recipients)
        self.notify_message(phone_no=phone, ignore_condition=True)
        return dict(doc=self)
    
    def trigger_notify_event(self, doc: Document):
        recipients = self.get_phone_from_recipients(doc)
        if not len(recipients):
            return
        phone = ",".join(recipients)
        self.notify_message(doc, phone_no=phone)


    def notify_message(self, doc: Document = None, phone_no=None, ignore_condition=False):
        """Specific to Document Event triggered Server Scripts."""
        if self.disabled:
            return
        if doc:
            doc_data = doc.as_dict()
            if self.condition and not ignore_condition:
                # check if condition satisfies
                if not frappe.safe_eval(
                    self.condition, get_safe_globals(), dict(doc=doc_data)
                ):
                    return

        attach_doctype = ""
        attach_docname = ""
        if doc:
            attach_doctype = doc.doctype
            attach_docname = doc.name

        rendered_message = render_template(self.message, {"doc": doc})
        content_type = "Text"
        if self.attach_document_print == 1:
            content_type = "Document"
            if self.attach_document_print_as_image == 1:
                content_type = "Image"
        # print(self.caption)
        frappe.get_doc({
            "doctype": "Onesender Message",
            "to": phone_no,
            "device": self.device,
            "message": rendered_message,
            "content_type": content_type,
            "attach_with_doctype": self.attach_document_print,
            "attach_doctype": attach_doctype,
            "attach_docname": attach_docname,
            "attach_document_name": render_template(self.attach_document_name, {"doc": doc}),
            "caption": render_template(self.caption, {"doc": doc}),
            "onesender_notification": self.name,
            "is_event": True
        }).insert()

    def format_number(self, number):
        """Format number."""
        if (number.startswith("+")):
            number = number[1:len(number)]

        return number
    

    def get_notifications_today(self):
        """get list of documents that will be triggered today"""
        diff_days = self.days_in
        if self.doctype_event == "Days After":
            diff_days = -diff_days

        reference_date = add_to_date(nowdate(), days=diff_days)
        reference_date_start = reference_date + " 00:00:00.000000"
        reference_date_end = reference_date + " 23:59:59.000000"

        doc_list = frappe.get_all(
            self.reference_doctype,
            fields="name",
            filters=[
                {self.reference_date: (">=", reference_date_start)},
                {self.reference_date: ("<=", reference_date_end)},
            ],
        )
        for d in doc_list:
            doc = frappe.get_doc(self.reference_doctype, d.name)
            recipients = self.get_phone_from_recipients(doc)
            phone = ",".join(recipients)
            self.notify_message(doc, phone_no=phone)
            # print(doc.name)

