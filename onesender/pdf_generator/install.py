import click
import subprocess
import sys
import shutil
import os

from typing import Literal

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.synchronization import filelock

from onesender.pdf_generator.custom_fields import CUSTOM_FIELDS

# ==========================================================
# Version check
# ==========================================================

def check_frappe_version():
	def major_version(v: str) -> str:
		return v.split(".")[0]

	frappe_version = major_version(frappe.__version__)
	if int(frappe_version) >= 15:
		return

	click.secho(
		f"You're attempting to install Print Designer with Frappe version {frappe_version}. "
		"This is not supported. Please use Frappe v15 or develop branch.",
		fg="red",
	)
	raise SystemExit(1)


def before_install():
	check_frappe_version()


def after_install():
	setup_custom_fields()
	setup_playwright()
	set_pdf_generator_option("add")

def setup_custom_fields():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)

# ==========================================================
# Playwright setup
# ==========================================================

@filelock("pdf_generator_playwright_setup", timeout=60, is_global=True)
def setup_playwright():
	python = sys.executable
	# ----------------------------------------------------------
	# Resolve CLI
	# ----------------------------------------------------------
	playwright_cmd = resolve_playwright_cmd(python)
	
	if is_playwright_installed(python) and is_chromium_installed(playwright_cmd):
		frappe.logger().info("Playwright + Chromium already installed. Skipping setup.")
		return
	# ----------------------------------------------------------
	# 1. Python package
	# ----------------------------------------------------------
	if not is_playwright_installed(python):
		frappe.logger().info("Installing python package: playwright")
		subprocess.check_call([
			python, "-m", "pip", "install",
			"--upgrade",
			"--disable-pip-version-check",
			"playwright",
		])
	else:
		frappe.logger().info("Playwright python package already installed")


	# ----------------------------------------------------------
	# 2. Chromium browser
	# ----------------------------------------------------------
	if not is_chromium_installed(playwright_cmd):
		frappe.logger().info("Installing Playwright Chromium")
		subprocess.check_call(playwright_cmd + ["install", "chromium"])
	else:
		frappe.logger().info("Playwright Chromium already installed")

	# ----------------------------------------------------------
	# 3. OS dependencies (best effort)
	# ----------------------------------------------------------
	if should_install_deps():
		try:
			subprocess.check_call(playwright_cmd + ["install-deps"])
		except Exception as e:
			frappe.logger().warning(
				f"Playwright install-deps skipped: {e}"
			)

	frappe.logger().info("Playwright setup finished")


# ==========================================================
# Helpers
# ==========================================================

def is_playwright_installed(python):
	try:
		subprocess.check_output(
			[python, "-m", "pip", "show", "playwright"],
			stderr=subprocess.DEVNULL
		)
		return True
	except subprocess.CalledProcessError:
		return False


def resolve_playwright_cmd(python):
	if shutil.which("playwright"):
		return ["playwright"]
	return [python, "-m", "playwright"]


def is_chromium_installed(playwright_cmd):
	try:
		output = subprocess.check_output(
			playwright_cmd + ["show-browsers"],
			stderr=subprocess.DEVNULL,
			text=True
		)
		return "chromium" in output.lower()
	except Exception:
		return False


def should_install_deps():
	return not os.path.exists("/.dockerenv")


# ==========================================================
# Print Format integration
# ==========================================================

def set_pdf_generator_option(action: Literal["add", "remove"]):
	field = frappe.get_meta("Print Format").get_field("pdf_generator")
	if not field:
		return

	options = (field.options or "").split("\n")

	if action == "add" and "tekma" not in options:
		options.append("tekma")

	if action == "remove" and "tekma" in options:
		options.remove("tekma")

	make_property_setter(
		"Print Format",
		"pdf_generator",
		"options",
		"\n".join(options),
		"Text",
		validate_fields_for_doctype=False,
	)
