# Persistent Analysis Jobs

Beattrack stores uploaded audio analysis status in `analysis_jobs`.

Before this change, `/analyze` kept job state in a Python dictionary inside the API process. That works for one local process, but it breaks after restarts and becomes unreliable when API and worker processes are separate.

★ ʕ ᵔᴥᵔ ʔ Erklaerbaer
Think of `analysis_jobs` as the shared notebook for the upload flow. The API writes "job created", the worker writes "I am processing" and then "done" or "failed", and every API instance can read the same note.

## Lifecycle

`queued` means the upload was accepted and the Procrastinate task was enqueued.

`processing` means the worker has started feature extraction or result processing.

`completed` means the worker finished and stored the response payload in `result`.

`failed` means the worker or enqueue step failed. `last_error` contains the human-readable detail, and `error_code` contains a stable category for the API/UI.

## Important Columns

- `id`: UUID returned to the client as `job_id`.
- `status`: `queued`, `processing`, `completed`, or `failed`.
- `progress`: number from `0` to `1`.
- `audio_path`: temporary file path used by the worker.
- `duration_sec`: validated audio duration.
- `result`: JSON response returned by `/analyze/{job_id}/results` after completion.
- `last_error`: readable failure message.
- `error_code`: stable failure category such as `feature_extraction_failed` or `queue_enqueue_failed`.
- `attempt_count`: how many times a worker has started processing this job.

## Request Flow

1. `POST /analyze` validates and stores the uploaded file.
2. The route creates an `analysis_jobs` row with `status = queued`.
3. The route enqueues `analyze_audio` in Procrastinate.
4. The worker updates the row to `processing`, increments `attempt_count`, and clears stale error fields.
5. The worker writes either `completed + result` or `failed + last_error/error_code`.
6. `/analyze/{job_id}/results` and `/analyze/{job_id}/stream` read from `analysis_jobs`.

## Debugging

For a job that disappeared from the UI, check the table first:

```sql
select id, status, progress, last_error, error_code, created_at, updated_at
from analysis_jobs
where id = '<job-id>';
```

If there is no row, the upload failed before job creation.

If the row is stuck in `queued`, check whether Procrastinate workers are running.

If the row is stuck in `processing`, check worker logs and the temp audio path.

If the row is `failed`, use `error_code` for the broad class and `last_error` for the concrete message.
