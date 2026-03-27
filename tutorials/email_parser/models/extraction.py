from odoo import fields, models


class Extraction(models.Model):
    _name = "parser.extraction"
    _description = "Binds nominations extracted from a single email job"

    job_id = fields.Char()
    email_from = fields.Char()
    subject = fields.Char()
    nominations_summary = fields.Text()
    companies_summary = fields.Text()
    nominations = fields.One2many(
        comodel_name="parser.nomination",
        inverse_name="extraction_id",
    )
