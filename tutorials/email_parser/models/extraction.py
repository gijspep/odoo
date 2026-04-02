from odoo import exceptions, fields, models


class Extraction(models.Model):
    _name = "parser.extraction"
    _description = "Binds nominations extracted from a single email job"
    _rec_name = "job_id"
    job_id = fields.Char()
    email_from = fields.Char()
    subject = fields.Char()
    nominations_summary = fields.Text()
    previous_cargoes_summary = fields.Text()
    state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed")],
        default="draft",
        required=True,
    )
    nominations = fields.One2many(
        comodel_name="parser.nomination",
        inverse_name="extraction_id",
    )
    unmatched_previous_cargo_ids = fields.One2many(
        comodel_name="parser.previous_cargo",
        inverse_name="extraction_id",
    )

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise exceptions.UserError("Only draft extractions can be confirmed.")
            rec.state = "confirmed"
