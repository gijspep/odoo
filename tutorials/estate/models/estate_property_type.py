from odoo import fields, models


class EstatePropertyType(models.Model):
    _name = "estate_property_type"
    _description = "The type of the property"
    _order = "sequence, name"
    name = fields.Char(required=True)
    sequence = fields.Integer(
        "Sequence",
        default=lambda self: -self.env["estate_property"].search_count([]),
    )
    property_ids = fields.One2many(
        comodel_name="estate_property",
        inverse_name="property_type_id",
    )

    offer_ids = fields.One2many(
        comodel_name="estate_property_offer",
        inverse_name="property_type_id",
    )

    offer_count = fields.Integer(compute="_compute_offer_count")

    _name_constraint = models.Constraint("UNIQUE(name)", "type must be unique")

    def _compute_offer_count(self):
        for record in self:
            available_offers = record.offer_ids.filtered(
                lambda o: o.property_id.is_available
            )
            record.offer_count = len(available_offers)

    def action_show_offers(self):
        return True
