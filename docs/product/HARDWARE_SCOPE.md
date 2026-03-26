# Hardware Scope

## Authoritative Product Boundary

For this capstone, `hardware` is a demo surface, not a real connected-device program.

What exists:

- a 3D-printed shell or rendered visual of a wearable support device
- frontend animations that make the device appear to connect, disconnect, upload, download, and sync
- a thin backend state layer that stores demo device status and demo sync history for UI continuity

What does not exist:

- BLE, USB, serial, or WebRTC device transport
- firmware, chips, drivers, provisioning, or background daemons
- real device discovery, pairing, claiming, or permissions handling
- vendor SDK integration
- physical-world data ingestion from an actual wearable device

## Backend Implication

The backend should model hardware as `demo device state + demo sync events`, not as a real IoT stack.

Allowed backend responsibilities:

- persist the current device state for the signed-in user
- auto-create one default demo device for a signed-in user on first `GET /api/v1/hardware/devices` when none exists; this is demo convenience, not provisioning
- simulate connect / disconnect / sync transitions
- expose demo logs and sync records for the Hardware page
- allow Review / Live / Hardware surfaces to reference the same demo device state

Disallowed backend responsibilities:

- implementing hardware protocols
- validating physical device identity
- ingesting real sensor or vibration streams
- building a production device platform

## UX Implication

The frontend may visually imply:

- connected / disconnected
- upload / download / sync in progress
- recent event history

Those states are presentation and demo states. They should not be described as proof of real hardware integration.

## Implementation Rule For Future Phases

Any future `hardware` phase in this repo must preserve this boundary unless the product scope explicitly changes and the documentation is revised first.
