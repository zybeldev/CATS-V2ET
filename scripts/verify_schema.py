from __future__ import annotations

from sqlalchemy import inspect

from cats.configuration import get_settings
from cats.database import create_engine_from_settings


REQUIRED_TABLES = {
    "SYS_Environment",
    "FIN_Financial_Instrument",
    "TRACE_Flow",
    "TRACE_Event",
    "TRACE_Provenance_Link",
    "TRACE_Lineage_Link",
    "TAA_Evidence_Item",
    "TAA_Assessment",
    "TAA_Assessment_Evidence",
    "PMS_Optimization_Request",
    "PMS_Portfolio_Alternative",
    "PMS_Alternative_Position",
    "PMA_Portfolio",
    "PMA_Portfolio_State",
    "PMA_Position",
    "PMA_Portfolio_Decision",
    "PMA_Decision_Target",
    "SYS_Validation_Result",
    "SYS_Validation_Rule_Result",
    "TEA_Execution",
    "TEA_Execution_State",
    "TEA_Execution_Action",
    "TEA_Reconciliation",
    "TEA_Execution_Result",
    "TES_Order",
    "TES_Broker_Action_Result",
    "TES_Fill",
}


def main():
    engine = create_engine_from_settings(get_settings())
    tables = set(inspect(engine).get_table_names())
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise SystemExit("Schema verification FAILED. Missing: " + ", ".join(missing))
    print(f"Schema verification: PASS ({len(REQUIRED_TABLES)} required tables present)")


if __name__ == "__main__":
    main()
