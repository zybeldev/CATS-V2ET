from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cats.database import models


class PortfolioRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_current_state(self, portfolio_id: str):
        stmt = (
            select(models.PortfolioState)
            .where(models.PortfolioState.portfolio_id == portfolio_id)
            .order_by(models.PortfolioState.effective_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def add_state(self, state: models.PortfolioState):
        self.session.add(state)
        return state


class AssessmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, assessment: models.AssessmentRecord):
        self.session.add(assessment)
        return assessment

    def latest_for_instrument(self, financial_instrument_id: str):
        stmt = (
            select(models.AssessmentRecord)
            .where(
                models.AssessmentRecord.financial_instrument_id
                == financial_instrument_id
            )
            .order_by(models.AssessmentRecord.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class OptimizationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_request(self, request: models.OptimizationRequestRecord):
        self.session.add(request)
        return request

    def add_alternative(self, alternative: models.PortfolioAlternativeRecord):
        self.session.add(alternative)
        return alternative


class ValidationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, result: models.ValidationResultRecord):
        self.session.add(result)
        return result

    def latest_for_decision(self, portfolio_decision_id: str):
        stmt = (
            select(models.ValidationResultRecord)
            .where(
                models.ValidationResultRecord.portfolio_decision_id
                == portfolio_decision_id
            )
            .order_by(models.ValidationResultRecord.validated_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class ExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_execution(self, execution: models.ExecutionRecord):
        self.session.add(execution)
        return execution

    def add_state(self, state: models.ExecutionStateRecord):
        self.session.add(state)
        return state

    def add_action(self, action: models.ExecutionActionRecord):
        self.session.add(action)
        return action

    def current_state(self, execution_id: str):
        stmt = (
            select(models.ExecutionStateRecord)
            .where(models.ExecutionStateRecord.execution_id == execution_id)
            .order_by(models.ExecutionStateRecord.effective_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class ConfigurationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_current(self, environment_id: str):
        stmt = (
            select(models.ConfigurationVersion)
            .where(
                models.ConfigurationVersion.environment_id == environment_id,
                models.ConfigurationVersion.is_current.is_(True),
            )
            .limit(1)
        )
        return self.session.scalar(stmt)

    def add(self, configuration: models.ConfigurationVersion):
        self.session.add(configuration)
        return configuration


class TSSRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_measurement_set(self, measurement_set: models.TSSMeasurementSetRecord):
        self.session.add(measurement_set)
        return measurement_set

    def add_measurement(self, measurement: models.TSSMeasurementRecord):
        self.session.add(measurement)
        return measurement
