from typing import Any, override

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

STATUS: Any = [
    ("accepted", "Accepted"),
    ("refused", "Refused"),
    ("pending", "Pending"),
]


class PropertyOffer(models.Model):
    _name = "estate_property_offer"
    _description = "An offer for an Estate"
    _order = "price desc"
    price = fields.Float(required=True)
    status = fields.Selection(
        copy=False,
        selection=STATUS,
        default=STATUS[2][0],
    )
    partner_id = fields.Many2one(comodel_name="res.partner", required=True)
    property_id = fields.Many2one(
        comodel_name="estate_property",
        required=True,
        ondelete="cascade",
    )
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(
        compute="_compute_deadline",
        inverse="_inverse_deadline",
        readonly=False,
    )
    property_type_id = fields.Many2one(
        comodel_name="estate_property_type",
        related="property_id.property_type_id",
        store=True,
    )

    _check_price = models.Constraint(
        "CHECK(price > 0.0)",
        "An offer price must be strictly positive",
    )

    def _check_property_available(self):
        """Raises an error if any record in the recordset is linked to a closed property."""
        # 'self' is a recordset, so we iterate through it directly
        for record in self:
            if record.property_id.state in ["sold", "cancelled"]:
                raise UserError(
                    f"Cannot create or modify offers for a {record.property_id.state} property."
                )

    @api.model_create_multi
    def create(self, vals_list):
        offers = super().create(vals_list)
        offers._check_property_available()
        # Validate AFTER creation so we can easily access the related property records
        for offer in offers:
            if offer.property_id.state == "new":
                offer.property_id.state = "offer received"

        return offers

    @override
    def write(self, vals):
        # 1. HARD BLOCK: Prevent any edits if the property is already closed
        self._check_property_available()

        # 2. Call super() to apply the actual database updates
        res = super().write(vals)

        # 3. Handle the side-effects of the status change
        if "status" in vals:
            for record in self:
                if record.status == "accepted":
                    # Refuse all other offers FIRST, while the property is still "offer received"
                    other_offers = record.property_id.property_offer_ids - record
                    other_offers.write({"status": "refused"})

                    # THEN update the parent property to "sold"
                    record.property_id.with_context(accepted_offer_bypass=True).write(
                        {
                            "state": "sold",
                            "buyer": record.partner_id.id,
                            "selling_price": record.price,
                            "active": False,
                        }
                    )

                elif record.status == "refused":
                    active_offers = record.property_id.property_offer_ids.filtered(
                        lambda o: o.status != "refused",
                    )
                    if (
                        not active_offers
                        and record.property_id.state == "offer received"
                    ):
                        record.property_id.state = "new"

        return res

    @override
    def unlink(self):
        properties = self.mapped("property_id")
        res = super().unlink()

        for prop in properties.exists():
            if prop.state == "offer received":
                active_offers = prop.property_offer_ids.filtered(
                    lambda o: o.status != "refused",
                )
                if not active_offers:
                    prop.state = "new"

        return res

    @api.depends("create_date", "validity")
    def _compute_deadline(self):
        for record in self:
            # Safely fallback to the user's current local date if not saved yet
            base_date = (
                record.create_date.date()
                if record.create_date
                else fields.Date.context_today(record)
            )
            record.date_deadline = base_date + relativedelta(days=record.validity)

    # Use the inverse method to prevent a circular dependency crash.
    # It updates the actual database record when saved, but it does NOT
    # trigger the frontend to refresh the UI to show the new value.
    def _inverse_deadline(self):
        for record in self:
            if not record.date_deadline:
                continue

            base_date = (
                record.create_date.date()
                if record.create_date
                else fields.Date.context_today(record)
            )

            diff = record.date_deadline - base_date
            record.validity = diff.days

    # Use api.onchange to instantly update the UI's virtual record while editing.
    # Without this, the UI remains stale and won't show the correct validity
    # even after the inverse method saves the accurate data to the backend.
    @api.onchange("date_deadline")
    def _onchange_date_deadline(self):
        """Forces the UI to instantly update 'validity' when 'date_deadline' is edited."""
        if self.date_deadline:
            base_date = (
                self.create_date.date()
                if self.create_date
                else fields.Date.context_today(self)
            )

            diff = self.date_deadline - base_date
            self.validity = diff.days

    def action_reply_offer(self):
        for record in self:
            accept = self.env.context.get("accept", None)
            if accept is None:
                continue

            # Changing the status here automatically triggers the write() method
            if accept:
                record.status = "accepted"
            else:
                record.status = "refused"

        return True
