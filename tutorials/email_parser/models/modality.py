from odoo import api, fields, models

# Assuming these are defined elsewhere in your file as in your original code
MODALITY_TYPES = [
    ("SHIP", "Ship"),
    ("TRUCK", "Truck"),
    ("TRAIN", "Train"),
    ("PIPELINE", "Pipeline"),
    ("TANK", "Tank"),
    ("", "None"),
]
SHIP_TYPES = [("BARGE", "Barge"), ("VESSEL", "Vessel"), ("", "None")]


class Modality(models.Model):
    _name = "parser.modality"
    _description = "A transport or storage modality"
    _rec_name = "label"

    modality_type = fields.Selection(selection=MODALITY_TYPES, required=True)
    identifier = fields.Char()
    ship_name = fields.Char()
    ship_type = fields.Selection(selection=SHIP_TYPES)
    label = fields.Char(compute="_compute_label", string="Label")
    alias_ids = fields.One2many(
        comodel_name="parser.modality.alias",
        inverse_name="modality_id",
    )

    @api.depends("modality_type", "identifier", "ship_name")
    def _compute_label(self):
        for rec in self:
            parts = [x for x in [rec.modality_type, rec.identifier, rec.ship_name] if x]
            rec.label = " / ".join(parts) if parts else ""

    # ---------------------------------------------------------
    # API ENTRY POINT
    # ---------------------------------------------------------

    @api.model
    def get_or_create_from_api(self, mod_data):
        """Entry point for API payloads. Returns a single record ID."""
        if not mod_data:
            return False

        vals = {
            "modality_type": (mod_data.get("modality_type") or "").upper(),
            "identifier": mod_data.get("identifier") or False,
            "ship_name": mod_data.get("ship_name") or False,
            "ship_type": (mod_data.get("ship_type") or "").upper() or False,
        }

        # This routes through our custom create() method below
        return self.create(vals).id

    # ---------------------------------------------------------
    # CORE CRUD OVERRIDES (DEDUPLICATION LOGIC)
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Intercept creation to return existing records if a match is found."""
        records = self.env["parser.modality"]

        for vals in vals_list:
            identifier = vals.get("identifier")
            ship_name = vals.get("ship_name")
            modality_type = vals.get("modality_type")

            target = self._find_matching_modality(identifier, ship_name, modality_type)

            if target:
                target._ensure_aliases(identifier, ship_name)
                records |= target
            else:
                records |= super().create([vals])

        return records

    def write(self, vals):
        """Intercept writes to merge records if they are renamed to an existing match."""
        # Allow normal write if none of our key matching fields are changed
        if not any(key in vals for key in ["identifier", "ship_name", "modality_type"]):
            return super().write(vals)

        normal_write_records = self.env["parser.modality"]

        for rec in self:
            new_identifier = vals.get("identifier", rec.identifier)
            new_ship_name = vals.get("ship_name", rec.ship_name)
            new_mod_type = vals.get("modality_type", rec.modality_type)

            target = rec._find_matching_modality(
                new_identifier, new_ship_name, new_mod_type
            )

            if target and target.id != rec.id:
                rec._merge_into_target(target, new_identifier, new_ship_name)
            else:
                normal_write_records |= rec

        if normal_write_records:
            super(Modality, normal_write_records).write(vals)

        return True

    # ---------------------------------------------------------
    # MERGE & ALIAS HELPER METHODS
    # ---------------------------------------------------------
    def _find_matching_modality(self, identifier, ship_name, modality_type=False):
        """Searches for an existing Modality based on identifier, ship_name, or aliases."""

        # 1. Handle exact empty matches (e.g., generic Trucks with no names)
        if not identifier and not ship_name:
            if modality_type:
                return self.search(
                    [
                        ("modality_type", "=", modality_type),
                        ("identifier", "in", [False, ""]),
                        ("ship_name", "in", [False, ""]),
                    ],
                    limit=1,
                )
            return False

        targets = self.env["parser.modality"]

        # 2. Match via Main Fields
        if identifier:
            targets |= self.search([("identifier", "=", identifier)])
        if ship_name:
            targets |= self.search([("ship_name", "=ilike", ship_name)])

        # 3. Match via Aliases (Using loops to safely map records)
        if identifier:
            aliases = self.env["parser.modality.alias"].search(
                [("alias_type", "=", "identifier"), ("value", "=", identifier)]
            )
            for alias in aliases:
                targets |= alias.modality_id

        if ship_name:
            aliases = self.env["parser.modality.alias"].search(
                [("alias_type", "=", "name"), ("value", "=ilike", ship_name)]
            )
            for alias in aliases:
                targets |= alias.modality_id

        # 4. Filter out the current record to prevent merging into itself
        targets -= self

        return targets[:1] if targets else False

    def _ensure_aliases(self, identifier, ship_name):
        """Helper to create aliases if the provided values differ from the main record."""
        aliases_to_create = []

        if identifier and identifier != self.identifier:
            if not self.alias_ids.filtered(
                lambda a: a.alias_type == "identifier" and a.value == identifier
            ):
                aliases_to_create.append(
                    {
                        "modality_id": self.id,
                        "alias_type": "identifier",
                        "value": identifier,
                    }
                )

        if ship_name and ship_name.lower() != (self.ship_name or "").lower():
            if not self.alias_ids.filtered(
                lambda a: (
                    a.alias_type == "name" and a.value.lower() == ship_name.lower()
                )
            ):
                aliases_to_create.append(
                    {"modality_id": self.id, "alias_type": "name", "value": ship_name}
                )

        if aliases_to_create:
            self.env["parser.modality.alias"].create(aliases_to_create)

    def _merge_into_target(self, target, identifier, ship_name):
        """Reassigns all DB references to the target, manages aliases, and unlinks self."""
        # 1. Manage aliases on the target
        target._ensure_aliases(identifier, ship_name)

        # 2. Transfer any existing aliases attached to this record over to the target
        self.alias_ids.write({"modality_id": target.id})

        # 3. Redirect all Many2one fields pointing to this record across the ENTIRE database
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
                model_obj = self.env[field.model].sudo()
                linked_records = model_obj.search([(field.name, "=", self.id)])
                if linked_records:
                    linked_records.write({field.name: target.id})

        # 4. Delete the old, now obsolete record
        self.unlink()


class ModalityAlias(models.Model):
    _name = "parser.modality.alias"
    _description = (
        "Alternative name or identifier for a modality as received from the API"
    )

    modality_id = fields.Many2one(
        comodel_name="parser.modality",
        required=True,
        ondelete="cascade",
    )
    alias_type = fields.Selection(
        selection=[("name", "Name"), ("identifier", "Identifier")],
        required=True,
    )
    value = fields.Char(required=True)
