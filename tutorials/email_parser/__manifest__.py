{
    "name": "email_parser module",
    "version": "1.0",
    "depends": ["base", "web", "website"],
    "author": "gijs pepping",
    "category": "Email Parser",
    "application": True,
    "installable": True,
    "license": "LGPL-3",
    "description": """
    email parser website
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/backend_views.xml",
        "views/portal_template.xml",
    ],
}
