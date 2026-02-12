# Supabase Worker Operations

This document outlines how to run and manage the Supabase worker for the Lomaopas Sustainability Agent.

## Overview

The Supabase worker is responsible for:
- Consuming `ingest_jobs` from the Supabase database.
- Running the sustainability fact extraction pipeline (scraping, LLM extraction, normalization, scoring).
- Generating `facts_snapshots` based on the extracted data.
- Calculating diffs against existing `facts_current` entries.
- Automatically accepting small diffs (updating `facts_current`).
- Proposing large diffs for manual review (inserting into `facts_proposed`).
- Scheduling new `ingest_jobs` based on entity refresh policies.

## Environment Variables

The worker requires the following environment variables to be set. These should be defined in a `.env` file in the project root (which is gitignored).

| Variable                      | Description                                                                 | Default                                 |
| :---------------------------- | :-------------------------------------------------------------------------- | :-------------------------------------- |
| `SUPABASE_URL`                | The URL of your Supabase project.                                           | **(Required)**                          |
| `SUPABASE_SERVICE_ROLE_KEY`   | The Supabase service role key (found in Project Settings -> API).           | **(Required)**                          |
| `SUPABASE_SCHEMA`             | The database schema to use (e.g., `public`).                                | `public`                                |
| `WORKER_ID`                   | A unique identifier for this worker instance (e.g., hostname).              | `hostname-or-random`                    |
| `OPENAI_API_KEY`              | OpenAI API key, if using the OpenAI extractor.                              | (Optional)                              |
| `LOCAL_LLM_BASE_URL`          | Base URL for local LLM (e.g., Ollama), if using the local extractor.        | `http://localhost:11434`                |
| `DEFAULT_EXTRACTOR_MODE`      | Default LLM extractor mode to use: `all`, `openai`, or `local`.             | `all`                                   |

**Example `.env` file:**
```
SUPABASE_URL=https://your-supabase-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
# SUPABASE_SCHEMA=public
# WORKER_ID=my-worker-instance-1
OPENAI_API_KEY=sk-your_openai_api_key
LOCAL_LLM_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b-instruct
DEFAULT_EXTRACTOR_MODE=all
```

## Running the Worker

The worker functionality is integrated into the main CLI application.

### Start the Job Consumer

To start a worker instance that continuously consumes `ingest_jobs`:

```bash
python -m lomaopas_sus.cli worker run
```

This will run in an infinite loop, fetching and processing jobs.

#### Single Job Mode

To process a single job and exit:

```bash
python -m lomaopas_sus.cli worker run --once
```

#### Dry-Run Mode

To run the worker logic without making any changes to the database (e.g., for testing or debugging):

```bash
python -m lomaopas_sus.cli worker run --dry-run
```

This will log what actions *would* be taken (e.g., "DRY-RUN: Would insert snapshot...").

### Run the Scheduler

To run the scheduler that creates `refresh` jobs based on entity refresh cadences:

```bash
python -m lomaopas_sus.cli worker schedule
```

#### Dry-Run Mode for Scheduler

To run the scheduler logic without creating any actual jobs or updating entity refresh times:

```bash
python -m lomaopas_sus.cli worker schedule --dry-run
```

## Cron Examples

Here are examples of how you might set up cron jobs to manage the worker and scheduler.

**1. Scheduler: Run every hour to create refresh jobs.**
```cron
0 * * * * cd /path/to/lomaopas-sustainability-agent && /usr/bin/python3 -m lomaopas_sus.cli worker schedule >> /var/log/lomaopas_scheduler.log 2>&1
```

**2. Worker: Run continuously as a background process (e.g., using systemd or a process manager).**
Alternatively, if running as a simple cron job, ensure it's not overlapping:
```cron
*/5 * * * * cd /path/to/lomaopas-sustainability-agent && /usr/bin/python3 -m lomaopas_sus.cli worker run --once >> /var/log/lomaopas_worker.log 2>&1
```
*(Note: A `--once` cron job is generally less efficient than a long-running process managed by systemd for continuous job processing.)*

## Deployment Considerations

- **Multiple Workers**: You can run multiple worker instances concurrently. Ensure `WORKER_ID` is unique for each instance if you need to track which worker processed a job. The job locking mechanism (`locked_at`, `locked_by`) prevents multiple workers from processing the same job.
- **Error Monitoring**: Monitor worker logs (`/var/log/lomaopas_worker.log`) for any `Failed` job statuses or `Worker main loop error` messages.
- **Resource Usage**: LLM extraction can be resource-intensive. Monitor CPU/memory usage of worker processes.
