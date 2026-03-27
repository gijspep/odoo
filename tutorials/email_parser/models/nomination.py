from odoo import fields, models


class Nomination(models.Model):
    _name = "parser.nomination"
    _description = "A single nomination extracted from an email"

    extraction_id = fields.Many2one(comodel_name="parser.extraction", ondelete="cascade")

    references = fields.One2many(
        comodel_name="parser.reference_item",
        inverse_name="nomination_id",
    )
    product_transfers = fields.One2many(
        comodel_name="parser.product_transfer",
        inverse_name="nomination_id",
    )

    arrival_date = fields.Date()
    transporter = fields.Many2one(comodel_name="parser.company")
    receiver = fields.Many2one(comodel_name="parser.company")
    sender = fields.Many2one(comodel_name="parser.company")
    agent = fields.Char()
    nomination_type = fields.Char()

    sample_required = fields.Boolean(default=False)
    inspection_before = fields.Boolean(default=False)
    inspection_after = fields.Boolean(default=False)
    certificate_of_analysis = fields.Boolean(default=False)
