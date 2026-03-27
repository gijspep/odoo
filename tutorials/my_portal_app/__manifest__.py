{
    "name": "My Custom Portal",
    "version": "1.0",
    "summary": "A standalone landing page and web portal",
    "category": "Website",
    "depends": ["base", "web"],  # 'web' gives us access to basic web core features
    "data": [
        "views/portal_template.xml",
    ],
    "application": True,  # This makes it show up as a main app in the Odoo menu
    "installable": True,
}
