# Router usage and quota manager

## Goal

A laptop desktop application for managing internet access through a main router.

## Initial release

- Add a router connection and verify access using the router's supported management interface.
- List connected devices with available names, IP addresses, stable identifiers, connection status, and monthly data usage.
- Assign and increase a monthly allowance in GB for each managed customer.
- Show used and remaining data and the current access status.
- Block internet access when the allowance is exhausted.
- Let the operator manually enable or disable access and reset usage after payment.
- Retain quota assignments and usage history across application restarts.
- Keep router credentials secure and exclude them from logs and source control.

## Enforcement requirements

Usage measurement and blocking must happen on the router or an always-on gateway, so closing the laptop app cannot bypass a quota. Router model and firmware support must be confirmed before implementing an integration. Unsupported routers may require supported firmware or a separate gateway.

IP addresses alone are not stable customer identities. The integration must account for DHCP address changes and distinguish customers from their devices. Whether one allowance covers multiple devices needs confirmation during implementation.

An enable action must state whether it overrides an exhausted quota; a usage reset starts a new allowance period. Calendar-month renewal versus renewal after manual payment must be defined before automatic resets are implemented.

## Exhausted-allowance notice

Where supported by a router captive portal, show “Your monthly limit has expired. Please contact the administrator to renew.” A desktop application alone cannot display a message on blocked devices. Arbitrary HTTPS pages cannot safely be replaced with a quota notice.

## Future release

Payment integration can renew allowances and restore access automatically. The initial release uses manual operator actions and does not process payments.

## Pending platform decisions

- Main router brand, exact model, firmware, and available management API.
- Laptop operating system.
- Router's ability to retain usage counters and enforce quotas without the laptop running.

No router integration or application functionality has been implemented or validated yet.
