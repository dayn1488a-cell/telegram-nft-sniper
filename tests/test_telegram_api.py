import unittest

from telethon import functions
from telethon.sessions import StringSession


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
        saved = session.save()
        self.assertIsInstance(saved, str)


if __name__ == "__main__":
    unittest.main()
