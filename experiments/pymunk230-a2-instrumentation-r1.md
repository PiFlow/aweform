# Pymunk #230 A2-R1 instrumentation-only candidate

This source-only candidate repairs the receipt contract, parent wall watchdog, and fixed runner boundary. It does **not** execute Pymunk or any simulator transition. `--preflight` only prints the fixed run plan; the CLI refuses physical execution pending the separately required fresh decision after exact-source review.

## Preserved identities and scope

- Base: `c9280554268a789949b73babdd40d5f363649761`.
- Frozen attempt-3 source: `1ab7cf43220ee9348e8d966745c93abfa346e190`.
- Frozen full protocol SHA-256: `9f749b39d37da4541b8dae84c732a9e24ae271e3767906ed862c5f88a1e0fe18`.
- Frozen physics digest: `7f2492e326a57d7ca12b65bbdb1202cb7538d5a0c4ae25dea8c7a6f809f93fd4`.
- Frozen cmd1 prefix digest: `e8c0aec8d82c6e79143ee70ea50519f3cf2c369e07df73795db6038a387e63c7`.
- Total proposed accounting remains 4,800 substeps. The A2-convex target uses frozen cmd1+cmd2 prefixes at N400 (400+400) and N800 (800+800), totaling 2,400. The exact `empty-free` control starts at `(1,1,0)`, runs `F×1`, and uses primary plus fresh replay at N400 (400+400) and N800 (800+800), totaling the remaining 2,400. The source fixture identity for A2 remains bound to its frozen digest; no A2 start/action value is redefined here. The model-free negative-control validator requires byte-identical primary/replay JSONL and zero contact-event rows.
- Checkpoints are cmd1 `{0,.25,.50,.75,1}` and cmd2 `{0,.25,.50,.75,.85,.90,.98,1}`; detailed cmd2 logging is inclusive `[.85,.98]`. N400/N800 observations align by normalized physical time.
- The original frozen geometry, commands, thresholds, failure disposition, and STOP semantics are not changed.

## Safety mechanics

The public entry point takes no child command. Its fixed child is an internal model-free plumbing worker. Child output is consumed by a separate reader thread while the supervising process polls a monotonic deadline; a silent child cannot block deadline enforcement. Timeout/cap/error paths terminate the process group, reap the child, fsync the append-only event journal, then atomically write/fsync `STOP.json` plus detached `STOP.sha256`. The receipt's `last_durable` is top-level and names the flushed byte count, event sequence, and SHA-256; it never replaces or weakens event custody.

Limits apply to the complete event file plus STOP receipt and detached hash (2 MiB), 10,000 events, 120 seconds wall, 120 seconds child CPU, and observed RSS 256 MiB. Unavailable CPU/RSS measurements fail closed. Events are sequence-numbered and individually flushed before advancing the durable watermark. Output directories are one-shot.

Tests use only local subprocess plumbing and synthetic events. They do not import/step Pymunk, call an A2 case, or execute a physics transition. No Stage C run is authorized by this candidate.
