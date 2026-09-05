from __future__ import annotations

import os
from dataclasses import dataclass


SYS_PROFILE_NORMAL = "NORMAL"
SYS_PROFILE_AGGRESSIVE_PAPER_TEST = "AGGRESSIVE_PAPER_TEST"


def active_sys_profile() -> str:
    """Return the active SYS policy profile for this process.

    The profile is deliberately process-scoped. V2ET's normal behavior remains
    unchanged unless the operator explicitly exports CATS_SYS_PROFILE before
    starting the PAPER runtime.
    """
    return os.getenv("CATS_SYS_PROFILE", SYS_PROFILE_NORMAL).strip().upper()


@dataclass(frozen=True)
class GovernedConfiguration:
    configuration_version_id: str
    environment_code: str
    permitted_instrument_type: str = "EQUITY"
    permitted_trading_environment: str = "PAPER"
    max_position_weight: float = 0.25
    max_total_equity_exposure: float = 1.0
    min_cash_reserve_weight: float = 0.05
    max_order_value: float = 25_000.0
    max_order_quantity: float = 1_000.0
    allowed_order_types: tuple[str, ...] = ("MARKET", "LIMIT")

    def __post_init__(self):
        profile = active_sys_profile()

        if profile not in {SYS_PROFILE_NORMAL, SYS_PROFILE_AGGRESSIVE_PAPER_TEST}:
            raise ValueError(f"Unsupported CATS_SYS_PROFILE: {profile}")

        if profile == SYS_PROFILE_AGGRESSIVE_PAPER_TEST:
            # Temporary test-only policy relaxation. The profile can never be
            # activated for a non-PAPER environment. It does not bypass SYS
            # direction checks, instrument restrictions, broker reconciliation,
            # provenance, or fail-closed behavior.
            if (
                self.environment_code != "PAPER"
                or self.permitted_trading_environment != "PAPER"
            ):
                raise ValueError(
                    "AGGRESSIVE_PAPER_TEST may be used only with PAPER trading."
                )

            # Bounded PAPER-test ceilings. These are intentionally permissive
            # enough to exercise PMA -> SYS -> TEA -> TES without becoming
            # unlimited or disabling governance.
            object.__setattr__(
                self,
                "max_position_weight",
                max(self.max_position_weight, 0.25),
            )
            object.__setattr__(self, "max_total_equity_exposure", 0.99)
            object.__setattr__(
                self,
                "min_cash_reserve_weight",
                min(self.min_cash_reserve_weight, 0.01),
            )
            object.__setattr__(
                self,
                "max_order_value",
                max(self.max_order_value, 50_000.0),
            )
            object.__setattr__(
                self,
                "max_order_quantity",
                max(self.max_order_quantity, 5_000.0),
            )

        if not 0 <= self.max_position_weight <= 1:
            raise ValueError("max_position_weight must be between 0 and 1")
        if not 0 <= self.max_total_equity_exposure <= 1:
            raise ValueError("max_total_equity_exposure must be between 0 and 1")
        if not 0 <= self.min_cash_reserve_weight <= 1:
            raise ValueError("min_cash_reserve_weight must be between 0 and 1")
        if self.max_order_value <= 0:
            raise ValueError("max_order_value must be positive")
        if self.max_order_quantity <= 0:
            raise ValueError("max_order_quantity must be positive")
