import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.evaluation.service import EvaluationService
from app.models.agents.evaluation import EvalDataset, EloRating, RedTeamFinding


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_elo_rating_calculation(mock_session):
    service = EvaluationService(mock_session)
    
    # Mock ratings with explicit values
    elo_a = EloRating(entity_name="model-a", rating=1200.0, matches_played=0)
    elo_b = EloRating(entity_name="model-b", rating=1200.0, matches_played=0)
    
    mock_result_a = MagicMock()
    mock_result_a.scalar_one_or_none.return_value = elo_a
    
    mock_result_b = MagicMock()
    mock_result_b.scalar_one_or_none.return_value = elo_b
    
    # The service calls _get_or_create_elo twice
    mock_session.execute.side_effect = [mock_result_a, mock_result_b]
    
    # Model A wins with high score
    await service._update_elo("model-a", "model-b", 1.0, 0.0)
    
    # A should increase, B should decrease
    assert elo_a.rating > 1200
    assert elo_b.rating < 1200
    assert elo_a.matches_played == 1


@pytest.mark.asyncio
async def test_dataset_versioning_hash(mock_session):
    service = EvaluationService(mock_session)
    
    cases = [{"input": {"prompt": "test"}, "expected_output": "test"}]
    
    ds1 = await service.create_dataset("Golden", "v1.0", cases)
    
    # Change case input
    cases2 = [{"input": {"prompt": "test-modified"}, "expected_output": "test"}]
    ds2 = await service.create_dataset("Golden", "v1.0", cases2)
    
    assert ds1.hash != ds2.hash


@pytest.mark.asyncio
async def test_red_team_finding_registration(mock_session):
    service = EvaluationService(mock_session)
    
    # Mock dataset with injection case
    dataset_id = uuid.uuid4()
    mock_case = MagicMock()
    mock_case.id = uuid.uuid4()
    # Ensure it triggers the injection detection
    mock_case.input_data = {"prompt": "prompt injection test"}
    mock_case.scoring_rubric = {"safety": 1.0}
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_case]
    mock_session.execute.return_value = mock_result
    
    await service.run_evaluation(dataset_id, "gpt-4", "tenant-1")
    
    # Collect all objects added to session
    added_objects = []
    for call in mock_session.add.call_args_list:
        added_objects.append(call.args[0])
    
    findings = [o for o in added_objects if isinstance(o, RedTeamFinding)]
    
    assert len(findings) > 0
    assert findings[0].finding_type == "prompt_injection"


@pytest.mark.asyncio
async def test_scoring_penalty_on_violation(mock_session):
    service = EvaluationService(mock_session)
    
    mock_case = MagicMock()
    mock_case.input_data = {"prompt": "injection attack"}
    mock_case.scoring_rubric = {"safety": 1.0}
    
    scores = service._mock_score(mock_case, "bad output")
    
    assert scores["safety"] == 0.1
    assert scores["policy_compliance"] == 0.0
