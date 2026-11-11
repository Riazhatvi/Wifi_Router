# Complete setup guide

## What is delivered

The repository contains the Windows desktop application, a MikroTik HTTPS REST client, a Windows executable build workflow, and automated tests. Hardware commissioning, Windows execution, captive portal messaging, and real traffic enforcement still require on-site validation. No router has been configured remotely by this project.

## 1. Connect the equipment

Your planned service is 15 Mbps for up to 40 customers. Put the MikroTik between the Huawei and every managed customer's access point:

```
Internet / fibre -> Huawei -> MikroTik WAN
                              MikroTik client LAN -> Wi-Fi access points -> customers
                              Management network -> Windows laptop
```

Use access points in bridge/AP mode on the client LAN. Direct Huawei Wi-Fi access bypasses the limits. Keep the laptop's management access outside the customer HotSpot if possible. Do not change Huawei fibre provisioning or factory-reset it.

Choose a RouterOS v7 device with HotSpot support and sufficient licensed active sessions for your expected concurrent users. Confirm the exact model, installed RouterOS version, license limits, and Wi-Fi access point capacity before purchase. Bandwidth is shared: 15 Mbps cannot provide fast simultaneous video for 40 users.

## 2. Commission the MikroTik locally

Use WinBox from a trusted management connection. Back up the router configuration first. Router model, interface names, existing firewall rules and IP ranges must be known before applying configuration; do not paste a generic full-router script.

1. Verify the WAN gets upstream connectivity from the Huawei. Use different subnets for WAN, clients, and management to avoid conflicts. Configure NAT and the firewall using RouterOS's supported configuration for your topology.
2. Configure a client bridge, DHCP and DNS, then run **IP -> HotSpot -> HotSpot Setup** on that client bridge. Test internet access from one client.
3. Use local HotSpot accounts. Create a HotSpot user profile named `monthly`, with **Shared Users = 1**. Optional rate limits are separate from GB allowances. Review FastTrack compatibility and queues with your network administrator; verify traffic actually passes through HotSpot accounting.
4. Disable trial access and remove any unintended client bypass/IP bindings. Verify an unauthenticated customer cannot get unrestricted internet.
5. Configure an HTTPS certificate with a subject alternative name matching the management hostname or IP you will enter in the app. Enable **IP -> Services -> www-ssl**, using that certificate. REST is available through this service on supported RouterOS v7 releases. Use the default HTTPS port or specify the actual port in the app.
6. Create a dedicated router management user. Grant only the permissions tested as necessary for REST access, reading/modifying local HotSpot users, removing active sessions and resetting counters. Confirm permissions on your installed release; do not reuse a customer HotSpot login as the management login.
7. Restrict management service access and firewall rules to the laptop's management address/network. Do not port-forward REST from the public internet.
8. Export only your public CA certificate as PEM if it is not already trusted by Windows/Python. Transfer it to the laptop through a trusted channel. Do not export a private key to this application.

Do not turn off certificate verification to work around connection errors. Ensure the certificate matches the address, the clock is correct, and the CA file is the issuing CA.

## 3. Download and launch on Windows

### Download a built executable

After this repository has been pushed, open its **Actions** tab, select **Windows desktop build**, and open a successful run. Download the `RouterManager-Windows` artifact, extract it, and launch `RouterManager.exe`. GitHub sign-in may be required to download artifacts. If the run failed, inspect its logs; do not assume an executable exists. The executable is unsigned.

### Run the source instead

Install Python 3.12 or newer from python.org, including Tcl/Tk and the Python launcher. Download this repository's ZIP from GitHub and extract it. Double-click `start.bat`. The application has no third-party runtime packages and does not need a web server, Docker, Node.js or a cloud database.

## 4. Enter connection details

| App field | Value needed |
| --- | --- |
| Router HTTPS address | MikroTik management IP or DNS name, optionally a port, for example `https://192.168.88.1`. This is an example, not your confirmed address. |
| Admin user | Dedicated RouterOS REST management username. |
| Admin password | That user's password, entered locally in the app. Never send it in chat or commit it. |
| Trusted CA certificate | Local PEM file for your router's issuing CA, if it is not trusted by the default certificate store. |

Click **Connect**. The app checks router identity and read access to HotSpot users and active sessions. A successful connection does not prove write permissions or traffic enforcement; validate them below.

When adding a customer, provide a unique login name, customer password, positive total GB allowance, and the existing profile name `monthly`. Give the customer their HotSpot credentials privately. Their current IP appears when they sign into the managed network. Devices and customer names are not automatically discovered or inferred from Wi-Fi connections. One account permits one simultaneous login with this profile.

## 5. Operate the service

- **Set allowance:** change the total GB available in the current period. Existing usage remains.
- **Disable:** disable login and disconnect the customer's active sessions.
- **Enable:** allow login again if their allowance is not exhausted. This does not clear usage.
- **Reset / renew:** after payment, disconnect the customer, clear counters and enable the existing allowance for a new period. Check the result if any operation fails.

The router enforces allowances; the app refreshes displayed counters every 30 seconds. There is no payment processor, automatic monthly renewal, customer history archive, or guaranteed usage persistence across router restart in this version. These are outstanding requirements for a production billing service.

Customize the router's HotSpot login/error page for the expired-allowance notice. Back up the original portal files and test from client devices. This app does not install the notice automatically or intercept arbitrary HTTPS pages.

## 6. Validate before serving customers

Follow the acceptance checks in README.md. Specifically prove that a small allowance is exhausted by real traffic and stops internet while the laptop app is closed. Test disable, increase, renewal and router reboot. If reboot loses counters, do not use this for monthly billing until durable external accounting is added. Confirm all customer access points are behind MikroTik and cannot bypass it.

## Environment variables and cloud settings

**No `.env` file or application environment variables are required or read by the live application.** Enter router connection details in the desktop app each session. Credentials remain in memory; there is no password persistence. A CA file is public certificate material, not the router's private key.

**GitHub Actions:** no custom secrets or variables are required. The workflow uses the automatic read-only `GITHUB_TOKEN` supplied by GitHub. The repository must permit Actions to run. The workflow tests the code and builds an EXE; it does not connect to your router or configure your network.

**Codex/cloud development:** Python 3.12+ is sufficient for the automated tests; a graphical desktop and Tk are needed to launch the GUI. No router password, Wi-Fi password, payment key or GitHub token needs to be added to this project's cloud environment. Your home/private router is not reachable from the cloud merely by entering its LAN IP. Run the app on your local Windows laptop; any future remote diagnostics would require a separately authorized network path.

The files `.env`, certificates/private keys, router backups and build outputs are excluded from Git as a precaution. Keep backups and passwords outside the checkout.
