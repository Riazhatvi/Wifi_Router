"""Windows desktop interface for MikroTik HotSpot accounts."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from mikrotik import Router, GB


class App:
    def __init__(self, root):
        self.root, self.router, self.busy = root, None, False
        self.events = queue.Queue()
        root.title('Router Manager — MikroTik')
        root.geometry('1200x720')
        root.minsize(980, 600)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.closed = False
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=32)
        page = ttk.Frame(root, padding=20)
        page.pack(fill='both', expand=True)
        ttk.Label(page, text='Router Manager', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(page, text='MikroTik RouterOS v7 · HotSpot customer accounts · Router-enforced allowances').pack(anchor='w', pady=8)
        form = ttk.Frame(page)
        form.pack(fill='x', pady=10)
        self.host, self.username, self.password, self.ca = [tk.StringVar() for _ in range(4)]
        for label, var, secret in [('Router HTTPS address', self.host, False), ('Admin user', self.username, False), ('Admin password', self.password, True)]:
            ttk.Label(form, text=label).pack(side='left', padx=(0, 4))
            ttk.Entry(form, textvariable=var, width=22, show='*' if secret else '').pack(side='left', padx=(0, 12))
        cert = ttk.Frame(page)
        cert.pack(fill='x')
        ttk.Button(cert, text='Choose trusted CA certificate (optional)', command=self.choose_ca).pack(side='left')
        ttk.Label(cert, textvariable=self.ca).pack(side='left', padx=10)
        self.buttons = []
        self.button(cert, 'Connect', self.connect)
        self.button(cert, 'Disconnect', self.disconnect)
        self.status = tk.StringVar(value='Disconnected. Configure HotSpot and HTTPS on the router before connecting.')
        ttk.Label(page, textvariable=self.status, wraplength=1100).pack(anchor='w', pady=14)
        cols = ('name', 'ip', 'quota', 'used', 'left', 'status')
        self.table = ttk.Treeview(page, columns=cols, show='headings', selectmode='browse')
        for key, title in zip(cols, ('Customer login', 'Active IP address(es)', 'Allowance GB', 'Used GB', 'Remaining GB', 'Router status')):
            self.table.heading(key, text=title)
            self.table.column(key, width=175)
        self.table.pack(fill='both', expand=True)
        bar = ttk.Frame(page)
        bar.pack(fill='x', pady=15)
        for label, fn in [('Refresh', self.refresh), ('Add customer', self.add), ('Set allowance', self.quota), ('Enable', lambda: self.enable(True)), ('Disable', lambda: self.enable(False)), ('Reset / renew', self.renew)]:
            self.button(bar, label, fn)
        ttk.Label(page, text='Usage includes upload + download. 1 GB = 1,000,000,000 bytes. Renewal is manual after payment.\n'
                  'Enable does not clear an exhausted allowance. Customers must use the configured HotSpot network.').pack(anchor='w')
        root.after(100, self.poll)
        root.after(30000, self.auto_refresh)

    def button(self, parent, text, fn):
        button = ttk.Button(parent, text=text, command=lambda: self.guard(fn))
        button.pack(side='left', padx=4)
        self.buttons.append(button)

    def guard(self, fn):
        try:
            fn()
        except Exception as exc:
            messagebox.showerror('Router Manager', str(exc), parent=self.root)

    def run(self, action, callback):
        if self.busy:
            return
        self.busy = True
        for b in self.buttons:
            b.configure(state='disabled')
        self.status.set('Contacting router…')
        def worker():
            try:
                self.events.put((callback, action(), None))
            except Exception as exc:
                self.events.put((callback, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            callback, result, error = self.events.get_nowait()
            self.busy = False
            for b in self.buttons:
                b.configure(state='normal')
            if error:
                self.status.set('Request failed. Displayed data may be stale. ' + error)
                messagebox.showerror('Router request failed', error, parent=self.root)
            else:
                self.guard(lambda: callback(result))
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self.poll)

    def choose_ca(self):
        path = filedialog.askopenfilename(title='Trusted router CA certificate', filetypes=[('PEM certificate', '*.pem *.crt'), ('All files', '*')])
        if path:
            self.ca.set(path)

    def connect(self):
        if self.router:
            raise ValueError('Disconnect before changing router connections.')
        candidate = Router(self.host.get(), self.username.get(), self.password.get(), self.ca.get())
        def connected(result):
            self.router = candidate
            self.password.set('')
            self.refresh()
        self.run(lambda: (candidate.identity(), candidate.users(), candidate.active()), connected)

    def disconnect(self):
        self.router = None
        self.password.set('')
        self.table.delete(*self.table.get_children())
        self.status.set('Disconnected. Router quotas remain in effect.')

    def selected(self):
        if not self.router:
            raise ValueError('Connect to the router first.')
        selection = self.table.selection()
        if not selection:
            raise ValueError('Select a customer first.')
        return selection[0]

    def refresh(self):
        if not self.router:
            raise ValueError('Connect to the router first.')
        router = self.router
        self.run(lambda: (router.users(), router.active()), self.render)

    def render(self, result):
        users, active = result
        selection = self.table.selection()
        self.table.delete(*self.table.get_children())
        for user in users:
            if user.get('name') == 'default-trial':
                continue
            sessions = [a for a in active if a.get('user') == user.get('name')]
            used = int(user.get('bytes-in', 0)) + int(user.get('bytes-out', 0))
            quota = int(user.get('limit-bytes-total', 0))
            disabled = str(user.get('disabled', 'false')).lower() == 'true'
            state = 'Disabled' if disabled else 'Limit expired' if quota and used >= quota else 'Online' if sessions else 'Enabled / offline'
            self.table.insert('', 'end', iid=user['.id'], values=(user.get('name', ''), ', '.join(a.get('address', '') for a in sessions) or 'Offline',
                              f'{quota/GB:.3f}' if quota else 'Unlimited', f'{used/GB:.3f}', f'{max(0,quota-used)/GB:.3f}' if quota else 'Unlimited', state))
        if selection and self.table.exists(selection[0]):
            self.table.selection_set(selection[0])
        self.status.set(f'Connected · {len(self.table.get_children())} customers · Live router counters refreshed · Automatic refresh every 30 seconds')

    def change(self, fn):
        self.run(fn, lambda _: self.refresh())

    def add(self):
        if not self.router:
            raise ValueError('Connect first.')
        values = []
        for title, prompt, secret in [('Customer', 'Customer login name:', False), ('Password', 'Customer HotSpot password:', True), ('Allowance', 'Total allowance in GB:', False), ('Profile', 'Existing HotSpot profile (use shared-users=1):', False)]:
            value = simpledialog.askstring(title, prompt, parent=self.root, show='*' if secret else '')
            if value is None:
                return
            values.append(value)
        self.change(lambda: self.router.create(*values))

    def quota(self):
        user = self.selected()
        value = simpledialog.askstring('Set allowance', 'New total allowance in GB (existing usage remains):', parent=self.root)
        if value is not None:
            self.change(lambda: self.router.set_quota(user, value))

    def enable(self, enabled):
        user = self.selected()
        if not enabled and not messagebox.askyesno('Disable customer', 'Disable this account and disconnect its active sessions?', parent=self.root):
            return
        self.change(lambda: self.router.enable(user, enabled))

    def renew(self):
        user = self.selected()
        if messagebox.askyesno('Reset / renew', 'Disconnect customer, clear usage, and enable their existing allowance for a new payment period?', parent=self.root):
            self.change(lambda: self.router.renew(user))

    def auto_refresh(self):
        if self.router and not self.busy:
            self.refresh()
        if not self.closed:
            self.root.after(30000, self.auto_refresh)

    def close(self):
        if self.busy and not messagebox.askyesno('Operation in progress', 'A router operation is in progress. Closing cannot cancel a change already sent. Close anyway?', parent=self.root):
            return
        self.closed = True
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
