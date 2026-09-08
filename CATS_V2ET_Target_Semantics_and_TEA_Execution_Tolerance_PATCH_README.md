# CATS V2ET — Target Semantics + TEA Execution Tolerance Patch

## Purpose

Correct the semantic defect exposed by the first AAPL PAPER vertical slice while preserving the established CATS authority boundaries.

Observed prior behavior:

- TAA assessment: positive
- PMS exact target quantity: slightly below current quantity
- PMA decision_type: BUY_OR_INCREASE
- TEA execution: SELL a very small delta

The execution arithmetic was correct, but the PMA decision label did not describe the selected PMS target transition. In addition, the small residual should not require a broker order when the current position already satisfies the authorized target within the standard TEA execution tolerance.

## Implemented behavior

### 1. PMA target-transition classification

After PMA selects a feasible PMS PortfolioAlternative, PMA classifies the exact transition from current Portfolio State to the selected target:

- only positive quantity deltas -> BUY_OR_INCREASE
- only negative quantity deltas -> SELL_OR_REDUCE
- mixed deltas -> REBALANCE
- exact zero deltas -> NO_CHANGE

TAA/PMA reasoning still determines whether optimization is warranted. PMS still constructs the exact target. PMA does not edit the PMS alternative.

### 2. SYS direction-consistency guard

SYS now performs a fail-closed `DECISION_DIRECTION_CONSISTENCY` rule using signed target deltas.

Examples:

- BUY_OR_INCREASE + sell delta -> FAIL
- SELL_OR_REDUCE + buy delta -> FAIL
- correctly aligned direction -> PASS

### 3. TEA standard execution tolerance

TEA now implements the already-established standard execution-completion tolerance:

- default target-weight tolerance: +/- 0.05 percentage points (`0.0005` in portfolio-weight units)
- applied uniformly by TEA
- PMA does not define or modify this tolerance

Before creating an execution state/order, TEA compares broker-confirmed current portfolio weight with the PMA-authorized target weight.

If the target is already satisfied within tolerance:

- no execution state is created
- no TES call occurs
- no broker order occurs
- the existing broker-confirmed Portfolio State remains authoritative
- the residual delta remains part of actual state and is naturally incorporated into the next PMS rebalance

### 4. Operator/UI visibility

When the target is already satisfied, the vertical-slice visibility report now shows:

- `TEA EXECUTION: TARGET_ALREADY_SATISFIED`
- current weight
- target weight
- weight delta
- execution tolerance
- `BROKER RESULT: NO_ORDER_REQUIRED`
- `RECONCILIATION: TARGET_WITHIN_TOLERANCE`
- `ACCEPTED PORTFOLIO STATE: UNCHANGED`

The PMA visibility stage also shows current weight, target weight, weight delta, and whether the target is within TEA tolerance.

## AAPL interpretation

For the first real AAPL flow, the exact selected target was slightly below the current position. PMA should therefore describe the exact target transition as `SELL_OR_REDUCE`, but because the difference is within the standard TEA tolerance, TEA should create no order.

This preserves both boundaries:

- PMA owns exact portfolio intent.
- TEA owns execution-completion tolerance.

At the next rebalance, PMS starts from the actual current Portfolio State, so the tolerated residual is handled indirectly by the next optimization rather than by a separate cleanup queue.

## Validation performed in the supplied source subset

Focused regression set covering PMA, SYS, TEA, full-chain persistence, recovery, and flow visibility:

- 18 passed

Broader available tests whose supporting scripts were present:

- 91 passed
- 1 skipped

The remaining test failures in the supplied source subset are due only to scripts that were not included in the original uploaded source package (for example paper_operator.py and evaluation scripts). Run the complete local project suite after applying the patch.

Expected complete local suite count from the current 107-test baseline:

- 112 passed

No PAPER run is required to validate this patch initially.
