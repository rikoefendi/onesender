"""Run on each event."""
import frappe
from frappe.core.doctype.server_script.server_script_utils import EVENT_MAP
from croniter import croniter
from datetime import datetime
from datetime import datetime, time
from croniter import croniter
 
from typing import Literal

def build_header(secret: str):
    return {
        "authorization": f"Bearer {secret}"
    }

def run_server_script_for_doc_event(doc, event):
    """Run on each event."""
    if event not in EVENT_MAP:
        return

    if frappe.flags.in_install:
        return

    if frappe.flags.in_migrate:
        return
    
    if frappe.flags.in_uninstall:
        return

    notification = get_notifications_map().get(
        doc.doctype, {}
    ).get(EVENT_MAP[event], None)
    if notification:
        # run all scripts for this doctype + event
        for notification_name in notification:
            frappe.get_doc(
                "Onesender Notification",
                notification_name
            ).trigger_notify_event(doc)


def get_notifications_map():
    """Get mapping."""
    if frappe.flags.in_patch and not frappe.db.table_exists("Onesender Notification"):
        return {}

    notification_map = {}
    enabled_onesender_notifications = frappe.get_all(
        "Onesender Notification",
        fields=("name", "reference_doctype", "doctype_event", "notification_type"),
        filters={"disabled": 0},
    )
    for notification in enabled_onesender_notifications:
        if notification.notification_type == "DocType Event":
            notification_map.setdefault(
                notification.reference_doctype, {}
            ).setdefault(
                notification.doctype_event, []
            ).append(notification.name)

    frappe.cache().set_value("onesender_notification_map", notification_map)

    return notification_map

def trigger_device_connection_check():
    devices = frappe.get_all("Onesender Device")
    for device in devices:
        frappe.get_doc("Onesender Device", device.name).check()


from croniter import croniter
from datetime import datetime, time
import frappe

def get_cron_expression_from_notification(doc):
    run_time = frappe.utils.get_time(doc.run_time) if doc.run_time else time(0, 0)
    minute = run_time.minute
    hour = run_time.hour

    freq = doc.event_frequency.lower()
    unit = doc.interval_unit or ""
    unit = unit.lower()
    every = doc.interval_every or 1

    if freq == "cron" and doc.cron_expression:
        return doc.cron_expression.strip()

    if freq == "once":
        return None
    if freq == "at regular intervals":
        # print(freq, every, unit)
        if unit == "minutes":
            return f"*/{every} * * * *"
        elif unit == "hours":
            return f"{minute} */{every} * * *"
        elif unit == "days":
            return f"{minute} {hour} */{every} * *"
        elif unit == "weeks":
            return f"{minute} {hour} * * */{every}"

    if freq == "every day":
        return f"{minute} {hour} * * *"

    if freq == "days of the week" and doc.weekday_days:
        days = ",".join(d.strip() for d in doc.weekday_days.split(",") if d.strip().isdigit())
        return f"{minute} {hour} * * {days}"

    if freq == "dates of the month" and doc.monthday_days:
        days = ",".join(d.strip() for d in doc.monthday_days.split(",") if d.strip().isdigit())
        return f"{minute} {hour} {days} * *"

    return None

def run_notification(name, run_now = False):
    now = datetime.now()
    doc = frappe.get_doc("Onesender Notification", name)
    cron_expr = get_cron_expression_from_notification(doc)
    if not cron_expr:
        return

    last_run = doc.last_run_at or now.replace(year=now.year - 1)
    cron = croniter(cron_expr, last_run)
    next_time = cron.get_next(datetime)
    if next_time <= now or run_now:
        doc.db_set("last_run_at", now)
        doc.db_set("next_run_at", next_time)
        doc.trigger_notify_scheduler()

def trigger_onesender_notifications_cron():
    
    notification_list = frappe.get_all("Onesender Notification",
        filters={"disabled": 0, "notification_type": "Scheduler Event"},)
    
    for nl in notification_list:
        try:
            run_notification(nl.name)
        except Exception as e:
            frappe.log_error("Onesender Notification Cron", f"Error in notification {nl.name}: {e}", )
            continue  # safely continue even if one fails


def trigger_onesender_notification_today():
    doc_list = frappe.get_all(
            "Onesender Notification", filters={"doctype_event": ("in", ("Days Before", "Days After")), "disabled": 0}
        )
    for d in doc_list:
        try:
            alert = frappe.get_doc("Onesender Notification", d.name)
            alert.get_notifications_today()
        except Exception as e:
            frappe.log_error("Onesender Notification Dalily", f"Error in notification {d.name}: {e}", )
            continue  # safely continue even if one fails
    return len(doc_list)

from pdf_generator.page_renderer import build_url
def get_attach_doctype_link(doctype, docname, print_format="", no_letterhead=0, key: str = None, filename : str = None, attach_type: Literal["pdf", "png"] = "pdf"):
    return build_url(doctype, docname, {
        "print_format": print_format,
        "no_letterhead": no_letterhead,
        "key": key,
        "filename": filename
    }, ext=attach_type)






