import unittest
from app import app

class TestApp(unittest.TestCase):
    def test_interesting_topic_classification(self):
         tester = app.test_client(self)
         response = tester.post(
             "/interesting_topic_classification",
             json={
                 "tweet": """AI agents need a lot of orchestration, authentication and tooling
The Abacus Enterprise platform makes it super simple for you to create Agents, connect to different apps and data sources and manage / maintain permissions
Using a platform is the way to go here, trying to"""
             },
             headers={'Content-Type': 'application/json'}
         )
         self.assertEqual(response.status_code, 200)

    # def test_tweet_statistics(self):
    #      tester = app.test_client(self)
    #      response = tester.post(
    #          "/tweet_statistics",
    #          json={
    #              "tweet_url": "https://x.com/MarkusOdenthal/status/1805601967076696390"
    #          },
    #          headers={'Content-Type': 'application/json'}
    #      )
    #      self.assertEqual(response.status_code, 200)

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
