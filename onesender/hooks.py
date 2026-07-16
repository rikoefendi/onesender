app_name = "onesender"
app_title = "Onesender"
app_publisher = "MKB"
app_description = "Frappe integration Onesender(Wa Api Gateway)"
app_email = "web.madinakebab@gmail.com"
app_license = "unlicense"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "onesender",
# 		"logo": "/assets/onesender/logo.png",
# 		"title": "Frappe Onesender",
# 		"route": "/frappe_os"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/onesender/css/onesender.css"
app_include_js = ["/assets/onesender/js/attach.js", "/assets/onesender/js/list_view.js"]

# Document Events
# ---------------
# Hook on document methods and events


doc_events = {
    "*": {
        "before_insert": "onesender.utils.run_server_script_for_doc_event",
        "after_insert": "onesender.utils.run_server_script_for_doc_event",
        "before_validate": "onesender.utils.run_server_script_for_doc_event",
        "validate": "onesender.utils.run_server_script_for_doc_event",
        "on_update": "onesender.utils.run_server_script_for_doc_event",
        "before_submit": "onesender.utils.run_server_script_for_doc_event",
        "on_submit": "onesender.utils.run_server_script_for_doc_event",
        "before_cancel": "onesender.utils.run_server_script_for_doc_event",
        "on_cancel": "onesender.utils.run_server_script_for_doc_event",
        "on_trash": "onesender.utils.run_server_script_for_doc_event",
        "after_delete": "onesender.utils.run_server_script_for_doc_event",
        "before_update_after_submit": "onesender.utils.run_server_script_for_doc_event",
        "on_update_after_submit": "onesender.utils.run_server_script_for_doc_event"
    }
}


# Scheduled Tasks
# ---------------
scheduler_events = {
    "cron": {
        "* * * * *": [
            "onesender.utils.trigger_onesender_notifications_cron",
        ],
        "*/5 * * * *":[
            "onesender.utils.trigger_device_connection_check"
        ]
    },
    "daily":[
        "onesender.utils.trigger_onesender_notification_today"
    ]
}

# PDF Generator
page_renderer = "onesender.pdf_generator.page_renderer.PageRenderer"

pdf_generator = "onesender.pdf_generator.generate"
before_install = "onesender.pdf_generator.install.before_install"
after_install = "onesender.pdf_generator.install.after_install"
before_uninstall = "onesender.pdf_generator.uninstall.before_uninstall"

page_js = {"print" : "pdf_generator/print.js"}

jinja = {
    "methods": ["onesender.utils.get_sales_person", "onesender.utils.get_sales_persons"],
}