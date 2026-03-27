{
    "name": "real-estate module",
    "version": "1.0",
    "depends": ["base", "web", "account"],
    "author": "gijs pepping",
    "category": "Real Estate/Brokerage",
    "application": True,
    "license": "LGPL-3",
    "description": """
    Description text
    """,
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "report/estate_property_template.xml",
        "report/estate_property_reports.xml",
        "views/estate_property_view_list.xml",
        "views/estate_property_view_form.xml",
        "views/estate_property_view_search.xml",
        "views/estate_property_offer_views.xml",
        "views/estate_property_tag_views.xml",
        "views/estate_property_views.xml",
        "views/estate_property_type_views.xml",
        "views/estate_users_extension_view.xml",
        "views/estate_menus.xml",
        "demo_data/estate_property.xml",
        "demo_data/estate_property_type.csv",
    ],
}
