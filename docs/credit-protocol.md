# Credit protocol

SASES has one canonical credit protocol for the official network.

```text
protocol: sases-credit-v1
rules: credits_per_compute=5, stake_apy=0.1, pool_share=0.5
```

## What is enforced

- Credit rules live on the server; clients cannot submit their own rules.
- Peer credit transfers carry `credit_protocol`.
- A peer with a different protocol is rejected.
- `/version` exposes `credit_protocol` and `credit_rules_hash`.
- `/credits/protocol` exposes the canonical rules.

Strict mode:

```env
SASES_CREDIT_STRICT=1
```

Then a peer that omits the protocol is rejected too.

## What is not possible

SASES is MIT open source. A determined person can fork the code and run an
unofficial network with a different credit system.

That fork:

- is not part of the official network
- does not sync credits with official nodes
- is not supported
- must not use official branding

So: one protocol inside the official network, not one protocol on the planet.

## Upgrade path

Credit rule changes require:

1. a new protocol version
2. a release
3. node upgrade
4. strict mode enabled after all nodes are updated

No user/plugin can register a second credit system.
