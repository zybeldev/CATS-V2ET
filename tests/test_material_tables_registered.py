from cats.database.base import Base
import cats.database.models  # noqa


def test_step14_material_tables_registered():
    for name in [
        "TAA_Assessment_Evidence",
        "PMS_Alternative_Position",
        "PMA_Decision_Target",
        "SYS_Validation_Rule_Result",
        "TEA_Execution_Result",
    ]:
        assert name in Base.metadata.tables
