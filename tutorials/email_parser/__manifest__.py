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
    "assets": {
        "web.assets_backend": [
            "email_parser/static/src/upload_view.js",
            "email_parser/static/src/upload_view.xml",
            "email_parser/static/src/instruct_view.js",
            "email_parser/static/src/instruct_view.xml",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/backend_views.xml",
        "views/generate_nomination_views.xml",
        "views/menus_views.xml",
        "views/portal_template.xml",
    ],
}
