from typing_extensions import override

# not allowed to import here, odoo goes crazy but keep it for easy access to type checking
# from addons.account.models.account_move import AccountMove
from odoo import fields, models
from odoo.orm.commands import Command


class InheritedProperty(models.Model):
    _inherit = ["estate_property"]
    _name = "estate_property"

    @override
    def action_set_state(self):
        # account_move = self.env["account.move"].create(
        #     [
        #         {
        #             "partner_id": self.buyer,
        #             "move_type": "out_invoice",
        #             "line_ids": [
        #                 Command.create(
        #                     {
        #                         "name": self.name,
        #                         "quantity": 1,
        #                         "price_unit": self.selling_price,
        #                     },
        #                 ),
        #             ],
        #         },
        #     ],
        # )
        # print(account_move)
        return super().action_set_state()
