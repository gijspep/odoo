from odoo import fields, models


class PropertyTag(models.Model):
    _name = "estate_property_tag"
    _description = "A tag for the Estate"
    _order = "name"
    name = fields.Char(required=True)
    color = fields.Integer()
    _name_constraint = models.Constraint("UNIQUE(name)", "type must be unique")
