import unittest
from app import app

class TestApp(unittest.TestCase):
    # def test_add_label_data_to_topic_classification(self):
    #     tester = app.test_client(self)
    #     response = tester.post(
    #         "/add_label_data_to_topic_classification",
    #         json={
    #             "post": "The road to success is paved with small, consistent efforts.",
    #             "label": "uninteresting_topic"
    #         },
    #         headers={'Content-Type': 'application/json'}
    #     )
    #     self.assertEqual(response.status_code, 200)
    # def test_interesting_topic_classification(self):
    #      tester = app.test_client(self)
    #      response = tester.post(
    #          "/interesting_topic_classification",
    #          json={
    #              "tweet": """AI agents need a lot of orchestration, authentication and tooling
 # Abacus Enterprise platform makes it super simple for you to create Agents, connect to different apps and data sources and manage / maintain permissions
# g a platform is the way to go here, trying to"""
    #          },
    #          headers={'Content-Type': 'application/json'}
    #      )
    #      self.assertEqual(response.status_code, 200)

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

    def test_generate_comment(self):
        tweet = """"3 dead-simple steps to write copy with AI:\n\n1. Pick a proven Sales Letter/Email/Hook\n2. Ask AI to turn this into a template with variables\n3. Feed the template back to ChatGPT, giving it the variables\n\nBoom.\n\nHigh-converting copy written in less than 10 minutes."""
        tester = app.test_client(self)
        response = tester.post(
            "/generate_comment_viral",
            json={
                "tweet": tweet, "author_id": 1286341463597604864
            },
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
