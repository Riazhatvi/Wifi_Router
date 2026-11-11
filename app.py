import os
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from store import Store, GB


class App:
    def __init__(self, root, store):
        self.root, self.store = root, store
        root.title('Router Manager — Local Demo')
        root.geometry('1100x640')
        root.minsize(900, 520)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=34)
        style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'))
        page = ttk.Frame(root, padding=24)
        page.pack(fill='both', expand=True)
        ttk.Label(page, text='Router Manager', style='Title.TLabel').pack(anchor='w')
        ttk.Label(page, text='LOCAL DEMO • No live router connection • Changes do not affect internet access',
                  foreground='#a04400').pack(anchor='w', pady=(8, 16))
        connection = ttk.Frame(page)
        connection.pack(fill='x')
        ttk.Label(connection, text='Huawei EG8141H5 · Router IP:').pack(side='left')
        self.address = tk.StringVar(value=store.router())
        ttk.Entry(connection, textvariable=self.address, width=20).pack(side='left', padx=8)
        ttk.Button(connection, text='Save address', command=lambda: self.guard(self.save_router)).pack(side='left')
        self.summary = ttk.Label(page)
        self.summary.pack(anchor='w', pady=18)
        columns = ('name', 'ip', 'quota', 'used', 'remaining', 'status')
        self.table = ttk.Treeview(page, columns=columns, show='headings', selectmode='browse')
        for key, title in zip(columns, ('Customer', 'IP address', 'Allowance (GB)', 'Used (GB)', 'Remaining (GB)', 'Local status')):
            self.table.heading(key, text=title)
            self.table.column(key, width=150, minwidth=90)
        self.table.tag_configure('expired', foreground='#b42318')
        self.table.tag_configure('disabled', foreground='#667085')
        self.table.pack(fill='both', expand=True)
        actions = ttk.Frame(page)
        actions.pack(fill='x', pady=16)
        for title, fn in [('Add customer', self.add), ('Set allowance', self.set_quota),
                          ('Enable', lambda: self.set_enabled(True)), ('Disable', lambda: self.set_enabled(False)),
                          ('Reset / renew', self.renew), ('Simulate usage', self.simulate)]:
            ttk.Button(actions, text=title, command=lambda f=fn: self.guard(f)).pack(side='left', padx=(0, 8))
        ttk.Label(page, text='1 GB = 1,000,000,000 bytes. Reset starts a new period and enables access locally.\n'
                  'Enabling an exhausted allowance does not renew it. No automatic monthly reset or payments.',
                  wraplength=950).pack(anchor='w')
        self.refresh()

    def guard(self, fn):
        try:
            fn()
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Unable to complete action', str(error), parent=self.root)

    def selected(self):
        selected = self.table.selection()
        if not selected:
            raise ValueError('Select a customer first.')
        return int(selected[0])

    def refresh(self):
        selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        rows = self.store.customers()
        expired = 0
        for r in rows:
            status = self.store.status(r)
            expired += status == 'Limit expired'
            tag = 'expired' if status == 'Limit expired' else 'disabled' if status == 'Disabled' else ''
            self.table.insert('', 'end', iid=str(r['id']), values=(r['name'], r['ip'],
                f"{r['quota']/GB:.3f}", f"{r['used']/GB:.3f}", f"{max(0,r['quota']-r['used'])/GB:.3f}", status), tags=(tag,))
        if selected and self.table.exists(selected[0]):
            self.table.selection_set(selected[0])
        self.summary.configure(text=f'{len(rows)} customers    |    {expired} expired allowances    |    Usage source: manual simulation')

    def ask(self, title, prompt):
        return simpledialog.askstring(title, prompt, parent=self.root)

    def add(self):
        name = self.ask('Add customer', 'Customer name:')
        if name is None:
            return
        ip = self.ask('Add customer', 'Device IP address:')
        if ip is None:
            return
        quota = self.ask('Add customer', 'Monthly allowance in GB:')
        if quota is not None:
            self.store.add(name, ip, quota)
            self.refresh()

    def set_quota(self):
        customer = self.selected()
        quota = self.ask('Set allowance', 'New total allowance in GB (usage stays unchanged):')
        if quota is not None:
            self.store.quota(customer, quota)
            self.refresh()

    def set_enabled(self, enabled):
        self.store.enable(self.selected(), enabled)
        self.refresh()

    def renew(self):
        customer = self.selected()
        if messagebox.askyesno('Reset / renew', 'Clear recorded usage and enable this customer for a new period?', parent=self.root):
            self.store.renew(customer)
            self.refresh()

    def simulate(self):
        customer = self.selected()
        value = self.ask('Simulate usage', 'Demo traffic to add in GB (does not read the router):')
        if value is not None:
            self.store.simulate(customer, value)
            self.refresh()

    def save_router(self):
        self.store.save_router(self.address.get())
        messagebox.showinfo('Address saved', 'Saved locally. Live Huawei integration is not implemented.', parent=self.root)


if __name__ == '__main__':
    data = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share'))) / 'RouterManager'
    data.mkdir(parents=True, exist_ok=True)
    store = Store(data / 'router-manager.sqlite3')
    root = tk.Tk()
    App(root, store)
    try:
        root.mainloop()
    finally:
        store.db.close()
