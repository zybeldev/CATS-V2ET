from sqlalchemy import create_engine, text

from cats.ui.read_model import CatsUiReadModel


def make_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE "TRACE_Flow" (flow_id TEXT PRIMARY KEY, status TEXT, created_at TEXT)'))
        conn.execute(text('CREATE TABLE "TAA_Assessment" (assessment_id TEXT PRIMARY KEY, flow_id TEXT, status TEXT, assessment_type TEXT, horizon TEXT, confidence NUMERIC, summary TEXT, created_at TEXT)'))
        conn.execute(text('CREATE TABLE "PMA_Portfolio_Decision" (portfolio_decision_id TEXT PRIMARY KEY, source_portfolio_state_id TEXT, flow_id TEXT, decision_type TEXT, status TEXT, created_at TEXT)'))
        conn.execute(text('CREATE TABLE "PMA_Position" (portfolio_state_id TEXT, financial_instrument_id TEXT, quantity NUMERIC)'))
        conn.execute(text('CREATE TABLE "PMA_Decision_Target" (portfolio_decision_id TEXT, financial_instrument_id TEXT, target_quantity NUMERIC, target_weight NUMERIC)'))
        conn.execute(text('CREATE TABLE "FIN_Financial_Instrument" (financial_instrument_id TEXT PRIMARY KEY, symbol TEXT)'))
        conn.execute(text('CREATE TABLE "TSS_Measurement_Set" (tss_measurement_set_id TEXT PRIMARY KEY, financial_instrument_id TEXT, flow_id TEXT, observed_at TEXT, status TEXT)'))
        conn.execute(text('CREATE TABLE "TSS_Measurement" (tss_measurement_id TEXT PRIMARY KEY, tss_measurement_set_id TEXT, measurement_type TEXT, value_numeric NUMERIC, value_text TEXT, unit TEXT, status TEXT)'))
        conn.execute(text('CREATE TABLE "SYS_Validation_Result" (validation_result_id TEXT PRIMARY KEY, flow_id TEXT, result TEXT)'))
        conn.execute(text('CREATE TABLE "TEA_Execution" (execution_id TEXT PRIMARY KEY, flow_id TEXT, status TEXT, side TEXT, target_quantity NUMERIC, certainty_status TEXT)'))
        conn.execute(text('CREATE TABLE "TES_Order" (order_id TEXT PRIMARY KEY, flow_id TEXT, side TEXT, quantity NUMERIC, status TEXT)'))
        conn.execute(text('CREATE TABLE "TES_Fill" (fill_id TEXT PRIMARY KEY, flow_id TEXT, quantity NUMERIC, price NUMERIC)'))
        conn.execute(text('CREATE TABLE "TEA_Reconciliation" (reconciliation_id TEXT PRIMARY KEY, flow_id TEXT, result TEXT, certainty_after TEXT)'))
        conn.execute(text('CREATE TABLE "TEA_Execution_Result" (execution_result_id TEXT PRIMARY KEY, flow_id TEXT, status TEXT, certainty_status TEXT)'))

        conn.execute(text("INSERT INTO \"TRACE_Flow\" VALUES ('f1','COMPLETED','2026-09-01T10:00:00Z')"))
        conn.execute(text("INSERT INTO \"TRACE_Flow\" VALUES ('f2','ACTIVE','2026-09-02T10:00:00Z')"))
        conn.execute(text("INSERT INTO \"TAA_Assessment\" VALUES ('a1','f2','FINAL','CANDIDATE','TACTICAL',0.75,'grounded assessment','2026-09-02T10:01:00Z')"))
        conn.execute(text("INSERT INTO \"PMA_Portfolio_Decision\" VALUES ('d1','s1','f2','SELL_OR_REDUCE','FINAL','2026-09-02T10:02:00Z')"))
        conn.execute(text("INSERT INTO \"FIN_Financial_Instrument\" VALUES ('i1','AAPL')"))
        conn.execute(text("INSERT INTO \"PMA_Position\" VALUES ('s1','i1',30.786674449)"))
        conn.execute(text("INSERT INTO \"PMA_Decision_Target\" VALUES ('d1','i1',30.726077695,0.10)"))
        conn.execute(text("INSERT INTO \"TSS_Measurement_Set\" VALUES ('ms1','i1','f2','2026-09-02T10:00:30Z','FINAL')"))
        conn.execute(text("INSERT INTO \"TSS_Measurement\" VALUES ('m1','ms1','LAST_PRICE',326.504,NULL,'USD','FINAL')"))
        conn.execute(text("INSERT INTO \"SYS_Validation_Result\" VALUES ('v1','f2','PASS')"))
        conn.execute(text("INSERT INTO \"TEA_Execution\" VALUES ('e1','f2','COMPLETED','SELL',0.060596754,'CONFIRMED')"))
        conn.execute(text("INSERT INTO \"TES_Order\" VALUES ('o1','f2','SELL',0.060596754,'FILLED')"))
        conn.execute(text("INSERT INTO \"TES_Fill\" VALUES ('fill1','f2',0.060596754,326.504)"))
        conn.execute(text("INSERT INTO \"TEA_Reconciliation\" VALUES ('r1','f2','PASS','CONFIRMED')"))
        conn.execute(text("INSERT INTO \"TEA_Execution_Result\" VALUES ('er1','f2','COMPLETED','CONFIRMED')"))
    return engine


def test_latest_flows_orders_newest_first():
    model = CatsUiReadModel(make_engine())
    rows = model.latest_flows()
    assert [row["flow_id"] for row in rows] == ["f2", "f1"]


def test_stage_summary_is_read_only_projection():
    model = CatsUiReadModel(make_engine())
    taa = next(s for s in model.stage_summaries("f2") if s.label == "TAA")
    assert taa.available is True
    assert taa.flow_linked is True
    assert taa.count == 1
    assert taa.status == "FINAL"


def test_selected_decision_transition_uses_actual_current_state():
    model = CatsUiReadModel(make_engine())
    rows = model.selected_decision_transition("f2")
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["decision_type"] == "SELL_OR_REDUCE"
    assert abs(rows[0]["delta_quantity"] - (-0.060596754)) < 1e-9


def test_selected_decision_transition_adds_usd_equivalence_from_tss_price():
    model = CatsUiReadModel(make_engine())
    row = model.selected_decision_transition("f2")[0]
    assert row["reference_price"] == 326.504
    assert row["reference_price_type"] == "LAST_PRICE"
    assert abs(row["current_value_usd"] - (30.786674449 * 326.504)) < 1e-6
    assert abs(row["target_value_usd"] - (30.726077695 * 326.504)) < 1e-6
    assert abs(row["delta_value_usd"] - (-0.060596754 * 326.504)) < 1e-6


def test_taa_reasoning_projection_preserves_horizon_confidence_and_summary():
    model = CatsUiReadModel(make_engine())
    taa = model.taa_reasoning("f2")
    assert taa is not None
    assert taa["horizon"] == "TACTICAL"
    assert float(taa["confidence"]) == 0.75
    assert taa["summary"] == "grounded assessment"


def test_execution_snapshot_calculates_human_trade_value():
    model = CatsUiReadModel(make_engine())
    snapshot = model.execution_snapshot("f2")
    assert snapshot["decision_type"] == "SELL_OR_REDUCE"
    assert snapshot["validation"] == "PASS"
    assert snapshot["order_side"] == "SELL"
    assert snapshot["certainty"] == "CONFIRMED"
    assert abs(snapshot["trade_value_usd"] - (0.060596754 * 326.504)) < 1e-6


def make_historical_taa_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            'CREATE TABLE "TRACE_Flow" ('
            'flow_id TEXT PRIMARY KEY, status TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TAA_Assessment" ('
            'assessment_id TEXT PRIMARY KEY, flow_id TEXT, status TEXT, '
            'assessment_type TEXT, confidence NUMERIC, assessment_summary TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            "INSERT INTO \"TRACE_Flow\" VALUES ('old-flow','COMPLETED','2026-09-01T10:00:00Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"TAA_Assessment\" VALUES ("
            "'old-a','old-flow','FINAL','TACTICAL',0.75,"
            "'Apple tactical assessment narrative','2026-09-01T10:01:00Z')"
        ))
    return engine


def test_taa_historical_assessment_type_is_normalized_to_horizon():
    model = CatsUiReadModel(make_historical_taa_engine())
    taa = model.taa_reasoning("old-flow")
    assert taa is not None
    assert taa["horizon"] == "TACTICAL"
    assert taa["assessment_type"] == "CANDIDATE"
    assert taa["normalized_historical_shape"] is True
    assert taa["raw_assessment_type"] == "TACTICAL"


def test_taa_historical_narrative_alias_is_recovered():
    model = CatsUiReadModel(make_historical_taa_engine())
    taa = model.taa_reasoning("old-flow")
    assert taa is not None
    assert taa["summary"] == "Apple tactical assessment narrative"


def test_taa_historical_duplicate_horizon_field_still_normalizes_assessment_type():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            'CREATE TABLE "TRACE_Flow" ('
            'flow_id TEXT PRIMARY KEY, status TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TAA_Assessment" ('
            'assessment_id TEXT PRIMARY KEY, flow_id TEXT, status TEXT, '
            'assessment_type TEXT, horizon TEXT, confidence NUMERIC, '
            'assessment_summary TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            "INSERT INTO \"TRACE_Flow\" VALUES "
            "('mixed-flow','COMPLETED','2026-09-01T10:00:00Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"TAA_Assessment\" VALUES ("
            "'mixed-a','mixed-flow','FINAL','TACTICAL','TACTICAL',0.75,"
            "'Apple tactical assessment narrative','2026-09-01T10:01:00Z')"
        ))

    taa = CatsUiReadModel(engine).taa_reasoning("mixed-flow")
    assert taa is not None
    assert taa["horizon"] == "TACTICAL"
    assert taa["assessment_type"] == "CANDIDATE"
    assert taa["normalized_historical_shape"] is True


def make_indirect_lineage_engine():
    """Schema shape matching the persisted V2ET broker/material lineage."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            'CREATE TABLE "TRACE_Flow" ('
            'flow_id TEXT PRIMARY KEY, status TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "PMA_Portfolio_Decision" ('
            'portfolio_decision_id TEXT PRIMARY KEY, source_portfolio_state_id TEXT, '
            'flow_id TEXT, decision_type TEXT, status TEXT, created_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "PMA_Portfolio_State" ('
            'portfolio_state_id TEXT PRIMARY KEY, source_portfolio_decision_id TEXT, '
            'effective_at TEXT, status TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "PMA_Position" ('
            'portfolio_state_id TEXT, financial_instrument_id TEXT, quantity NUMERIC, '
            'market_value NUMERIC)'
        ))
        conn.execute(text(
            'CREATE TABLE "PMA_Decision_Target" ('
            'portfolio_decision_id TEXT, financial_instrument_id TEXT, '
            'target_quantity NUMERIC, target_weight NUMERIC)'
        ))
        conn.execute(text(
            'CREATE TABLE "FIN_Financial_Instrument" ('
            'financial_instrument_id TEXT PRIMARY KEY, symbol TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "SYS_Validation_Result" ('
            'validation_result_id TEXT PRIMARY KEY, flow_id TEXT, result TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TEA_Execution" ('
            'execution_id TEXT PRIMARY KEY, portfolio_decision_id TEXT, '
            'financial_instrument_id TEXT, flow_id TEXT, status TEXT, side TEXT, '
            'target_quantity NUMERIC, certainty_status TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TES_Order" ('
            'order_id TEXT PRIMARY KEY, execution_id TEXT, financial_instrument_id TEXT, '
            'side TEXT, quantity NUMERIC, status TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TES_Fill" ('
            'fill_id TEXT PRIMARY KEY, order_id TEXT, execution_id TEXT, '
            'quantity NUMERIC, price NUMERIC, filled_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TEA_Reconciliation" ('
            'reconciliation_id TEXT PRIMARY KEY, execution_id TEXT, '
            'certainty_status TEXT, resolved BOOLEAN, broker_status TEXT, '
            'filled_quantity NUMERIC, average_fill_price NUMERIC, reconciled_at TEXT)'
        ))
        conn.execute(text(
            'CREATE TABLE "TEA_Execution_Result" ('
            'execution_result_id TEXT PRIMARY KEY, execution_id TEXT, '
            'result_status TEXT, verified BOOLEAN, created_at TEXT)'
        ))

        conn.execute(text(
            "INSERT INTO \"TRACE_Flow\" VALUES "
            "('f-old','COMPLETED','2026-09-02T15:36:12Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"PMA_Portfolio_Decision\" VALUES "
            "('d-old','s-before','f-old','BUY_OR_INCREASE','FINAL','2026-09-02T15:36:20Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"PMA_Portfolio_State\" VALUES "
            "('s-after','d-old','2026-09-02T15:36:43Z','ACCEPTED')"
        ))
        conn.execute(text(
            "INSERT INTO \"PMA_Position\" VALUES "
            "('s-before','i1',30.786674449,NULL),"
            "('s-after','i1',30.726077696,10030.00)"
        ))
        conn.execute(text(
            "INSERT INTO \"PMA_Decision_Target\" VALUES "
            "('d-old','i1',30.726077695195773,0.10)"
        ))
        conn.execute(text("INSERT INTO \"FIN_Financial_Instrument\" VALUES ('i1','AAPL')"))
        conn.execute(text("INSERT INTO \"SYS_Validation_Result\" VALUES ('v1','f-old','PASS')"))
        conn.execute(text(
            "INSERT INTO \"TEA_Execution\" VALUES "
            "('e1','d-old','i1','f-old','COMPLETED','SELL',0.060596753804226466,'CONFIRMED')"
        ))
        conn.execute(text(
            "INSERT INTO \"TES_Order\" VALUES "
            "('o1','e1','i1','SELL',0.060596753,'FILLED')"
        ))
        conn.execute(text(
            "INSERT INTO \"TES_Fill\" VALUES "
            "('fill1','o1','e1',0.060596753,326.504,'2026-09-02T15:36:40Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"TEA_Reconciliation\" VALUES "
            "('r1','e1','CONFIRMED',1,'filled',0.060596753,326.504,'2026-09-02T15:36:41Z')"
        ))
        conn.execute(text(
            "INSERT INTO \"TEA_Execution_Result\" VALUES "
            "('er1','e1','COMPLETED',1,'2026-09-02T15:36:42Z')"
        ))
    return engine


def test_indirect_execution_lineage_recovers_order_fill_reconciliation_and_state():
    model = CatsUiReadModel(make_indirect_lineage_engine())
    assert len(model.rows_related_to_flow("TES_Order", "f-old")) == 1
    assert len(model.rows_related_to_flow("TES_Fill", "f-old")) == 1
    assert len(model.rows_related_to_flow("TEA_Reconciliation", "f-old")) == 1
    states = model.rows_related_to_flow("PMA_Portfolio_State", "f-old")
    assert len(states) == 1
    assert states[0]["status"] == "ACCEPTED"


def test_broker_fill_is_price_fallback_when_tss_not_persisted():
    model = CatsUiReadModel(make_indirect_lineage_engine())
    row = model.selected_decision_transition("f-old")[0]
    assert row["reference_price"] == 326.504
    assert row["reference_price_type"] == "BROKER_FILL"
    assert abs(row["delta_value_usd"] - (-0.060596753804226466 * 326.504)) < 1e-6


def test_execution_snapshot_uses_indirect_lineage_and_final_position():
    model = CatsUiReadModel(make_indirect_lineage_engine())
    snapshot = model.execution_snapshot("f-old")
    assert snapshot["order_side"] == "SELL"
    assert snapshot["order_status"] == "FILLED"
    assert snapshot["fill_quantity"] == 0.060596753
    assert snapshot["fill_price"] == 326.504
    assert snapshot["reconciliation"] == "RESOLVED"
    assert snapshot["reconciliation_certainty"] == "CONFIRMED"
    assert snapshot["final_position_quantity"] == 30.726077696
    assert snapshot["final_position_value_usd"] == 10030.0


def test_stage_summary_treats_indirect_material_lineage_as_flow_linked():
    model = CatsUiReadModel(make_indirect_lineage_engine())
    summaries = {summary.label: summary for summary in model.stage_summaries("f-old")}
    assert summaries["Order"].flow_linked is True
    assert summaries["Order"].status == "FILLED"
    assert summaries["Fill"].flow_linked is True
    assert summaries["Reconciliation"].status == "RESOLVED"
    assert summaries["Execution Result"].status == "COMPLETED"
    assert summaries["Portfolio State"].status == "ACCEPTED"
