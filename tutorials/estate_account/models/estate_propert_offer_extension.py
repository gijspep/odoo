from typing import override

from odoo import Command, models


class PropertyOfferExtension(models.Model):
    # Standard syntax for extending a model without creating a new one
    _inherit = "estate_property_offer"

    @override
    def write(self, vals):
        # 1. Capture offers that MIGHT be accepted
        offers_to_check = self.env["estate_property_offer"]
        if vals.get("status") == "accepted":
            offers_to_check = self.filtered(lambda o: o.status != "accepted")

        # 2. Let the base class handle property state and auto-refusing sibling offers
        res = super().write(vals)

        # 3. VERIFY the status after super() to prevent invoicing auto-refused offers
        offers_to_invoice = offers_to_check.filtered(lambda o: o.status == "accepted")

        for record in offers_to_invoice:
            self.env["account.move"].sudo().create(
                {
                    "partner_id": record.partner_id.id,
                    "move_type": "out_invoice",
                    "line_ids": [
                        Command.create(
                            {
                                "name": record.property_id.name,
                                "quantity": 1,
                                "price_unit": record.price * 0.06,
                            }
                        ),
                        Command.create(
                            {
                                "name": "Administrative Fees",
                                "quantity": 1,
                                "price_unit": 100.00,
                            }
                        ),
                    ],
                }
            )

        return res
