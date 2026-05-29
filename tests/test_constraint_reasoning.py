import pytest
from app.services.agents.reasoning.constraints.constraint_runtime import ConstraintRuntime
from app.services.agents.reasoning.constraints.constraint_model import ConstraintModel, Constraint
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_plano_valido_passa():
    settings = get_settings()
    settings.agent_constraint_reasoning_enabled = True
    
    runtime = ConstraintRuntime()
    model = ConstraintModel(constraints=[
        Constraint(id="c1", type="comparison", target_field="budget", operator="le", value=100.0)
    ])
    plan_data = {"budget": 50.0}
    
    res = await runtime.validate_plan(model, plan_data)
    assert res["status"] == "validated"

@pytest.mark.asyncio
async def test_budget_constraint_invalida_bloqueia():
    settings = get_settings()
    settings.agent_constraint_reasoning_enabled = True
    settings.agent_z3_solver_enabled = False
    settings.agent_glpk_solver_enabled = False
    
    runtime = ConstraintRuntime()
    model = ConstraintModel(constraints=[
        Constraint(id="c1", type="comparison", target_field="budget", operator="le", value=100.0, message="Budget exceeded")
    ])
    plan_data = {"budget": 150.0}
    
    res = await runtime.validate_plan(model, plan_data)
    assert res["status"] == "rejected"
    assert res["errors"][0]["message"] == "Budget exceeded"

@pytest.mark.asyncio
async def test_solver_indisponivel_fallback_simples_funciona():
    settings = get_settings()
    settings.agent_constraint_reasoning_enabled = True
    settings.agent_z3_solver_enabled = False
    settings.agent_glpk_solver_enabled = False
    
    runtime = ConstraintRuntime()
    model = ConstraintModel(constraints=[
        Constraint(id="c1", type="comparison", target_field="team_size", operator="ge", value=2)
    ])
    
    # Valid case
    res1 = await runtime.validate_plan(model, {"team_size": 3})
    assert res1["status"] == "validated"
    assert res1["stage"] == "fallback_validation"
    
    # Invalid case
    res2 = await runtime.validate_plan(model, {"team_size": 1})
    assert res2["status"] == "rejected"
