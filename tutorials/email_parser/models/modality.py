from typing import Any

from odoo import fields, models

MODALITY_TYPES: Any = [
    ("SHIP", "Ship"),
    ("TRUCK", "Truck"),
    ("TRAIN", "Train"),
    ("PIPELINE", "Pipeline"),
    ("TANK", "Tank"),
    ("", ""),
]


class Modality(models.Model):
    _name = "parser.modality"
    _description = "A transport or storage modality"

    modality_type = fields.Selection(selection=MODALITY_TYPES)
    identifier = fields.Char()
    ship_name = fields.Char()
    ship_type = fields.Char()
    previous_cargo_ids = fields.One2many(
        comodel_name="parser.previous_cargo",
        inverse_name="modality_id",
    )
