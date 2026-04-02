from odoo import api, fields, models


class Company(models.Model):
    _name = "parser.company"
    _description = "A company referenced in nominations"
    _inherits = {"res.partner": "partner_id"}
    _rec_name = "name"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    can_be_agent = fields.Boolean()
    can_be_transporter = fields.Boolean()
    alias_ids = fields.One2many(
        comodel_name="parser.company.alias",
        inverse_name="company_id",
    )

    # ---------------------------------------------------------
    # CORE CRUD OVERRIDES (DEDUPLICATION LOGIC)
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Intercept creation to return existing records if a match is found."""
        records = self.env["parser.company"]

        for vals in vals_list:
            name = vals.get("name")
            target = self._find_matching_company(name)

            if target:
                target._ensure_aliases(name)
                records |= target
            else:
                records |= super().create([vals])

        return records

    def write(self, vals):
        """Intercept writes to merge records if they are renamed to an existing match."""
        if "name" not in vals:
            return super().write(vals)

        normal_write_records = self.env["parser.company"]

        for rec in self:
            new_name = vals.get("name", rec.name)
            target = rec._find_matching_company(new_name)

            if target and target.id != rec.id:
                rec._merge_into_target(target, new_name)
            else:
                normal_write_records |= rec

        if normal_write_records:
            super(Company, normal_write_records).write(vals)

        return True

    # ---------------------------------------------------------
    # MERGE & ALIAS HELPER METHODS
    # ---------------------------------------------------------

    def _find_matching_company(self, name):
        """Search for an existing Company by name or alias (case-insensitive)."""
        if not name:
            return False
        target = self.search([("name", "=ilike", name)], limit=1)
        if not target:
            alias = self.env["parser.company.alias"].search(
                [("name", "=ilike", name)], limit=1
            )
            if alias:
                target = alias.company_id
        target -= self  # prevent matching against the current record
        return target or False

    def _ensure_aliases(self, name):
        """Create an alias if the provided name differs from the record's current name."""
        if not name or name.lower() == (self.name or "").lower():
            return
        if not self.alias_ids.filtered(lambda a: a.name.lower() == name.lower()):
            self.env["parser.company.alias"].create(
                {"company_id": self.id, "name": name}
            )

    def _merge_into_target(self, target, name):
        """Reassigns all DB references to the target, manages aliases, and unlinks self."""
        # 1. Manage aliases on the target
        target._ensure_aliases(name)

        # 2. Transfer any existing aliases attached to this record over to the target
        self.alias_ids.write({"company_id": target.id})

        # 3. Redirect all Many2one fields pointing to this record across the ENTIRE database
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
                model_obj = self.env[field.model].sudo()
                linked_records = model_obj.search([(field.name, "=", self.id)])
                if linked_records:
                    linked_records.write({field.name: target.id})

        # 4. Delete the old, now obsolete record
        self.unlink()


class CompanyAlias(models.Model):
    _name = "parser.company.alias"
    _description = "Alternative names for a company as received from the API"

    company_id = fields.Many2one(
        comodel_name="parser.company",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(required=True)
