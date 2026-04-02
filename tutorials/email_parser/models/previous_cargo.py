from odoo import api, fields, models


class PreviousCargo(models.Model):
    _name = "parser.previous_cargo"
    _description = "Previous Cargo"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )

    unmatched_name = fields.Char(string="Unmatched Name")
    tank_id = fields.Char()
    first_last = fields.Char()
    second_last = fields.Char()
    third_last = fields.Char()

    modality_id = fields.Many2one(
        comodel_name="parser.modality",
        ondelete="set null",
    )

    # Set when matched to the source side of a product transfer
    source_transfer_id = fields.Many2one(
        comodel_name="parser.product_transfer",
        ondelete="set null",
    )
    # Set when matched to the destination side of a product transfer
    destination_transfer_id = fields.Many2one(
        comodel_name="parser.product_transfer",
        ondelete="set null",
    )
    # Set when no modality match could be found
    extraction_id = fields.Many2one(
        comodel_name="parser.extraction",
        ondelete="set null",
    )

    @api.depends("modality_id.label", "unmatched_name")
    def _compute_name(self):
        for record in self:
            if record.modality_id:
                # Use the label from the related modality
                record.name = record.modality_id.label
            else:
                # Fall back to the raw parsed name
                record.name = record.unmatched_name
