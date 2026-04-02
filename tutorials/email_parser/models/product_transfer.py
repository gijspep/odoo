from typing import Any

from odoo import fields, models

UNITS_OF_MEASUREMENT: Any = [
    ("KG", "KG"),
    ("MT", "MT"),
    ("LTR", "LTR"),
    ("M3", "M3"),
    ("MG", "MG"),
]

CUSTOMS_TYPES: Any = [
    ("AGD", "AGD"),
    ("T2", "T2"),
    ("T1", "T1"),
    ("FREE CIRC.", "Free Circ."),
    ("FREE CIRCULATION", "Free Circulation"),
    ("IMA", "IMA"),
]


class ProductTransfer(models.Model):
    _name = "parser.product_transfer"
    _description = "A product transfer within a nomination"

    nomination_id = fields.Many2one(
        comodel_name="parser.nomination",
        ondelete="cascade",
    )

    source_modality = fields.Many2one(comodel_name="parser.modality")
    destination_modality = fields.Many2one(comodel_name="parser.modality")
    source_previous_cargo_ids = fields.One2many(
        comodel_name="parser.previous_cargo",
        inverse_name="source_transfer_id",
    )
    destination_previous_cargo_ids = fields.One2many(
        comodel_name="parser.previous_cargo",
        inverse_name="destination_transfer_id",
    )

    extraction_state = fields.Selection(related="nomination_id.extraction_id.state")

    product_name = fields.Char(required=True)
    unit_of_measurement = fields.Selection(
        selection=UNITS_OF_MEASUREMENT,
        required=True,
        string="UoM",
    )
    amount = fields.Float(required=True)
    customs_type = fields.Selection(selection=CUSTOMS_TYPES)
    country_of_origin = fields.Char()
