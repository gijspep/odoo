from odoo.tests.common import TransactionCase


class TestModalityMerge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestModalityMerge, cls).setUpClass()

        cls.target_modality = cls.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "VESSEL",
                "identifier": "TARGET_IMO",
                "ship_name": "Target Ship",
            }
        )

        cls.env["parser.modality.alias"].create(
            [
                {
                    "modality_id": cls.target_modality.id,
                    "alias_type": "identifier",
                    "value": "TARGET_ALIAS_IMO",
                },
                {
                    "modality_id": cls.target_modality.id,
                    "alias_type": "name",
                    "value": "Target Alias Name",
                },
            ]
        )

    def _create_dummy_source(self, identifier, ship_name):
        """Helper now requires unique inputs to prevent test-pollution intercepts."""
        return self.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "VESSEL",
                "identifier": identifier,
                "ship_name": ship_name,
            }
        )

    def test_01_identifier_merges(self):
        """Tests all permutations of merging via 'identifier'."""

        # --- 1A. WRITE to match MAIN identifier ---
        source_1 = self._create_dummy_source("TEMP_IMO_1A", "Temp Ship 1A")
        source_1.write({"identifier": "TARGET_IMO"})
        self.assertFalse(
            source_1.exists(),
            "Source should be unlinked after writing main identifier.",
        )

        # --- 1B. CREATE to match MAIN identifier ---
        new_rec_1 = self.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "VESSEL",
                "identifier": "TARGET_IMO",
                "ship_name": "New Name 1",
            }
        )
        self.assertEqual(
            new_rec_1.id,
            self.target_modality.id,
            "Creation with matching main identifier should return the target record.",
        )

        # --- 1C. WRITE to match ALIAS identifier ---
        source_2 = self._create_dummy_source("TEMP_IMO_1C", "Temp Ship 1C")
        source_2.write({"identifier": "TARGET_ALIAS_IMO"})
        self.assertFalse(
            source_2.exists(),
            "Source should be unlinked after writing alias identifier.",
        )

        # --- 1D. CREATE to match ALIAS identifier ---
        new_rec_2 = self.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "VESSEL",
                "identifier": "TARGET_ALIAS_IMO",
                "ship_name": "New Name 2",
            }
        )
        self.assertEqual(
            new_rec_2.id,
            self.target_modality.id,
            "Creation with matching alias identifier should return the target record.",
        )

    def test_02_ship_name_merges(self):
        """Tests all permutations of merging via 'ship_name'."""

        # --- 2A. WRITE to match MAIN ship_name ---
        source_1 = self._create_dummy_source("TEMP_IMO_2A", "Temp Ship 2A")
        source_1.write({"ship_name": "Target Ship"})
        self.assertFalse(
            source_1.exists(), "Source should be unlinked after writing main ship_name."
        )

        # --- 2B. CREATE to match MAIN ship_name ---
        new_rec_1 = self.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "BARGE",
                "identifier": "NEW_IMO_1",
                "ship_name": "Target Ship",
            }
        )
        self.assertEqual(
            new_rec_1.id,
            self.target_modality.id,
            "Creation with matching main ship_name should return the target record.",
        )

        # --- 2C. WRITE to match ALIAS ship_name ---
        source_2 = self._create_dummy_source("TEMP_IMO_2C", "Temp Ship 2C")
        source_2.write({"ship_name": "Target Alias Name"})
        self.assertFalse(
            source_2.exists(),
            "Source should be unlinked after writing alias ship_name.",
        )

        # --- 2D. CREATE to match ALIAS ship_name ---
        new_rec_2 = self.env["parser.modality"].create(
            {
                "modality_type": "SHIP",
                "ship_type": "BARGE",
                "identifier": "NEW_IMO_2",
                "ship_name": "Target Alias Name",
            }
        )
        self.assertEqual(
            new_rec_2.id,
            self.target_modality.id,
            "Creation with matching alias ship_name should return the target record.",
        )
