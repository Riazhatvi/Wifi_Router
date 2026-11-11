# Router Manager — Windows + MikroTik

Start with [the complete setup guide](SETUP.md) for hardware wiring, router commissioning, Windows download instructions and environment requirements. No `.env` file is needed.

A Python/Tk desktop app using MikroTik RouterOS v7 HTTPS REST and HotSpot accounts. It lists customer accounts, active IP addresses, upload plus download counters, allowances and status. It creates accounts, sets GB allowances, enables/disables access, and resets counters after manual payment. The router enforces `limit-bytes-total` while the laptop is off.

**Status:** implementation and automated tests are available. A physical MikroTik router, real traffic exhaustion, Windows GUI, and generated EXE have not been validated in this cloud environment. Do not deploy to paying customers until the acceptance checks below pass. The Huawei by itself is not supported by this integration.

## Run on Windows

Install Python 3.12+ from python.org with Tcl/Tk and the Python launcher. Double-click `start.bat` or run `py -3 live_app.py`. No pip dependencies are needed to run the app. Enter the MikroTik HTTPS address, management username/password, and optional trusted CA PEM certificate, then Connect. Credentials stay in memory and are not saved. HTTPS certificate verification is required; use a certificate matching the router address signed by a trusted CA, or select your own trusted CA certificate.

The old local simulation remains available with `py -3 app.py`; its local data is separate from live router accounts.

## Windows executable

The included GitHub Actions workflow builds `RouterManager.exe` on Windows when pushed to main or manually triggered. Download the `RouterManager-Windows` artifact from the successful run. This workflow has not been run here. Alternatively, on Windows:

```
py -3 -m pip install pyinstaller==6.16.0
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name RouterManager live_app.py
```

Output: `dist\RouterManager.exe`. It is unsigned; an installer and code signing are not included.

## Required network setup

Keep the Huawei as the upstream fibre device. Connect Huawei LAN to MikroTik WAN. Connect all managed customers to the MikroTik client LAN or access points bridged to that LAN. Customers connected directly to Huawei Wi-Fi bypass MikroTik enforcement. Keep management access separate from the HotSpot client network.

Have an administrator configure RouterOS v7 HotSpot with working WAN, NAT, DHCP and DNS, using a supported model sized for your internet speed and client count. Use local HotSpot customer accounts, not a RADIUS-backed user database for this version. Create an appropriate HotSpot user profile with `shared-users=1`. Disable trial/free access and avoid bypass bindings for managed clients. Users sign into the HotSpot portal with the account created in this app. One account may serve only one simultaneous session under this profile; household multi-device quotas are not implemented.

Enable RouterOS HTTPS `www-ssl` with a valid certificate; restrict management to trusted administrator addresses using service restrictions and firewall rules. Do not expose REST to the internet. REST uses the permissions of the supplied RouterOS user. Use a dedicated management account with the minimum tested permissions for viewing/modifying HotSpot users, disconnecting sessions, and resetting counters. Exact policy configuration must be checked against the installed RouterOS release. The app performs no automatic firewall, WAN or HotSpot setup.

## Quota and renewal behavior

1 GB = 1,000,000,000 bytes. The allowance is combined upload and download per HotSpot account. Zero on an existing router account means unlimited and is shown as such. New app-created accounts require positive allowances. Enable does not reset counters. Increasing the total allowance retains usage; disabled accounts remain disabled.

Disable marks an account disabled and removes its current sessions. Reset / renew disables and disconnects the user, resets counters, and enables the account with its existing allowance. These requests are not atomic; a failure may leave a customer disabled. Refresh and inspect before retrying. Lowering an allowance during a live session needs testing on the selected RouterOS version; disconnect/re-login may be necessary for immediate enforcement.

Periods renew manually after payment; there is no automatic calendar-month reset or payment integration. Usage history is not archived. Router counters are the source of truth; their durability across reboot/upgrade and active-session accounting must be verified on your device. Persistent external accounting/RADIUS is needed if those checks do not preserve allowances reliably.

An expired user is denied access by HotSpot. This app does not install a custom portal. Configure and test a router HotSpot error/login page for “Your monthly limit has expired; contact the administrator.” It cannot replace arbitrary HTTPS pages.

## Acceptance checks on your actual router

Use a separate test customer and small allowance before live deployment:

1. Connect via HTTPS, create a test account using an existing profile, and sign in from the managed network. Confirm its IP appears and counters increase with upload and download.
2. Exceed a small allowance and confirm the router stops internet access while the desktop app is closed. Confirm portal messaging on the client device.
3. Increase the allowance and verify access resumes as expected; disable an active user and confirm disconnection. Re-enable without clearing an exhausted allowance and verify it stays blocked.
4. Reset / renew and confirm counters clear, login works, and the correct allowance remains.
5. Reboot the router and verify counters and enforcement survive. If not, stop deployment and add durable accounting. Test reconnects, concurrent logins, HTTPS portal behavior and bypass paths.

## Development

Use the existing checkout; cloud tasks are already isolated and do not need another Git worktree. Run `python -m unittest discover -s tests -v`. Client tests mock router responses; they do not establish real hardware compatibility. Launch `python live_app.py` in a graphical session for UI validation.
