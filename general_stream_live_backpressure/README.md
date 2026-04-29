# General Stream Live Backpressure

This blueprint demonstrates MirrorNeuron as a live event runtime with bounded stream pressure instead of an unlimited task queue.

The graph is intentionally small:

- `ingress`: accepts the initial stream start signal.
- `burst_source`: emits a fast burst of stream events.
- `slow_enricher`: manually sleeps for each event and has a tiny bounded queue.
- `metrics_sink`: also sleeps briefly while recording processed counts.

When `slow_enricher` falls behind, the runtime reports queue pressure and live external inputs receive retry-later responses instead of being accepted forever.

## Run

From the MirrorNeuron app directory:

```bash
mn run mn-blueprints/general_stream_live_backpressure
```

`mn run` writes slow-agent and backpressure events to the standard job log:

```bash
/tmp/mn_<job_id>/run.log
```

For a stronger retry-later proof, run the local demo from the MirrorNeuron app directory:

```bash
cd MirrorNeuron
MIRROR_NEURON_GRPC_PORT=55251 mix run ../mn-blueprints/general_stream_live_backpressure/demo_backpressure.exs
```

The demo starts the blueprint, sends concurrent live inputs to the slow stream processor, writes pressure evidence to `/tmp/mn_<job_id>/run.log`, prints accepted vs retry-later counts, prints pressure state, then cancels the daemon job.

## What To Look For

Runtime events include:

- `backpressure_state`: queue depth crossed a high watermark.
- `external_input_rejected`: live input was rejected with retry-later details.
- `slow_event_processed`: the overloaded stream processor made progress.
- `stream_metrics_updated`: the sink observed processed stream output.
- `source_burst_emitted`: the fast source emitted the burst that overloads the downstream queues.

Each pressure payload includes:

- `queue_depth`
- `high_watermark`
- `low_watermark`
- `max_queue_depth`
- `retry_after_ms`
- `status`

## Backpressure Settings

Each node can define:

```json
{
  "backpressure": {
      "max_queue_depth": 4,
      "high_watermark": 2,
      "low_watermark": 1,
      "retry_after_ms": 750
  }
}
```

`max_queue_depth` bounds accepted work. `high_watermark` marks the node as pressured. Live input routed to that node, or to an upstream node that can reach it, receives retry-later while pressure is active.

## Reuse

Use this pattern when building CEP-style agents:

- Put stream processors behind bounded queues.
- Emit small event envelopes with stable `type` and `payload`.
- Keep slow or external operations in isolated nodes.
- Use `MirrorNeuron.pressure(job_id)` to inspect live pressure.
- Treat retry-later as normal flow control, not as a fatal error.
