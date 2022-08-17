import unittest
import pyraindropio


class Tester(unittest.TestCase):
    def test_something(self):
        session = pyraindropio.Session(access_token="f09c0373-0fa5-4fae-a160-90247c4cef56", max_threads=8)
        for collection in (session.get_collection_by_id(collection_id) for collection_id in ['24904767']):
            for raindrop in collection.fetch_all_raindrops():
                for highlight in raindrop:
                    self.assertTrue(True)
        
        self.assertTrue(True)


    def test_something_else(self):
        session = pyraindropio.Session(access_token="f09c0373-0fa5-4fae-a160-90247c4cef56", max_threads=8)
        for collection in (session.get_collection_by_id(collection_id) for collection_id in ['24904767']):
            for raindrop in collection.fetch_all_raindrops():
                self.assertTrue(True)
        
        self.assertTrue(True)