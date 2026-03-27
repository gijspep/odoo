from odoo import fields, models


class PreviousCargo(models.Model):
    _name = "parser.previous_cargo"
    _description = "Previous cargo history for a ship modality"

    modality_id = fields.Many2one(comodel_name="parser.modality", ondelete="cascade")
    name = fields.Char()
    first_last = fields.Char()
    second_last = fields.Char()
    third_last = fields.Char()
