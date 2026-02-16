# Copyright (c) 2022, Shridhar Patil and contributors
# For license information, please see license.txt
import frappe.utils
import frappe
import json
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request
from onesender.utils import get_attach_doctype_link
from frappe.utils import get_request_session

class OnesenderMessage(Document):
    """Send Onesender messages."""
    is_event: bool = False

    def validate(self):
        """validate attach"""
        if self.attach_with_doctype == 1 and self.content_type not in ["Image", "Document"]:
            self.content_type = "Document"
        if self.content_type == "Image" or self.content_type == "Document":
            throwMsg = f"Message Type: {str(self.content_type)},"
            if self.attach_with_doctype == 1 and (self.attach_doctype is None or self.attach_docname is None):
                frappe.throw(f"{throwMsg} Attach with DocType, Please Set DocType and DocName")
            elif self.attach_with_doctype != 1 and self.attach is None:
                frappe.throw(f"{throwMsg} Please Attach")
    def after_insert(self):
        """Trigger Send message."""
        self.send_message()
    def send_message(self):
        self.validate()
        # self.bd
        """Build Message"""
        # send text 
        data_text = {
            "to": self.format_number(self.to),
            "type": "text",
            "text": {
                "body": self.message
            }
        }
        data_attach = None
        if self.content_type == "Image" or self.content_type == "Document":
            data_attach = {
                "to": self.format_number(self.to),
            }
            # generate attach link
            link = ""
            filename = self.name
            if self.attach_with_doctype:
                doctype = frappe.get_doc("DocType", self.attach_doctype)
                doc = frappe.get_doc(self.attach_doctype, self.attach_docname)
                key = doc.get_document_share_key()  # noqa
                frappe.db.commit()


                attach_type = "pdf"
                if self.content_type == "Image":
                    attach_type = "png"
                
                filename = self.attach_document_name or doc.name
                link = get_attach_doctype_link(
                        doctype.name,
                        doc.name,
                        filename=filename,
                        attach_type=attach_type,
                        key=key
                    )
                
                
            if self.attach and not self.attach_with_doctype:
                filename = self.attach_document_name or self.attach.split("/")[-1]
                link += frappe.utils.get_url() + self.attach

            data_attach["type"] = self.content_type.lower()
            data_attach[self.content_type.lower()] = {
                "link": link,
                "filename": filename,
                "caption": self.caption or filename
            }
        try:
            device, online = self.get_device()
            # if device:
            #     if not online and not device.is_default:
            #         device, online = self.get_device(True)

            # else:
            #     device, online = self.get_device(True)
            if not device:
                frappe.throw("Device not setted", exc=frappe.ValidationError)

            self.notify(device, data_text)
            if data_attach is not None:
                self.notify(device, data_attach)
            self.status = "Complete"
            self.details = ""
            frappe.msgprint("Onesender: Success send message", "Onesender message", indicator="green", alert=True)
        except Exception as e:
            self.details = str(e)
            self.status = "Failed"
            self.save()
            frappe.db.commit()

            if self.is_event:
                frappe.msgprint("Onesender: " +str(e), title="Onesender Message", indicator="red", alert=True)
            else:
                frappe.throw(str(e), title="Onesender Message", exc=e)
        finally:
            # print(device.name)
            sender = ""
            if device:
                sender = f"{device.name}-{device.phone}"
            self.data = json.dumps({
                "text": data_text,
                "attach": data_attach,
                "sender": sender 
            })
            self.save()
            frappe.db.commit()
    def notify(self, device, data):
        """Notify."""
        token = device.secret
        headers = {
            "authorization": f"Bearer {token}",
        }
        response = make_post_request(
            url=f"{device.url}/api/v1/messages",
            headers=headers,
            data=json.dumps(data)
        )
        if response["code"] != 200:
            raise OnesenderError(json.dumps(response))

    def get_device(self, default = False):
        dt = "Onesender Device"
        device = None
        if default:
            device = frappe.get_all(dt, filters={"is_default": 1}, limit=1)
        else:
            device = frappe.get_doc(dt, self.device)
        if type(device) is list:
            if len(device) > 0:
                device = frappe.get_doc(dt, device[0].name)
            else:
                device = None
        if not device:
            return None, False
        return device, device.is_online
    
    def format_number(self, number):
        """Format number."""
        if number.startswith("+"):
            number = number[1 : len(number)]

        return number
    
    @staticmethod
    def clear_old_logs(days=7):
        from frappe.query_builder import Interval
        from frappe.query_builder.functions import Now

        table = frappe.qb.DocType("Onesender Message")
        frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days)) and table.status == "Complete"))


class OnesenderError(Exception):
    pass

@frappe.whitelist()
def resend_message(docname = ""):
    try:
        frappe.get_doc("Onesender Message", docname).send_message()
        return {
            "message": "Successfully resend message"
        }
    except Exception as e:
        raise e
    