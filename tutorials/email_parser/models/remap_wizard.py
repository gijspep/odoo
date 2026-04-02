from odoo import api, fields, models
from odoo.exceptions import UserError


class RemapCompanyWizard(models.TransientModel):
    _name = "parser.remap.company.wizard"
    _description = "Remap a company role on a nomination"

    nomination_id = fields.Many2one(
        "parser.nomination", required=True, ondelete="cascade"
    )
    field_name = fields.Char(required=True)

    # ---------------------------------------------------------
    # LEFT SIDE: Current (Old) Company
    # ---------------------------------------------------------
    old_company_id = fields.Many2one("parser.company", string="Current Company")

    # Swapped from 'related' to 'compute'
    old_name = fields.Char(compute="_compute_old_name", string="Name")

    @api.depends("old_company_id")
    def _compute_old_name(self):
        for rec in self:
            # The backend ORM effortlessly crosses the _inherits boundary
            rec.old_name = rec.old_company_id.name if rec.old_company_id else ""

    save_alias = fields.Boolean(default=False, string="Save old name as alias")
    delete_old = fields.Boolean(string="Delete Old Company")

    # ---------------------------------------------------------
    # RIGHT SIDE: Target (New) Company
    # ---------------------------------------------------------
    new_company_id = fields.Many2one("parser.company", string="Select Existing")
    new_name = fields.Char(string="Target Name")

    @api.onchange("new_company_id")
    def _onchange_new_company_id(self):
        if self.new_company_id:
            self.new_name = self.new_company_id.name

    def action_apply(self):
        self.ensure_one()
        old = self.old_company_id
        is_global_merge = self.save_alias

        if not self.new_name:
            raise UserError("Please specify a target company name.")

        target = False

        # 1. Did the user select an existing company and leave the name unchanged?
        if self.new_company_id and self.new_name == self.new_company_id.name:
            target = self.new_company_id
        else:
            target = old._find_matching_company(self.new_name)

            if not target:
                if is_global_merge:
                    # Capture old name before overwriting
                    alias_name = old.name
                    # Rename old record in place (no match found, so write() proceeds normally)
                    old.write({"name": self.new_name})
                    old._ensure_aliases(alias_name)
                    target = old
                else:
                    # LOCAL UPDATE: Create a new record
                    target = self.env["parser.company"].create({"name": self.new_name})

        # ---------------------------------------------------------
        # 2. Relink Nomination & Cleanup
        # ---------------------------------------------------------
        if old == target:
            # Renamed in place — nomination still points to the same record
            pass
        elif is_global_merge:
            # Merge old into a different target; _merge_into_target redirects all m2o refs
            alias_name = old.name
            old._merge_into_target(target, alias_name)
        else:
            # Local replacement: update only this nomination's field
            self.nomination_id.write({self.field_name: target.id})

            if self.delete_old:
                if self._is_company_in_use_elsewhere(old):
                    raise UserError(
                        f"Cannot delete '{old.name}'. It is currently linked to "
                        "other nominations or records."
                    )
                old.unlink()

        return {"type": "ir.actions.act_window_close"}

    def _is_company_in_use_elsewhere(self, company):
        """Checks if the company is used anywhere in the database."""
        m2o_fields = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("relation", "=", "parser.company"),
                    ("ttype", "=", "many2one"),
                    ("store", "=", True),
                ]
            )
        )

        for field in m2o_fields:
            if field.model in self.env:
                count = (
                    self.env[field.model]
                    .sudo()
                    .search_count([(field.name, "=", company.id)])
                )
                if count > 0:
                    return True
        return False


class RemapModalityWizard(models.TransientModel):
    _name = "parser.remap.modality.wizard"
    _description = "Remap a modality on a product transfer"

    product_transfer_id = fields.Many2one(
        "parser.product_transfer", required=True, ondelete="cascade"
    )
    field_name = fields.Char(required=True)

    # ---------------------------------------------------------
    # LEFT SIDE: Current (Old) Modality
    # ---------------------------------------------------------
    old_modality_id = fields.Many2one("parser.modality", string="Current Modality")
    old_modality_type = fields.Selection(
        related="old_modality_id.modality_type", string="Type"
    )
    old_identifier = fields.Char(
        related="old_modality_id.identifier", string="Identifier"
    )
    old_ship_name = fields.Char(related="old_modality_id.ship_name", string="Ship Name")
    old_ship_type = fields.Selection(
        related="old_modality_id.ship_type", string="Ship Type"
    )

    save_name_alias = fields.Boolean(default=False, string="Save ship name as alias")
    save_identifier_alias = fields.Boolean(
        default=False, string="Save identifier as alias"
    )
    delete_old = fields.Boolean(string="Delete Old Modality")

    # ---------------------------------------------------------
    # RIGHT SIDE: Target (New) Modality
    # ---------------------------------------------------------
    new_modality_id = fields.Many2one("parser.modality", string="Select Existing")

    # Fields to hold the new values (populated by onchange or manual entry)
    new_modality_type = fields.Selection(
        selection=lambda self: (
            self.env["parser.modality"]._fields["modality_type"].selection
        ),
        string="Target Type",
        required=True,
    )
    new_identifier = fields.Char(string="Target Identifier")
    new_ship_name = fields.Char(string="Target Ship Name")
    new_ship_type = fields.Selection(
        selection=lambda self: (
            self.env["parser.modality"]._fields["ship_type"].selection
        ),
        string="Target Ship Type",
    )

    @api.onchange("new_modality_id")
    def _onchange_new_modality_id(self):
        """Populate the right-side fields when an existing modality is selected."""
        if self.new_modality_id:
            self.new_modality_type = self.new_modality_id.modality_type
            self.new_identifier = self.new_modality_id.identifier
            self.new_ship_name = self.new_modality_id.ship_name
            self.new_ship_type = self.new_modality_id.ship_type

    def action_apply(self):
        self.ensure_one()
        old = self.old_modality_id
        is_global_merge = self.save_name_alias or self.save_identifier_alias

        target = False

        # 1. Did the user select an existing modality and leave fields unchanged?
        if (
            self.new_modality_id
            and self.new_modality_type == self.new_modality_id.modality_type
            and self.new_identifier == self.new_modality_id.identifier
            and self.new_ship_name == self.new_modality_id.ship_name
        ):
            target = self.new_modality_id
        else:
            # FIX: Call _find_matching_modality ON the 'old' record so it excludes itself!
            target = old._find_matching_modality(
                self.new_identifier, self.new_ship_name, self.new_modality_type
            )

            if not target:
                if is_global_merge:
                    # 1. Capture the old values BEFORE we overwrite them
                    alias_identifier = (
                        old.identifier if self.save_identifier_alias else False
                    )
                    alias_name = old.ship_name if self.save_name_alias else False

                    # 2. Overwrite the record with the new values first
                    old.write(
                        {
                            "modality_type": self.new_modality_type,
                            "identifier": self.new_identifier,
                            "ship_name": self.new_ship_name,
                            "ship_type": self.new_ship_type,
                        }
                    )

                    # 3. NOW tell the record to store the old values as aliases.
                    # Since it now has the new name, it will see the difference and save them!
                    old._ensure_aliases(alias_identifier, alias_name)

                    target = old
                else:
                    # LOCAL UPDATE: Create a new record
                    target = self.env["parser.modality"].create(
                        {
                            "modality_type": self.new_modality_type,
                            "identifier": self.new_identifier,
                            "ship_name": self.new_ship_name,
                            "ship_type": self.new_ship_type,
                        }
                    )

        # ---------------------------------------------------------
        # 2. Relink Transfers & Cleanup
        # ---------------------------------------------------------
        if old == target:
            # We either renamed it in place, or the core deduplication intercepted
            # the local creation. No transfers need to be re-linked.
            pass
        elif is_global_merge:
            # Merge 'old' into a DIFFERENT 'target'
            alias_identifier = old.identifier if self.save_identifier_alias else False
            alias_name = old.ship_name if self.save_name_alias else False
            old._merge_into_target(target, alias_identifier, alias_name)
        else:
            # Local replacement: Update transfers in this nomination only
            nomination = self.product_transfer_id.nomination_id
            transfers_to_update = self.env["parser.product_transfer"].search(
                [("nomination_id", "=", nomination.id), (self.field_name, "=", old.id)]
            )
            transfers_to_update.write({self.field_name: target.id})

            if self.delete_old:
                if self._is_modality_in_use_elsewhere(old, transfers_to_update):
                    raise UserError(
                        f"Cannot delete '{old.label}'. It is currently linked to other "
                        "product transfers or records outside of this nomination."
                    )
                old.unlink()

        return {"type": "ir.actions.act_window_close"}

    def _is_modality_in_use_elsewhere(self, modality, ignored_transfers):
        """Checks if the modality is used anywhere in the database, ignoring the transfers we just updated."""
        m2o_fields = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("relation", "=", "parser.modality"),
                    ("ttype", "=", "many2one"),
                    ("store", "=", True),
                ]
            )
        )

        for field in m2o_fields:
            if field.model in self.env:
                domain = [(field.name, "=", modality.id)]

                # If we are checking the product_transfer model, ignore the records we are currently fixing
                if field.model == "parser.product_transfer":
                    domain.append(("id", "not in", ignored_transfers.ids))

                count = self.env[field.model].sudo().search_count(domain)
                if count > 0:
                    return True
        return False
