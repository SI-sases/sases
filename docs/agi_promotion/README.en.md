# 让两台服务器 AGI 在互联网上推广 SASES

Two regional AGI nodes, one domestic and one international, test whether
independent SASES agents can plan, localize, publish and report a small
SASES promotion campaign without a shared control plane.

## Nodes

| Role | Location | Node | Audience |
|---|---|---|---|
| Domestic | Hangzhou | node-C | Chinese |
| International | Hong Kong | node-B | English |

## What is tested

- independent content generation
- per-region localization
- publish receipt and idempotency
- per-region metrics
- failure isolation

## What is not tested

- mass automated posting
- platform rule evasion
- fake engagement

## Status

Both nodes are online with schema v18. The next step is a small,
human-approved campaign with one post per region and a 7-day observation window.
