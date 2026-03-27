from odoo.exceptions import UserError
from odoo.orm.commands import Command
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


# The CI will run these tests after all the modules are installed,
# not right after installing the one defining it.
# @tagged("post_install", "-at_install")
class EstateTestCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        # add env on cls and many other things
        super(EstateTestCase, cls).setUpClass()

        cls.property_type = cls.env["estate_property_type"].create(
            {
                "name": "Test_Residential",
            },
        )

        cls.tag_cozy = cls.env["estate_property_tag"].create({"name": "Cozy"})
        cls.tag_renovated = cls.env["estate_property_tag"].create({"name": "Renovated"})
        cls.buyer = cls.env[
            "res.partner"
        ].create(
            {
                "name": "John Doe",
                "autopost_bills": "never",  # Or 'always', depending on the module's selection options
            }
        )

        # 2. If you specifically need a User (which links to a partner)
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test Agent",
                "login": "test_agent",
                "email": "test@example.com",
            },
        )

        # create the data for each tests. By doing it in the setUpClass instead
        # of in a setUp or in each test case, we reduce the testing time and
        # the duplication of code.
        cls.properties = cls.env["estate_property"].create(
            [
                {
                    "name": "test_property_1",
                    "state": "new",
                    "expected_price": 150000.0,
                    # Many2one: Assign by passing the record's ID
                    "property_type_id": cls.property_type.id,
                    # Many2many: Use Command.set() with a list of IDs
                    "property_tag_ids": [
                        Command.set([cls.tag_cozy.id, cls.tag_renovated.id])
                    ],
                    # One2many: Use Command.create() to make children on the fly
                    "property_offer_ids": [
                        Command.create(
                            {
                                "price": 240000.0,
                                "partner_id": cls.buyer.id,
                            },
                        ),
                        Command.create(
                            {
                                "price": 255000.0,
                                "partner_id": cls.buyer.id,
                            },
                        ),
                    ],
                },
                {
                    "name": "test_property_2",
                    "state": "new",
                    "expected_price": 200000.0,
                    # Many2one: Assign by passing the record's ID
                    "property_type_id": cls.property_type.id,
                    # Many2many: Use Command.set() with a list of IDs
                    "property_tag_ids": [
                        Command.set([cls.tag_cozy.id, cls.tag_renovated.id])
                    ],
                    # One2many: Use Command.create() to make children on the fly
                    "property_offer_ids": [
                        Command.create(
                            {
                                "price": 255000.0,
                                "partner_id": cls.buyer.id,
                            },
                        ),
                        Command.create(
                            {
                                "price": 170000.0,
                                "partner_id": cls.buyer.id,
                            },
                        ),
                    ],
                },
                {
                    "name": "test_property_3",
                    "state": "new",
                    "expected_price": 200000.0,
                    # Many2one: Assign by passing the record's ID
                    "property_type_id": cls.property_type.id,
                    # Many2many: Use Command.set() with a list of IDs
                    "property_tag_ids": [
                        Command.set([cls.tag_cozy.id, cls.tag_renovated.id])
                    ],
                },
            ],
        )

    def test_action_sell(self):
        """Test that everything behaves like it should when selling a property."""
        self.properties[0].property_offer_ids[0].with_context(
            accept=True
        ).action_reply_offer()

        self.assertRecordValues(
            self.properties[0],
            [{"name": "test_property_1", "state": "sold"}],
        )

        # Test for the selling price.
        with self.assertRaises(UserError):
            self.properties[1].property_offer_ids[1].with_context(
                accept=True,
            ).action_reply_offer()

        # Test to make sure not new offers can be created
        with self.assertRaises(UserError):
            self.env["estate_property_offer"].create(
                {
                    "price": 100000.0,
                    "partner_id": self.buyer.id,
                    "property_id": self.properties[0].id,
                }
            )

        # Test that we cannot set state to sold from outside the write method of the PropertyOffer
        # which uses a context variable
        with self.assertRaises(UserError):
            self.properties[2].write({"state": "sold"})

    def test_property_form(self):
        """Test that makes sure the form behaves as intended"""
        property_form = Form(self.env["estate_property"])
        self.assertEqual(property_form.garden, False)
        self.assertEqual(property_form.garden_area, False)
        self.assertEqual(property_form.garden_orientation, False)
        self.assertEqual(property_form.total_area, False)

        property_form.garden = True

        self.assertEqual(property_form.garden, True)
        self.assertNotEqual(property_form.garden_area, False)
        self.assertNotEqual(property_form.garden_orientation, False)
        self.assertNotEqual(property_form.total_area, False)

        property_form.garden = False

        self.assertEqual(property_form.garden, False)
        self.assertEqual(property_form.garden_area, False)
        self.assertEqual(property_form.garden_orientation, False)
        self.assertEqual(property_form.total_area, False)
