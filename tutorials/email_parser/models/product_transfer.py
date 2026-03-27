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

    nomination_id = fields.Many2one(comodel_name="parser.nomination", ondelete="cascade")

    source_modality = fields.Many2one(comodel_name="parser.modality")
    destination_modality = fields.Many2one(comodel_name="parser.modality")

    product_name = fields.Char(required=True)
    unit_of_measurement = fields.Selection(selection=UNITS_OF_MEASUREMENT, required=True)
    amount = fields.Float(required=True)
    customs_type = fields.Selection(selection=CUSTOMS_TYPES)
    country_of_origin = fields.Char()
