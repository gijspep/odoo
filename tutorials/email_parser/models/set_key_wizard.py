from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.email_parser.crypto import encrypt_key


class SetKeyWizard(models.TransientModel):
    _name = "parser.set_key.wizard"
    _description = "Set Parser API Key"

    key_name = fields.Char(required=True, string="Key Name")
    raw_key_hex = fields.Char(required=True, string="AES Key (hex)")
    password = fields.Char(required=True, string="Password")
    confirm_password = fields.Char(required=True, string="Confirm Password")

    def action_save_key(self):
        self.ensure_one()

        if self.password != self.confirm_password:
            raise UserError("Passwords do not match.")

        try:
            raw_key = bytes.fromhex(self.raw_key_hex.strip())
        except ValueError:
            raise UserError("Invalid hex format. The key must be a valid hexadecimal string.")

        if len(raw_key) not in (16, 24, 32):
            raise UserError(
                f"Key length is {len(raw_key)} bytes. Must be 16, 24, or 32 bytes "
                f"(32, 48, or 64 hex characters)."
            )

        encrypted, salt, nonce = encrypt_key(raw_key, self.password)

        self.env["parser.api_key"].create(
            {
                "key_name": self.key_name,
                "encrypted_key": encrypted,
                "salt": salt,
                "nonce": nonce,
            }
        )

        return {"type": "ir.actions.act_window_close"}
