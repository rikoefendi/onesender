# OneSender

OneSender is a Frappe application providing:

1.  WhatsApp API integration
2.  Chromium-based PDF and image generation

This app is designed for ERPNext / Frappe environments and replaces
legacy wkhtmltopdf rendering with a modern Playwright (Chromium) engine.

------------------------------------------------------------------------

# Features

## 1. WhatsApp Integration

-   Send WhatsApp messages via API gateway
-   Designed for automation inside Frappe
-   Can be used in:
    -   DocType events
    -   Server scripts
    -   Scheduled jobs
    -   Custom API endpoints

------------------------------------------------------------------------

## 2. PDF Generator (Chromium Engine)

Location: onesender/pdf_generator/

Capabilities:

-   Generate PDF
-   Generate PNG
-   Generate JPEG
-   Full modern CSS support (Flexbox, Grid)
-   Custom `@pdf {}` CSS rule support

This engine does NOT rely on wkhtmltopdf.

------------------------------------------------------------------------

# Installation

Inside your bench:

bench get-app https://github.com/rikoefendi/onesender --branch main
bench install-app onesender

------------------------------------------------------------------------

# Playwright Requirement (For PDF Engine)

Install Playwright:

pip install playwright playwright install

Chromium will be downloaded automatically.

------------------------------------------------------------------------

# Architecture

## WhatsApp Flow

Frappe Event → OneSender → External WhatsApp API → Message Delivery

## PDF Flow

Frappe HTML → onesender.pdf_generator.generate() → Chromium → PDF/Image
bytes

------------------------------------------------------------------------

# Important Notes

-   `frappe.print_settings` is NOT used.
-   Margins, page size, header, and footer must be defined using CSS.
-   wkhtmltopdf settings are ignored.
-   Always define page layout using `@page` or `@pdf`.

------------------------------------------------------------------------

# CSS Example

```{=html}
<style>
@pdf {
  size: A4 portrait;
  margin: 8mm;
}

body {
  font-family: Arial, sans-serif;
  font-size: 12px;
}
</style>
```

------------------------------------------------------------------------

# Output Types

  Type   Method
  ------ ----------------------
  PDF    Chromium PDF engine
  PNG    Full-page screenshot
  JPEG   Full-page screenshot

------------------------------------------------------------------------

# Production Recommendations

-   Ensure HTML is self-contained.
-   Explicitly define margins and page size.
-   Test memory usage for large documents.
-   Run Playwright in a controlled server environment.

------------------------------------------------------------------------

# License

Private and proprietary. See LICENSE file.