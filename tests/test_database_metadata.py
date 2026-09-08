from cats.database.base import Base
import cats.database.models  # noqa: F401


def test_minimum_v2et_tables_registered():
    names = set(Base.metadata.tables)
    required = {
        "SYS_Environment",
        "FIN_Financial_Instrument",
        "TRACE_Flow",
        "PMA_Portfolio",
        "PMA_Portfolio_State",
        "PMA_Portfolio_Decision",
        "PMS_Optimization_Request",
        "PMS_Portfolio_Alternative",
        "SYS_Validation_Result",
        "TAA_Assessment",
        "TEA_Execution",
        "TEA_Execution_State",
        "TEA_Execution_Action",
        "TES_Order",
        "TES_Broker_Action_Result",
        "TSS_Measurement_Set",
        "TSS_Measurement",
    }
    assert required.issubset(names)
