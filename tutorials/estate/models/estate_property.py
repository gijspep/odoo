from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

GARDEN_SELECTION: Any = [
    ("south", "South"),
    ("north", "North"),
    ("east", "East"),
    ("west", "West"),
]

STATES: Any = [
    ("new", "New"),
    ("offer received", "Offer Received"),
    ("offer accepted", "Offer Accepted"),
    ("sold", "Sold"),
    ("cancelled", "Cancelled"),
]


class Property(models.Model):
    _name = "estate_property"
    _description = "A test module for an estate property"
    _order = "id desc"
    buyer = fields.Many2one(comodel_name="res.partner", copy=False)
    salesperson = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    active = fields.Boolean(default=True)
    is_available = fields.Boolean(
        compute="_compute_is_available",
        search="_search_is_available",
        store=True,
    )
    state = fields.Selection(
        selection=STATES,
        required=True,
        copy=False,
        default=STATES[0][0],
    )
    property_type_id = fields.Many2one(
        comodel_name="estate_property_type",
        delegate=False,
    )
    property_tag_ids = fields.Many2many(comodel_name="estate_property_tag")
    property_offer_ids = fields.One2many(
        comodel_name="estate_property_offer",
        inverse_name="property_id",
    )
    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(
        copy=False,
        default=lambda self: date.today() + relativedelta(months=3),
    )
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        selection=GARDEN_SELECTION,
    )
    total_area = fields.Integer(compute="_compute_total_area")
    best_price = fields.Float(compute="_compute_best_price")

    _check_expected_price = models.Constraint(
        "CHECK(expected_price > 0)",
        "The expected price must be strictly positive",
    )
    _check_selling_price = models.Constraint(
        "CHECK(selling_price >= 0)",
        "The selling price must be positive",
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_property_complete(self):
        if any(not record.is_available for record in self):
            raise UserError("Cannot delete completed records.")

    @api.depends("state")
    def _compute_is_available(self):
        for record in self:
            record.is_available = record.state in ["new", "offer received"]

    def _search_is_available(self, operator, value):
        if value:
            return [("state", "in", ["new", "offer received"])]

        return [("state", "not in", ["new", "offer received"])]

    @api.constrains("selling_price")
    def _constrain_selling_price(self):
        for record in self:
            if record.expected_price * 0.9 >= record.selling_price:
                raise ValidationError(
                    "The selling price must be greater than 90% of the expected price."
                )

    @api.depends("garden_area", "living_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.garden_area + record.living_area

    @api.depends("property_offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(
                [offer.price for offer in record.property_offer_ids],
                default=0.0,
            )

    @api.onchange("garden")
    def _set_or_clear_garden_values(self):
        if self.garden:
            self.garden_area = self.garden_area if self.garden_area else 10
            self.garden_orientation = (
                self.garden_orientation
                if self.garden_orientation
                else GARDEN_SELECTION[1][0]
            )
        else:
            self.garden_area = None
            self.garden_orientation = None

    def write(self, vals):
        # Check if we are trying to change the state
        if "state" in vals:
            if vals.get("state") == "sold":
                if not self.env.context.get("accepted_offer_bypass"):
                    raise UserError(
                        "A property can only be sold by accepting an offer."
                    )
            for record in self:
                # If the record is already sold/cancelled, block any state changes
                if (
                    record.state in ["sold", "cancelled"]
                    and vals["state"] != record.state
                ):
                    raise UserError(
                        f"The property '{record.name}' is already {record.state}. "
                        "Its state cannot be changed further."
                    )

        # If the check passes, or we aren't changing the state, call super()
        return super().write(vals)

    def action_set_state(self):
        for record in self:
            target_state = self.env.context.get("target_state")
            if record.state in ["cancelled", "sold"]:
                raise UserError(
                    f"Cannot change to {target_state} because the listing is already {record.state}."
                )
            if target_state:
                record.state = target_state
                if target_state in ["cancelled", "sold"]:
                    record.active = False
        return True
