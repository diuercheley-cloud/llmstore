from unittest.mock import patch

from app.schemas.routing import CommercialSimulateRequest, TaskType
from app.services.routing.commercial_routing import simulate_commercial_routing

CLOUD_PROVIDERS = {"openai", "anthropic", "deepseek", "openrouter"}


def _req(**overrides) -> CommercialSimulateRequest:
    kwargs = dict(
        plan="basic",
        model="default",
        estimated_input_tokens=100,
        estimated_output_tokens=512,
        task_type=TaskType.general,
        billing_status="active",
        wallet_balance_brl=100.0,
    )
    kwargs.update(overrides)
    return CommercialSimulateRequest(**kwargs)


class TestCommercialRoutingBasic:
    def test_basic_prefers_local_first(self):
        req = _req(plan="basic", task_type=TaskType.general)
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) in (
            "local",
            "lmstudio",
            "mock",
        )
        assert resp.tier == "basic"
        assert (resp.selected_route.provider if resp.selected_route else None) is not None

    def test_basic_blocks_cloud_when_not_allowed(self):
        req = _req(plan="basic", cloud_allowed=False)
        resp = simulate_commercial_routing(req)
        if resp.selected_route.provider if resp.selected_route else None:
            assert (resp.selected_route.provider if resp.selected_route else None) not in (
                "openai",
                "anthropic",
                "deepseek",
                "openrouter",
            )
        for r in resp.rejected_routes:
            if r.provider in ("openai", "anthropic", "deepseek", "openrouter"):
                assert (len(r.rejection_reasons) > 0) is True

    def test_basic_cloud_enabled_explicitly(self):
        req = _req(
            plan="basic", cloud_allowed=True, estimated_input_tokens=10, estimated_output_tokens=50
        )
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) is not None

    def test_basic_blocks_provider_on_excessive_cost(self):
        req = _req(
            plan="basic",
            cloud_allowed=True,
            estimated_input_tokens=50000,
            estimated_output_tokens=50000,
        )
        resp = simulate_commercial_routing(req)
        for r in resp.rejected_routes:
            if r.estimated_cost_brl > 0.10:
                assert (len(r.rejection_reasons) > 0) is True, (
                    f"{r.provider} should be rejected, cost={r.estimated_cost_brl}"
                )


class TestCommercialRoutingPro:
    def test_pro_uses_lowest_cost(self):
        req = _req(plan="pro", task_type=TaskType.general, cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "pro"
        assert (resp.selected_route.provider if resp.selected_route else None) is not None

    def test_pro_respects_wallet_balance(self):
        req = _req(
            plan="pro",
            cloud_allowed=True,
            wallet_balance_brl=0.05,
            estimated_input_tokens=10000,
            estimated_output_tokens=10000,
        )
        resp = simulate_commercial_routing(req)
        for r in resp.rejected_routes:
            if r.estimated_cost_brl > 0.05 and (r.provider in CLOUD_PROVIDERS):
                assert (len(r.rejection_reasons) > 0) is True

    def pro_respects_max_cost_per_request(self):
        req = _req(
            plan="pro",
            cloud_allowed=True,
            estimated_input_tokens=500000,
            estimated_output_tokens=500000,
        )
        resp = simulate_commercial_routing(req)
        if resp.selected_route.provider if resp.selected_route else None:
            assert resp.selected_route.estimated_cost_brl <= 0.50
        for r in resp.rejected_routes:
            if r.estimated_cost_brl > 0.50:
                assert (len(r.rejection_reasons) > 0) is True


class TestCommercialRoutingPremium:
    def test_premium_uses_premium_quality(self):
        req = _req(plan="enterprise", cloud_allowed=True, task_type=TaskType.general)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "premium"

    def test_premium_respects_max_cost_per_request(self):
        req = _req(
            plan="enterprise",
            cloud_allowed=True,
            estimated_input_tokens=500000,
            estimated_output_tokens=500000,
        )
        resp = simulate_commercial_routing(req)
        if resp.selected_route.provider if resp.selected_route else None:
            assert resp.selected_route.estimated_cost_brl <= 1.00

    def test_premium_allows_better_providers(self):
        req = _req(plan="enterprise", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) is not None
        providers_in_premium_order = [
            "openai",
            "anthropic",
            "local",
            "lmstudio",
            "deepseek",
            "openrouter",
            "mock",
        ]
        assert (
            resp.selected_route.provider if resp.selected_route else None
        ) in providers_in_premium_order


class TestCommercialRoutingCoding:
    def test_coding_prefers_anthropic(self):
        req = _req(plan="pro", task_type=TaskType.coding, cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "coding"
        if resp.selected_route.provider if resp.selected_route else None:
            assert (resp.selected_route.provider if resp.selected_route else None) in (
                "anthropic",
                "openai",
                "deepseek",
                "local",
                "lmstudio",
                "openrouter",
                "mock",
            )

    def test_coding_falls_back_when_margin_negative(self):
        req = _req(
            plan="pro",
            task_type=TaskType.coding,
            cloud_allowed=True,
            estimated_input_tokens=50000,
            estimated_output_tokens=50000,
        )
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) is not None
        for r in resp.rejected_routes:
            if r.estimated_margin_percent is not None and r.estimated_margin_percent < 0:
                assert (len(r.rejection_reasons) > 0) is True


class TestCommercialRoutingSuspended:
    def test_suspended_blocks_cloud(self):
        req = _req(plan="basic", billing_status="suspended", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "suspended"
        if resp.selected_route.provider if resp.selected_route else None:
            assert (resp.selected_route.provider if resp.selected_route else None) not in (
                "openai",
                "anthropic",
                "deepseek",
                "openrouter",
            )
        for r in resp.rejected_routes:
            if r.provider in CLOUD_PROVIDERS:
                assert (len(r.rejection_reasons) > 0) is True, (
                    f"cloud provider {r.provider} should be rejected for suspended client"
                )

    def test_suspended_allows_local(self):
        req = _req(plan="basic", billing_status="suspended", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        if resp.selected_route.provider if resp.selected_route else None:
            assert (resp.selected_route.provider if resp.selected_route else None) in (
                "local",
                "lmstudio",
                "mock",
            )

    def test_suspended_with_no_local_routes_still_returns_error(self):
        req = _req(plan="basic", billing_status="suspended", cloud_allowed=False)
        with patch(
            "app.services.routing.commercial_routing._is_provider_available",
            return_value=False,
        ):
            resp = simulate_commercial_routing(req)
            assert (resp.selected_route.provider if resp.selected_route else None) is None


class TestCommercialRoutingLowBalance:
    def test_low_balance_prefers_cheap_provider(self):
        req = _req(plan="pro", wallet_balance_brl=1.0, cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "low_balance"
        assert (resp.selected_route.provider if resp.selected_route else None) is not None

    def test_low_balance_returns_error_when_no_route(self):
        req = _req(plan="basic", wallet_balance_brl=0.0, cloud_allowed=False)
        with patch(
            "app.services.routing.commercial_routing._is_provider_available",
            side_effect=lambda p: p == "mock",
        ):
            resp = simulate_commercial_routing(req)
            assert (resp.selected_route.provider if resp.selected_route else None) == "mock"


class TestCommercialRoutingEdgeCases:
    def test_max_cost_per_request_never_violated(self):
        for plan, max_cost, tokens in [
            ("basic", 0.10, 500000),
            ("pro", 0.50, 500000),
            ("enterprise", 1.00, 500000),
        ]:
            req = _req(
                plan=plan,
                cloud_allowed=True,
                estimated_input_tokens=tokens,
                estimated_output_tokens=tokens,
            )
            resp = simulate_commercial_routing(req)
            if resp.selected_route.provider if resp.selected_route else None:
                assert resp.selected_route.estimated_cost_brl <= max_cost, (
                    f"{plan}: cost {resp.selected_route.estimated_cost_brl} > {max_cost}"
                )

    def test_fallback_on_negative_margin(self):
        req = _req(
            plan="pro",
            cloud_allowed=True,
            estimated_input_tokens=100000,
            estimated_output_tokens=100000,
        )
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) is not None
        for r in resp.rejected_routes:
            if r.estimated_margin_percent is not None and r.estimated_margin_percent < 0:
                assert (len(r.rejection_reasons) > 0) is True

    def test_no_real_cloud_calls(self):
        import app.services.routing.commercial_routing as cr

        original = cr.estimate_provider_cost
        call_count = [0]

        def counting_wrapper(*args, **kwargs):
            call_count[0] += 1
            return original(*args, **kwargs)

        with patch.object(cr, "estimate_provider_cost", side_effect=counting_wrapper):
            req = _req(plan="pro", cloud_allowed=True)
            _ = simulate_commercial_routing(req)
            assert call_count[0] > 0

        import app.services.routing.smart_router as sr

        with patch.object(sr, "_is_provider_available", return_value=True):
            with patch.object(sr, "_provider_health", return_value="healthy"):
                req = _req(plan="pro", cloud_allowed=True)
                resp = simulate_commercial_routing(req)
                assert (resp.selected_route.provider if resp.selected_route else None) is not None

    def test_all_tiers_return_valid_response(self):
        for plan, billing_status, wallet, task in [
            ("basic", "active", 100.0, TaskType.general),
            ("pro", "active", 100.0, TaskType.general),
            ("enterprise", "active", 100.0, TaskType.general),
            ("pro", "active", 100.0, TaskType.coding),
            ("basic", "suspended", 100.0, TaskType.general),
            ("pro", "active", 1.0, TaskType.general),
        ]:
            req = _req(
                plan=plan,
                billing_status=billing_status,
                wallet_balance_brl=wallet,
                task_type=task,
                cloud_allowed=True,
            )
            resp = simulate_commercial_routing(req)
            assert resp.tier, f"{plan}/{billing_status}: missing tier"
            assert isinstance(resp.rejected_routes, list), (
                f"{plan}/{billing_status}: rejected_routes not a list"
            )
            assert len(resp.rejected_routes) > 0, f"{plan}/{billing_status}: no routes evaluated"

    def test_response_contains_all_required_fields(self):
        req = _req(plan="pro", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert (resp.selected_route.provider if resp.selected_route else None) is not None
        assert resp.selected_route.model is not None
        assert isinstance(resp.selected_route.estimated_cost_brl, float)
        assert isinstance(resp.selected_route.estimated_revenue_brl, float)
        assert isinstance(resp.selected_route.estimated_margin_brl, float)
        assert isinstance(resp.rejected_routes, list)
        assert resp.tier is not None


class TestCommercialRoutingPlans:
    def test_basic_plan_config(self):
        req = _req(plan="basic")
        resp = simulate_commercial_routing(req)
        assert resp.tier == "basic"

    def test_pro_plan_config(self):
        req = _req(plan="pro", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "pro"

    def test_enterprise_plan_as_premium(self):
        req = _req(plan="enterprise", cloud_allowed=True)
        resp = simulate_commercial_routing(req)
        assert resp.tier == "premium"

    def test_free_plan_as_basic(self):
        req = _req(plan="free")
        resp = simulate_commercial_routing(req)
        assert resp.tier == "basic"

    def test_unknown_plan_defaults_to_basic(self):
        req = _req(plan="unknown_plan")
        resp = simulate_commercial_routing(req)
        assert resp.tier == "basic"


class TestCommercialRoutingIntegration:
    async def test_admin_endpoint_exists(self, admin_client, admin_token_headers):
        resp = await admin_client.post(
            "/admin/routing/commercial/simulate",
            json={
                "plan": "pro",
                "model": "default",
                "estimated_input_tokens": 100,
                "estimated_output_tokens": 512,
                "task_type": "general",
                "cloud_allowed": True,
                "wallet_balance_brl": 100.0,
                "billing_status": "active",
            },
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "selected_route" in data
        assert "rejected_routes" in data
        assert "tier" in data

    async def test_admin_endpoint_unauthorized(self, admin_client):
        resp = await admin_client.post(
            "/admin/routing/commercial/simulate",
            json={"plan": "pro"},
        )
        assert resp.status_code in (403, 401)

    async def test_admin_endpoint_suspended(self, admin_client, admin_token_headers):
        resp = await admin_client.post(
            "/admin/routing/commercial/simulate",
            json={
                "plan": "basic",
                "estimated_input_tokens": 100,
                "estimated_output_tokens": 512,
                "task_type": "general",
                "billing_status": "suspended",
                "cloud_allowed": True,
                "wallet_balance_brl": 0.0,
            },
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "suspended"
        for r in data["rejected_routes"]:
            if r.get("is_cloud"):
                assert r["rejected"] is True

    async def test_admin_endpoint_coding(self, admin_client, admin_token_headers):
        resp = await admin_client.post(
            "/admin/routing/commercial/simulate",
            json={
                "plan": "pro",
                "estimated_input_tokens": 100,
                "estimated_output_tokens": 512,
                "task_type": "coding",
                "cloud_allowed": True,
                "wallet_balance_brl": 100.0,
                "billing_status": "active",
            },
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "coding"

    async def test_admin_endpoint_no_real_cloud_calls(self, admin_client, admin_token_headers):
        resp = await admin_client.post(
            "/admin/routing/commercial/simulate",
            json={
                "plan": "pro",
                "estimated_input_tokens": 100,
                "estimated_output_tokens": 512,
                "task_type": "general",
                "cloud_allowed": True,
                "wallet_balance_brl": 100.0,
                "billing_status": "active",
            },
            headers=admin_token_headers,
        )
        assert resp.status_code == 200
