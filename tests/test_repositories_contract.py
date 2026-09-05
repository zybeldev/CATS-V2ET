import inspect

from cats.repositories import (
    AssessmentRepository,
    ConfigurationRepository,
    ExecutionRepository,
    OptimizationRepository,
    PortfolioRepository,
    TSSRepository,
    ValidationRepository,
)


def test_domain_repositories_are_concrete_classes():
    repos = [
        AssessmentRepository,
        ConfigurationRepository,
        ExecutionRepository,
        OptimizationRepository,
        PortfolioRepository,
        TSSRepository,
        ValidationRepository,
    ]
    assert all(inspect.isclass(repo) for repo in repos)
