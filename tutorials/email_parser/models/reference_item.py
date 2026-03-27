from odoo import fields, models


class ReferenceItem(models.Model):
    _name = "parser.reference_item"
    _description = "A key/value reference belonging to a nomination"

    label = fields.Char(required=True)
    value = fields.Char(required=True)
    nomination_id = fields.Many2one(comodel_name="parser.nomination", ondelete="cascade")
