import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch, call, ANY
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from lomaopas_sus.cli import worker_run_command, worker_schedule_command
from lomaopas_sus.supabase_client import SupabaseClient
from lomaopas_sus.diff import compute_facts_diff, should_auto_accept_diff
from lomaopas_sus.models import ExtractedFacts, SustainabilityScore, ScoreBreakdown, EvidenceSnippet, Hotel


# Mock data for testing
@pytest.fixture
def mock_supabase_client():
    with patch.dict(os.environ, {
        "SUPABASE_URL": "http://mock.supabase.url",
        "SUPABASE_SERVICE_ROLE_KEY": "mock_key",
        "WORKER_ID": "test-worker",
        "DEFAULT_EXTRACTOR_MODE": "all" # Added for worker tests
    }):
        client = AsyncMock(spec=SupabaseClient)
        client.worker_id = "test-worker"
        client.base_url = "http://mock.supabase.url/rest/v1" # Added for scheduler URL construction
        # Set default return values for common methods to avoid AttributeError
        client.fetch_next_job.return_value = None
        client.lock_job.return_value = None
        client.mark_job_success.return_value = None
        client.mark_job_failed.return_value = None
        client.get_entity.return_value = None
        client.get_entity_sources.return_value = []
        client.get_current_snapshot.return_value = None
        client.insert_snapshot.return_value = None
        client.upsert_current.return_value = None
        client.insert_proposed.return_value = None
        # client.update_entity_next_refresh.return_value = None # This is important to mock
        client.update_entity_last_attempt_success.return_value = None
        client._make_request.return_value = None # This is important for schedule command's direct _make_request calls

        yield client

@pytest.fixture
def mock_extracted_facts():
    return ExtractedFacts(
        energy_efficiency={"solar_panels_used": True},
        water_conservation={},
        waste_management={},
        local_community_engagement={},
        certifications={},
        evidence_snippets=[]
    )

@pytest.fixture
def mock_sustainability_score(mock_extracted_facts):
    return SustainabilityScore(
        score_model_version="v1.0",
        raw_facts=mock_extracted_facts,
        evidence=[],
        confidence=0.9,
        score_breakdown=ScoreBreakdown(),
        total_score_raw=50.0,
        total_score_final=45.0,
    )

# --- Test Diff Heuristics ---

def test_compute_facts_diff_first_snapshot(mock_extracted_facts, mock_sustainability_score):
    diff = compute_facts_diff(None, mock_extracted_facts, None, mock_sustainability_score)
    assert diff["summary"] == "First snapshot for this entity."
    assert diff["metrics"]["claims_added"] > 0
    assert should_auto_accept_diff(diff, is_first_snapshot=True) is True

def test_compute_facts_diff_small_change():
    current_facts = ExtractedFacts(energy_efficiency={"solar_panels_used": True})
    new_facts = ExtractedFacts(energy_efficiency={"solar_panels_used": True, "led_lighting_used": True})
    
    current_score = SustainabilityScore(score_model_version="v1.0", raw_facts=current_facts, evidence=[], confidence=0.9, score_breakdown=ScoreBreakdown(), total_score_raw=50.0, total_score_final=45.0)
    new_score = SustainabilityScore(score_model_version="v1.0", raw_facts=new_facts, evidence=[], confidence=0.9, score_breakdown=ScoreBreakdown(), total_score_raw=52.0, total_score_final=46.8)

    diff = compute_facts_diff(current_facts, new_facts, current_score, new_score)
    assert "added" in diff["changes"][0]["type"]
    assert diff["metrics"]["claims_added"] == 1
    assert diff["metrics"]["claims_removed"] == 0
    assert diff["metrics"]["label_delta"] == 0 # Small score change won't trigger label delta heuristic

    assert should_auto_accept_diff(diff, is_first_snapshot=False) is True

def test_compute_facts_diff_large_change():
    current_facts = ExtractedFacts(energy_efficiency={"solar_panels_used": True}, certifications={"eco_certifications": ["Green Key"]})
    new_facts = ExtractedFacts(energy_efficiency={"led_lighting_used": True})
    
    current_score = SustainabilityScore(score_model_version="v1.0", raw_facts=current_facts, evidence=[], confidence=0.9, score_breakdown=ScoreBreakdown(), total_score_raw=60.0, total_score_final=54.0)
    new_score = SustainabilityScore(score_model_version="v1.0", raw_facts=new_facts, evidence=[], confidence=0.9, score_breakdown=ScoreBreakdown(), total_score_raw=20.0, total_score_final=18.0)

    diff = compute_facts_diff(current_facts, new_facts, current_score, new_score)
    assert diff["metrics"]["claims_added"] >= 1
    assert diff["metrics"]["claims_removed"] >= 1
    assert abs(diff["metrics"]["label_delta"]) > 0 # Label should change significantly based on score delta
    assert diff["metrics"]["certifications_removed"] > 0

    assert should_auto_accept_diff(diff, is_first_snapshot=False) is False

# --- Test Worker Run Command ---

@pytest.mark.asyncio
async def test_worker_run_no_jobs(mock_supabase_client):
    args = MagicMock(once=True, dry_run=False)
    mock_supabase_client.fetch_next_job.return_value = None # Explicitly returning None for no jobs
    with patch('lomaopas_sus.cli.SupabaseClient', return_value=mock_supabase_client):
        await worker_run_command(args)
    mock_supabase_client.fetch_next_job.assert_called_once()
    mock_supabase_client.lock_job.assert_not_called()

@pytest.mark.asyncio
async def test_worker_run_success_auto_accept(mock_supabase_client):
    job_id = uuid4()
    entity_id = uuid4()
    mock_job_data = {"id": str(job_id), "entity_id": str(entity_id), "reason": "refresh", "attempts": 0}
    mock_locked_job_data = {"id": str(job_id), "status": "running", "attempts": 1}
    mock_entity_data = {"id": str(entity_id), "name": "Test Hotel"}
    mock_entity_sources_data = [{"source_type": "primary", "url": "http://test.com", "allowed": True}]
    mock_inserted_snapshot_data = {"id": str(uuid4())}
    mock_upserted_current_data = {"entity_id": str(entity_id)}
    mock_marked_success_data = {"id": str(job_id)}
    mock_updated_entity_data = {"id": str(entity_id)}

    mock_supabase_client.fetch_next_job.return_value = mock_job_data
    mock_supabase_client.lock_job.return_value = mock_locked_job_data
    mock_supabase_client.get_entity.return_value = mock_entity_data
    mock_supabase_client.get_entity_sources.return_value = mock_entity_sources_data
    mock_supabase_client.get_current_snapshot.return_value = None # First snapshot
    mock_supabase_client.insert_snapshot.return_value = mock_inserted_snapshot_data
    mock_supabase_client.upsert_current.return_value = mock_upserted_current_data
    mock_supabase_client.insert_proposed.return_value = None # Not called in this scenario
    mock_supabase_client.mark_job_success.return_value = mock_marked_success_data
    mock_supabase_client.update_entity_last_attempt_success.return_value = mock_updated_entity_data

    # Mock scrape_and_cache, ollama_extractor.extract, etc.
    with (
        patch("lomaopas_sus.cli.SupabaseClient", return_value=mock_supabase_client), # Patch the constructor
        patch("lomaopas_sus.cli.scrape_and_cache", new_callable=AsyncMock) as mock_scrape,
        patch("lomaopas_sus.cli.ollama_extractor.extract", new_callable=MagicMock) as mock_ollama_extract, # Changed to MagicMock
        patch("lomaopas_sus.cli.ExtractedFacts.model_validate", return_value=ExtractedFacts(energy_efficiency={"solar_panels_used": True})) as mock_validate,
        patch("lomaopas_sus.cli.calculate_sustainability_score", return_value=SustainabilityScore(score_model_version="v1.0", raw_facts=ExtractedFacts(), evidence=[], confidence=0.9, score_breakdown=ScoreBreakdown(), total_score_raw=50.0, total_score_final=45.0)) as mock_score,
        patch("lomaopas_sus.cli.json.dumps", return_value="{}"),
        patch("lomaopas_sus.cli.json.loads", return_value={}) # For extraction_schema
    ):
        mock_scrape.return_value = ("<html><body>sustainable claims</body></html>", "new")
        mock_ollama_extract.return_value = ({"energy_efficiency": {"solar_panels_used": True}}, {"duration_ms": 100, "tokens_out": 50}) # ollama_extractor.extract is sync

        args = MagicMock(once=True, dry_run=False)
        await worker_run_command(args)

        mock_supabase_client.fetch_next_job.assert_called_once()
        mock_supabase_client.lock_job.assert_called_once_with(job_id)
        mock_supabase_client.get_entity.assert_called_once_with(entity_id)
        mock_supabase_client.get_entity_sources.assert_called_once_with(entity_id)
        mock_scrape.assert_called_once()
        mock_ollama_extract.assert_called_once()
        mock_supabase_client.insert_snapshot.assert_called_once()
        mock_supabase_client.upsert_current.assert_called_once_with(entity_id, UUID(mock_inserted_snapshot_data["id"]))
        mock_supabase_client.insert_proposed.assert_not_called()
        mock_supabase_client.mark_job_success.assert_called_once_with(job_id)
        mock_supabase_client.update_entity_last_attempt_success.assert_called_once_with(entity_id, is_success=True)

@pytest.mark.asyncio
async def test_worker_run_failure(mock_supabase_client):
    job_id = uuid4()
    entity_id = uuid4()
    mock_job_data = {"id": str(job_id), "entity_id": str(entity_id), "reason": "refresh", "attempts": 0}
    mock_locked_job_data = {"id": str(job_id), "status": "running", "attempts": 1}
    mock_entity_data = {"id": str(entity_id), "name": "Test Hotel"}
    mock_entity_sources_data = [{"source_type": "primary", "url": "http://test.com", "allowed": True}]
    mock_marked_failed_data = {"id": str(job_id)}
    mock_updated_entity_data = {"id": str(entity_id)}

    mock_supabase_client.fetch_next_job.return_value = mock_job_data
    mock_supabase_client.lock_job.return_value = mock_locked_job_data
    mock_supabase_client.get_entity.return_value = mock_entity_data
    mock_supabase_client.get_entity_sources.return_value = mock_entity_sources_data
    mock_supabase_client.mark_job_failed.return_value = mock_marked_failed_data
    mock_supabase_client.update_entity_last_attempt_success.return_value = mock_updated_entity_data

    # Mock scraping to fail
    with (
        patch("lomaopas_sus.cli.SupabaseClient", return_value=mock_supabase_client), # Patch the constructor
        patch("lomaopas_sus.cli.scrape_and_cache", new_callable=AsyncMock) as mock_scrape
    ):
        mock_scrape.return_value = (None, None)

        args = MagicMock(once=True, dry_run=False)
        await worker_run_command(args)

        mock_supabase_client.fetch_next_job.assert_called_once()
        mock_supabase_client.lock_job.assert_called_once_with(job_id)
        mock_supabase_client.get_entity.assert_called_once_with(entity_id)
        mock_supabase_client.get_entity_sources.assert_called_once_with(entity_id)
        mock_scrape.assert_called_once()
        mock_supabase_client.mark_job_failed.assert_called_once_with(job_id, ANY) # Using ANY from unittest.mock for the error message
        mock_supabase_client.update_entity_last_attempt_success.assert_called_once_with(entity_id, is_success=False)


# --- Test Scheduler Command ---

@pytest.mark.asyncio
async def test_worker_schedule_no_entities_to_schedule(mock_supabase_client):
    args = MagicMock(dry_run=False)
    mock_supabase_client._make_request.return_value = [] # No entities
    with patch('lomaopas_sus.cli.SupabaseClient', return_value=mock_supabase_client): # Patch the constructor
        await worker_schedule_command(args)
    # fetch entities is called, but no jobs are scheduled
    mock_supabase_client._make_request.assert_called_once()
    mock_supabase_client.update_entity_next_refresh.assert_not_called()
    assert mock_supabase_client._make_request.call_count == 1 # Only fetch entities call

@pytest.mark.asyncio
async def test_worker_schedule_success(mock_supabase_client):
    entity_id_1 = uuid4()
    entity_id_2 = uuid4()
    mock_inserted_job_data = {"id": str(uuid4())}
    mock_updated_entity_data = {"id": str(uuid4())}

    mock_supabase_client._make_request.side_effect = [
        [ # First call to _make_request for fetching entities
            {"id": str(entity_id_1), "refresh_cadence_days": 30, "next_refresh_at": None, "status": "active"},
            {"id": str(entity_id_2), "refresh_cadence_days": 7, "next_refresh_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), "status": "active"}
        ],
        [mock_inserted_job_data], # For insert_job for entity_id_1 (POST)
        [mock_inserted_job_data], # For insert_job for entity_id_2 (POST)
    ]
    mock_supabase_client.update_entity_next_refresh.side_effect = [
        mock_updated_entity_data, # For entity_id_1
        mock_updated_entity_data, # For entity_id_2
    ]

    args = MagicMock(dry_run=False)
    with patch('lomaopas_sus.cli.SupabaseClient', return_value=mock_supabase_client): # Patch the constructor
        await worker_schedule_command(args)

    # _make_request is called 1 (fetch entities) + 2 (insert jobs) = 3 times
    assert mock_supabase_client._make_request.call_count == 3
    # Assert update_entity_next_refresh is called for both entities
    assert mock_supabase_client.update_entity_next_refresh.call_count == 2
    
    # Assert insert job calls
    post_calls = [call for call in mock_supabase_client._make_request.call_args_list if call.args[0] == "POST"]
    assert len(post_calls) == 2
    assert "ingest_jobs" in post_calls[0].args[1]
    assert "ingest_jobs" in post_calls[1].args[1]
    
    # Assert update entity calls (for next_refresh_at)
    assert mock_supabase_client.update_entity_next_refresh.call_args_list[0].args[0] == entity_id_1
    assert isinstance(mock_supabase_client.update_entity_next_refresh.call_args_list[0].args[1], datetime)
    assert mock_supabase_client.update_entity_next_refresh.call_args_list[1].args[0] == entity_id_2
    assert isinstance(mock_supabase_client.update_entity_next_refresh.call_args_list[1].args[1], datetime)
