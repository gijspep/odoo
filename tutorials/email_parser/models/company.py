from odoo import fields, models


class Company(models.Model):
    _name = "parser.company"
    _description = "A company referenced in nominations"

    name = fields.Char(required=True)
    role = fields.Char()
