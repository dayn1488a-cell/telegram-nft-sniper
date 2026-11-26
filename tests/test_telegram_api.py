import unittest
from types import SimpleNamespace

from telethon import functions, types
from telethon.sessions import StringSession

from src.scanner import _json_value, _price_in_stars


class TelegramApiCompatibilityTests(unittest.TestCase):
    def test_required_mtproto_requests_exist_and_accept_expected_fields(self):
        catalogue = functions.payments.GetStarGiftsRequest(hash=0)
        resale = functions.payments.GetResaleStarGiftsRequest(
            sort_by_price=True,
            stars_only=True,
            gift_id=123,
            attributes=[],
            offset="",
            limit=50,
        )
        app_config = functions.help.GetAppConfigRequest(hash=0)

        self.assertIsNotNone(catalogue)
        self.assertIsNotNone(resale)
        self.assertIsNotNone(app_config)

    def test_string_session_can_be_created_and_saved(self):
        session = StringSession()
        self.assertIsInstance(session.save(), str)

    def test_app_config_json_value_is_decoded(self):
        value = types.JsonObject(value=[
            types.JsonObjectValue(
                key="stars_stargift_resale_commission_permille",
                value=types.JsonNumber(value=800.0),
            )
        ])
        self.assertEqual(
            _json_value(value),
            {"stars_stargift_resale_commission_permille": 800.0},
        )

    def test_stars_resale_price_includes_nanos(self):
        gift = SimpleNamespace(resell_amount=[
            SimpleNamespace(amount=12, nanos=500_000_000),
            SimpleNamespace(amount=15, nanos=0),
        ])
        self.assertEqual(_price_in_stars(gift), 12.5)


if __name__ == "__main__":
    unittest.main()
