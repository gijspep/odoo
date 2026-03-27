from cryptography.exceptions import InvalidTag

from odoo import fields, models
from odoo.exceptions import UserError

import odoo.addons.email_parser.controllers.main as portal_ctrl


class UnlockWizard(models.TransientModel):
    _name = "parser.unlock_wizard"
    _description = "Unlock Parser API Key"

    password = fields.Char(required=True, string="Password")

    def action_unlock(self):
        self.ensure_one()
        record = self.env["parser.api_key"].search([], limit=1)
        if not record:
            raise UserError("No API key configured.")
        try:
            from odoo.addons.email_parser.crypto import decrypt_key
            portal_ctrl._cached_key = decrypt_key(
                bytes(record.encrypted_key),
                bytes(record.salt),
                bytes(record.nonce),
                self.password,
            )
        except (InvalidTag, Exception):
            raise UserError("Incorrect password.")
        return {"type": "ir.actions.act_window_close"}
