import unittest
from app import app

class TestApp(unittest.TestCase):
    def test_generate_comment(self):
        tester = app.test_client(self)
        response = tester.post(
            "/generate_comment",
            json={
                "tweet": "The road to success is paved with small, consistent efforts."
            },
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
