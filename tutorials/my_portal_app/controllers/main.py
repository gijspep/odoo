from odoo import http
from odoo.http import request


class MyPortalController(http.Controller):
    # This creates the route. e.g., http://localhost:8069/my-portal
    @http.route("/my-portal", type="http", auth="public", website=True)
    def portal_landing_page(self, **kwargs):
        # This tells Odoo to render our specific XML template
        return request.render("my_portal_app.standalone_portal_template", {})
