import unittest

import app as website


class DevelopersPageTests(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()

    def test_menu_and_key_instructions_in_each_site_language(self):
        for lang, copy in website.DEVELOPER_COPY.items():
            with self.subTest(lang=lang), self.client.session_transaction() as session:
                session["lang"] = lang
            response = self.client.get("/developers")
            self.assertEqual(response.status_code, 200)
            self.assertIn(copy["menu"].encode(), response.data)
            self.assertIn(copy["steps_title"].encode(), response.data)
            self.assertIn(b"X-API-Key", response.data)
            self.assertIn(f"/developer?lang={lang.split('-')[0]}".encode(), response.data)
        home = self.client.get("/")
        self.assertIn(b'href="/developers"', home.data)


if __name__ == "__main__":
    unittest.main()
