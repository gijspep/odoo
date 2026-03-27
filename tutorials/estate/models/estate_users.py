from odoo import fields, models


class EstateUsers(models.Model):
    _name = "res.users"
    _inherit = ["res.users"]
    property_ids = fields.One2many(
        comodel_name="estate_property",
        inverse_name="salesperson",
    )
