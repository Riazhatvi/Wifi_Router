import tempfile
import unittest
from pathlib import Path
from store import Store, GB

class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.store = Store(self.path)
        self.store.add('Customer', '192.168.18.20', '10')
        self.customer = self.store.customers()[0]['id']

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def status(self):
        return self.store.status(self.store.customers()[0])

    def test_exhaustion_increase_disable_and_renew(self):
        self.store.simulate(self.customer, '10')
        self.assertEqual(self.status(), 'Limit expired')
        self.store.enable(self.customer, True)
        self.assertEqual(self.status(), 'Limit expired')
        with self.assertRaises(ValueError):
            self.store.simulate(self.customer, '1')
        self.store.quota(self.customer, '20')
        self.assertEqual(self.status(), 'Enabled')
        self.store.enable(self.customer, False)
        self.store.quota(self.customer, '30')
        self.assertEqual(self.status(), 'Disabled')
        self.store.renew(self.customer)
        self.assertEqual(self.status(), 'Enabled')
        self.assertEqual(self.store.customers()[0]['used'], 0)

    def test_persistence_and_precision(self):
        self.store.simulate(self.customer, '0.1')
        self.store.save_router('192.168.18.1')
        other = Store(self.path)
        try:
            self.assertEqual(other.customers()[0]['used'], GB // 10)
            self.assertEqual(other.router(), '192.168.18.1')
        finally:
            other.db.close()

    def test_invalid_input(self):
        for value in ['0', '-1', 'NaN', 'Infinity', 'abc', '1000001']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.quota(self.customer, value)
        with self.assertRaises(ValueError):
            self.store.add('Invalid', 'not an IP', '10')

if __name__ == '__main__':
    unittest.main()
