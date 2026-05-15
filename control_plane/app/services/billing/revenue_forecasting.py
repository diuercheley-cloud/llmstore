import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

import numpy as np
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.commercial_revenue_forecast import CommercialRevenueForecast
from app.models.request_financial import RequestFinancial
from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.core.time import utc_now


class RevenueForecastingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def forecast_revenue(self, window_days: int = 30, method: str = None) -> CommercialRevenueForecast:
        """Forecast total revenue for the next N days."""
        return await self._run_forecast(
            forecast_type="revenue",
            window_days=window_days,
            method=method or self.settings.commercial_revenue_forecast_method,
        )

    async def forecast_cost(self, window_days: int = 30, method: str = None) -> CommercialRevenueForecast:
        """Forecast total cost for the next N days."""
        return await self._run_forecast(
            forecast_type="cost",
            window_days=window_days,
            method=method or self.settings.commercial_revenue_forecast_method,
        )

    async def forecast_margin(self, window_days: int = 30, method: str = None) -> CommercialRevenueForecast:
        """Forecast total margin for the next N days."""
        return await self._run_forecast(
            forecast_type="margin",
            window_days=window_days,
            method=method or self.settings.commercial_revenue_forecast_method,
        )

    async def forecast_qos_billing(self, window_days: int = 30, method: str = None) -> CommercialRevenueForecast:
        """Forecast QoS billing revenue for the next N days."""
        return await self._run_forecast(
            forecast_type="qos_billing",
            window_days=window_days,
            method=method or self.settings.commercial_revenue_forecast_method,
        )

    async def forecast_by_client(self, client_id: uuid.UUID, window_days: int = 30, method: str = None) -> CommercialRevenueForecast:
        """Forecast revenue for a specific client."""
        return await self._run_forecast(
            forecast_type="revenue",
            client_id=client_id,
            window_days=window_days,
            method=method or self.settings.commercial_revenue_forecast_method,
        )

    async def _run_forecast(
        self,
        forecast_type: str,
        window_days: int,
        method: str,
        client_id: Optional[uuid.UUID] = None,
        qos_tier: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CommercialRevenueForecast:
        # 1. Gather historical data (last 90 days)
        history_days = 90
        end_date = utc_now()
        start_date = end_date - timedelta(days=history_days)

        historical_data = await self._get_historical_series(
            forecast_type, start_date, end_date, client_id, qos_tier, provider, model
        )

        if len(historical_data) < self.settings.commercial_revenue_forecast_min_samples:
            # Not enough data for a reliable forecast
            return self._create_empty_forecast(
                forecast_type, window_days, method, client_id, qos_tier, provider, model
            )

        # 2. Apply forecasting method
        values = [float(v) for v in historical_data]
        
        if method == "moving_average":
            predicted, lower, upper, confidence = self._forecast_moving_average(values, window_days)
        elif method == "ewma":
            predicted, lower, upper, confidence = self._forecast_ewma(values, window_days)
        elif method == "linear_trend":
            predicted, lower, upper, confidence = self._forecast_linear_trend(values, window_days)
        else:
            predicted, lower, upper, confidence = self._forecast_moving_average(values, window_days)

        # 3. Save and return
        forecast = CommercialRevenueForecast(
            forecast_type=forecast_type,
            client_id=client_id,
            qos_tier=qos_tier,
            provider=provider,
            model=model,
            period_start=end_date,
            period_end=end_date + timedelta(days=window_days),
            forecast_window_days=window_days,
            predicted_amount_brl=Decimal(str(round(predicted, 6))),
            lower_bound_brl=Decimal(str(round(lower, 6))),
            upper_bound_brl=Decimal(str(round(upper, 6))),
            confidence=confidence,
            method=method,
        )
        self.session.add(forecast)
        await self.session.commit()
        return forecast

    async def _get_historical_series(
        self,
        forecast_type: str,
        start_date: datetime,
        end_date: datetime,
        client_id: Optional[uuid.UUID],
        qos_tier: Optional[str],
        provider: Optional[str],
        model: Optional[str],
    ) -> List[Decimal]:
        """Get daily aggregate series from DB."""
        if forecast_type == "qos_billing":
            stmt = select(
                func.date_trunc('day', CommercialQoSBillingRecord.created_at).label('day'),
                func.sum(CommercialQoSBillingRecord.billable_amount_brl).label('val')
            ).where(
                CommercialQoSBillingRecord.created_at >= start_date,
                CommercialQoSBillingRecord.created_at <= end_date
            )
            if client_id:
                stmt = stmt.where(CommercialQoSBillingRecord.client_id == client_id)
            if qos_tier:
                stmt = stmt.where(CommercialQoSBillingRecord.qos_tier == qos_tier)
            
            stmt = stmt.group_by('day').order_by('day')
        else:
            # revenue, cost, margin
            val_col = RequestFinancial.customer_price_brl
            if forecast_type == "cost":
                val_col = RequestFinancial.provider_cost_brl
            elif forecast_type == "margin":
                val_col = RequestFinancial.gross_profit_brl

            stmt = select(
                func.date_trunc('day', RequestFinancial.created_at).label('day'),
                func.sum(val_col).label('val')
            ).where(
                RequestFinancial.created_at >= start_date,
                RequestFinancial.created_at <= end_date
            )
            if client_id:
                stmt = stmt.where(RequestFinancial.client_id == client_id)
            if provider:
                stmt = stmt.where(RequestFinancial.provider == provider)
            if model:
                stmt = stmt.where(RequestFinancial.model == model)
            
            stmt = stmt.group_by('day').order_by('day')

        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Fill gaps with 0
        date_map = {row.day.date(): row.val for row in rows}
        series = []
        curr = start_date.date()
        while curr <= end_date.date():
            series.append(date_map.get(curr, Decimal("0.00")))
            curr += timedelta(days=1)
        
        return series

    def _forecast_moving_average(self, values: List[float], window_days: int):
        avg_daily = np.mean(values[-7:]) if len(values) >= 7 else np.mean(values)
        std_daily = np.std(values[-7:]) if len(values) >= 7 else np.std(values)
        
        predicted = avg_daily * window_days
        # Simple interval: 1.96 * std * sqrt(window)
        margin = 1.96 * std_daily * np.sqrt(window_days)
        
        confidence = "medium"
        if len(values) < 14 or sum(values) == 0:
            confidence = "low"
        elif std_daily < (avg_daily * 0.1) and avg_daily > 0:
            confidence = "high"
            
        return max(0, predicted), max(0, predicted - margin), predicted + margin, confidence

    def _forecast_ewma(self, values: List[float], window_days: int):
        alpha = 0.3
        ewma = values[0]
        for val in values[1:]:
            ewma = alpha * val + (1 - alpha) * ewma
            
        predicted = ewma * window_days
        std_daily = np.std(values[-14:]) if len(values) >= 14 else np.std(values)
        margin = 1.96 * std_daily * np.sqrt(window_days)
        
        confidence = "medium"
        if len(values) < 14 or sum(values) == 0:
            confidence = "low"
        elif std_daily < (ewma * 0.1) and ewma > 0:
            confidence = "high"
            
        return max(0, predicted), max(0, predicted - margin), predicted + margin, confidence

    def _forecast_linear_trend(self, values: List[float], window_days: int):
        # Use only the last 30 days for trend to be more reactive
        relevant_values = values[-30:] if len(values) > 30 else values
        x = np.arange(len(relevant_values))
        y = np.array(relevant_values)
        
        if len(relevant_values) < 2:
            return self._forecast_moving_average(relevant_values, window_days)
            
        slope, intercept = np.polyfit(x, y, 1)
        
        # Predicted sum of linear trend over window_days
        start_x = len(relevant_values)
        predicted = 0
        for i in range(start_x, start_x + window_days):
            predicted += max(0, slope * i + intercept)
            
        std_err = np.std(y - (slope * x + intercept))
        margin = 1.96 * std_err * np.sqrt(window_days)
        
        confidence = "medium"
        if len(relevant_values) < 14 or sum(relevant_values) == 0:
            confidence = "low"
        
        return max(0, predicted), max(0, predicted - margin), predicted + margin, confidence

    def _create_empty_forecast(self, f_type, window, method, client_id, qos_tier, provider, model):
        now = utc_now()
        return CommercialRevenueForecast(
            forecast_type=f_type,
            client_id=client_id,
            qos_tier=qos_tier,
            provider=provider,
            model=model,
            period_start=now,
            period_end=now + timedelta(days=window),
            forecast_window_days=window,
            predicted_amount_brl=Decimal("0.00"),
            lower_bound_brl=Decimal("0.00"),
            upper_bound_brl=Decimal("0.00"),
            confidence="low",
            method=method,
        )
