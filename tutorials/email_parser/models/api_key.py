from odoo import fields, models


class ParserApiKey(models.Model):
    _name = "parser.api_key"
    _description = "Parser API Key"

    key_name = fields.Char(required=True, string="Key Name")
    encrypted_key = fields.Binary(required=True, string="Encrypted Key", attachment=False)
    salt = fields.Binary(required=True, string="Salt", attachment=False)
    nonce = fields.Binary(required=True, string="Nonce", attachment=False)
