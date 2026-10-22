# Protocol v1 schema index

These Draft 2020-12 schemas describe the frozen ESP32-C3 P0 wire/profile shapes. The executable Python validator remains authoritative for cross-field/runtime limits such as decoded byte size, total cycle duration, minimum loop duration, exact sequence, MAC, and authenticated device-reported capacities. A future device with different capacity ceilings needs a matching profile schema while retaining the same semantic-free v1 message structure.

| Wire type | Structural schema for decoded body |
|---|---|
| Handshake and signed envelope | [`wire-message-v1.schema.json`](wire-message-v1.schema.json) |
| `LOAD_SCENE` | [`load-scene-body-v1.schema.json`](load-scene-body-v1.schema.json) |
| `KEEPALIVE`, `CLEAR` | [`scene-id-body-v1.schema.json`](scene-id-body-v1.schema.json) |
| Controller `STATUS` | [`status-request-body-v1.schema.json`](status-request-body-v1.schema.json) |
| `CAPABILITIES` | [`capabilities-body-v1.schema.json`](capabilities-body-v1.schema.json) |
| `ACK` | [`ack-body-v1.schema.json`](ack-body-v1.schema.json) |
| `ERROR` | [`error-body-v1.schema.json`](error-body-v1.schema.json) |
| Device `STATUS` | [`status-body-v1.schema.json`](status-body-v1.schema.json) |
| `BUTTON_EVENT` | [`button-event-body-v1.schema.json`](button-event-body-v1.schema.json) |
| `SENSOR_EVENT` | [`sensor-event-body-v1.schema.json`](sensor-event-body-v1.schema.json) |
| Pack manifest | [`pack-manifest-v1.schema.json`](pack-manifest-v1.schema.json) |

The envelope's `body` is base64url text. Decode it into a JSON object, select the body schema by authenticated `type`, then apply the runtime validator/capability checks. No v1 schema admits a battery event or battery capability.
