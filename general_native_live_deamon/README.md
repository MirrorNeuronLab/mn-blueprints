# Divisibility Monitor Example

This is a simple long-lived MirrorNeuron workflow that keeps running until you stop it manually.

**Note:** This uses native agents for fast simulation.

## What it does

1. `question_generator` emits a new random divisibility question every 10 seconds.
2. `answer_agent` answers `yes` or `no` and logs the result.
3. The generator keeps a delayed self-schedule between cycles, so the job stays active without blocking the agent process.

## How to run

From the project root:

```bash
mn validate mn-blueprints/general_native_live_deamon
mn run mn-blueprints/general_native_live_deamon
```

If you want to watch the job after starting it:

```bash
mn monitor
mn job agents <job_id>
mn job events <job_id>
```

## Notes

- This example does not use OpenShell.
- It is intentionally open-ended, so there is no final result summary unless you manually cancel the job.
- It uses `local_restart` recovery, so old interrupted runs are not automatically resumed across fresh local CLI invocations.
