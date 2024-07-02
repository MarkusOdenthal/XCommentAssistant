import unittest
from app import app

class TestApp(unittest.TestCase):
    def test_tweet_statistics(self):
         tester = app.test_client(self)
         response = tester.post(
             "/tweet_statistics",
             json={
                 "tweet_url": "https://twitter.com/MarkusOdenthal/status/1791014365061329301"
             },
             headers={'Content-Type': 'application/json'}
         )
         self.assertEqual(response.status_code, 200)
    # def test_generate_comment(self):
    #     tester = app.test_client(self)
    #     response = tester.post(
    #         "/generate_comment",
    #         json={
    #             "tweet": "The road to success is paved with small, consistent efforts."
    #         },
    #         headers={'Content-Type': 'application/json'}
    #     )
    #     self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
