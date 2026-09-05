from scripts.verify_schema import REQUIRED_TABLES


def test_schema_manifest_contains_complete_material_chain():
    required = {
        "TAA_Evidence_Item",
        "TAA_Assessment",
        "PMS_Optimization_Request",
        "PMS_Portfolio_Alternative",
        "PMA_Portfolio_Decision",
        "SYS_Validation_Result",
        "TEA_Execution",
        "TEA_Reconciliation",
        "TEA_Execution_Result",
        "TES_Order",
        "TES_Fill",
        "PMA_Portfolio_State",
        "TRACE_Provenance_Link",
        "TRACE_Lineage_Link",
    }
    assert required.issubset(REQUIRED_TABLES)
