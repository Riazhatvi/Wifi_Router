import ipaddress
import sqlite3
from datetime import datetime, timezone

GB = 1_000_000_000

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS customers (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, ip TEXT NOT NULL UNIQUE,
          quota INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0,
          enabled INTEGER NOT NULL DEFAULT 1, period TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')

    def customers(self):
        return self.db.execute('SELECT * FROM customers ORDER BY name COLLATE NOCASE').fetchall()

    @staticmethod
    def status(row):
        if not row['enabled']:
            return 'Disabled'
        return 'Limit expired' if row['used'] >= row['quota'] else 'Enabled'

    def add(self, name, ip, quota):
        name = name.strip()
        if not name:
            raise ValueError('Enter a customer name.')
        ip = str(ipaddress.ip_address(ip.strip()))
        with self.db:
            self.db.execute('INSERT INTO customers(name,ip,quota,period) VALUES(?,?,?,?)',
                            (name, ip, self.allowance(quota), datetime.now(timezone.utc).isoformat()))

    @staticmethod
    def allowance(value):
        from decimal import Decimal, InvalidOperation
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or amount <= 0 or amount > 1_000_000:
                raise ValueError()
            result = int(amount * GB)
            if result < 1:
                raise ValueError()
            return result
        except (InvalidOperation, ValueError, OverflowError):
            raise ValueError('Enter an allowance above zero and at most 1,000,000 GB.') from None

    def quota(self, customer_id, value):
        with self.db:
            self.db.execute('UPDATE customers SET quota=? WHERE id=?', (self.allowance(value), customer_id))

    def enable(self, customer_id, enabled):
        with self.db:
            self.db.execute('UPDATE customers SET enabled=? WHERE id=?', (int(enabled), customer_id))

    def renew(self, customer_id):
        with self.db:
            self.db.execute('UPDATE customers SET used=0,enabled=1,period=? WHERE id=?',
                            (datetime.now(timezone.utc).isoformat(), customer_id))

    def simulate(self, customer_id, value):
        amount = self.allowance(value)
        with self.db:
            row = self.db.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()
            if row is None or self.status(row) != 'Enabled':
                raise ValueError('Enable or renew this customer before simulating usage.')
            self.db.execute('UPDATE customers SET used=used+? WHERE id=?', (amount, customer_id))

    def save_router(self, address):
        address = str(ipaddress.ip_address(address.strip()))
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES('router',?)", (address,))

    def router(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='router'").fetchone()
        return row[0] if row else '192.168.18.1'
