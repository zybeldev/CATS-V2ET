from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


STAGE_TABLES: tuple[tuple[str, str], ...] = (
    ("Evidence", "TAA_Evidence_Item"),
    ("Retrieval", "TAA_Retrieval_Result"),
    ("TSS", "TSS_Measurement_Set"),
    ("TAA", "TAA_Assessment"),
    ("PMS Request", "PMS_Optimization_Request"),
    ("PMA", "PMA_Portfolio_Decision"),
    ("SYS", "SYS_Validation_Result"),
    ("TEA", "TEA_Execution"),
    ("Order", "TES_Order"),
    ("Fill", "TES_Fill"),
    ("Reconciliation", "TEA_Reconciliation"),
    ("Execution Result", "TEA_Execution_Result"),
    ("Portfolio State", "PMA_Portfolio_State"),
)


@dataclass(frozen=True)
class StageSummary:
    label: str
    table_name: str
    available: bool
    flow_linked: bool
    count: int | None
    status: str | None


class CatsUiReadModel:
    """SELECT-only projection used by the Streamlit capstone UI."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._inspector = inspect(engine)
        self._tables = set(self._inspector.get_table_names())
        self._columns_cache: dict[str, tuple[str, ...]] = {}

    def table_exists(self, table_name: str) -> bool:
        return table_name in self._tables

    def columns(self, table_name: str) -> tuple[str, ...]:
        if table_name not in self._columns_cache:
            if not self.table_exists(table_name):
                self._columns_cache[table_name] = ()
            else:
                self._columns_cache[table_name] = tuple(
                    col["name"] for col in self._inspector.get_columns(table_name)
                )
        return self._columns_cache[table_name]

    def _q(self, identifier: str) -> str:
        return self.engine.dialect.identifier_preparer.quote(identifier)

    @staticmethod
    def _plain(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _rowdicts(self, result: Iterable[Any]) -> list[dict[str, Any]]:
        return [
            {key: self._plain(value) for key, value in row.items()}
            for row in result
        ]

    def database_identity(self) -> dict[str, Any]:
        url = self.engine.url
        return {
            "dialect": url.get_backend_name(),
            "database": url.database,
            "host": url.host,
            "port": url.port,
        }

    def latest_flows(self, limit: int = 20) -> list[dict[str, Any]]:
        table = "TRACE_Flow"
        if not self.table_exists(table):
            return []
        cols = self.columns(table)
        order_col = next(
            (c for c in ("completed_at", "updated_at", "started_at", "created_at") if c in cols),
            None,
        )
        order_sql = f" ORDER BY {self._q(order_col)} DESC NULLS LAST" if order_col else ""
        sql = text(f"SELECT * FROM {self._q(table)}{order_sql} LIMIT :limit")
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()
        return self._rowdicts(rows)

    def rows_for_flow(self, table_name: str, flow_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.table_exists(table_name):
            return []
        cols = self.columns(table_name)
        if "flow_id" not in cols:
            return []
        order_col = next(
            (
                c
                for c in (
                    "completed_at",
                    "filled_at",
                    "observed_at",
                    "evaluated_at",
                    "created_at",
                    "started_at",
                )
                if c in cols
            ),
            None,
        )
        order_sql = f" ORDER BY {self._q(order_col)} DESC NULLS LAST" if order_col else ""
        sql = text(
            f"SELECT * FROM {self._q(table_name)} "
            f"WHERE {self._q('flow_id')} = :flow_id"
            f"{order_sql} LIMIT :limit"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"flow_id": str(flow_id), "limit": int(limit)}).mappings().all()
        return self._rowdicts(rows)

    def _rows_where_in(
        self,
        table_name: str,
        column_name: str,
        values: Iterable[Any],
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Read rows through a known foreign-key lineage without writing anything."""
        values = [str(value) for value in values if value is not None]
        if not values or not self.table_exists(table_name):
            return []
        cols = self.columns(table_name)
        if column_name not in cols:
            return []

        order_col = next(
            (
                c
                for c in (
                    "completed_at",
                    "filled_at",
                    "reconciled_at",
                    "effective_at",
                    "created_at",
                    "started_at",
                )
                if c in cols
            ),
            None,
        )
        order_sql = f" ORDER BY {self._q(order_col)} DESC" if order_col else ""
        placeholders = ", ".join(f":value_{index}" for index in range(len(values)))
        params = {f"value_{index}": value for index, value in enumerate(values)}
        params["limit"] = int(limit)
        sql = text(
            f"SELECT * FROM {self._q(table_name)} "
            f"WHERE CAST({self._q(column_name)} AS TEXT) IN ({placeholders})"
            f"{order_sql} LIMIT :limit"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
        return self._rowdicts(rows)

    def _flow_ids(self, table_name: str, flow_id: str, id_column: str) -> list[str]:
        return [
            str(row[id_column])
            for row in self.rows_for_flow(table_name, flow_id, limit=200)
            if row.get(id_column) is not None
        ]

    def rows_related_to_flow(
        self,
        table_name: str,
        flow_id: str,
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Reconstruct a material flow through durable relational lineage.

        Several CATS tables intentionally do not duplicate ``flow_id``. The read-only UI
        follows the same foreign-key relationships used by the flow audit repository so a
        human can still see the complete persisted material chain.
        """
        if not self.table_exists(table_name):
            return []
        if "flow_id" in self.columns(table_name):
            return self.rows_for_flow(table_name, flow_id, limit=limit)

        execution_ids = self._flow_ids("TEA_Execution", flow_id, "execution_id")
        decision_ids = self._flow_ids(
            "PMA_Portfolio_Decision", flow_id, "portfolio_decision_id"
        )

        if table_name == "TES_Order":
            return self._rows_where_in(table_name, "execution_id", execution_ids, limit=limit)
        if table_name == "TES_Fill":
            return self._rows_where_in(table_name, "execution_id", execution_ids, limit=limit)
        if table_name == "TEA_Reconciliation":
            return self._rows_where_in(table_name, "execution_id", execution_ids, limit=limit)
        if table_name == "TEA_Execution_Result":
            return self._rows_where_in(table_name, "execution_id", execution_ids, limit=limit)
        if table_name == "PMA_Portfolio_State":
            return self._rows_where_in(
                table_name,
                "source_portfolio_decision_id",
                decision_ids,
                limit=limit,
            )
        if table_name == "TAA_Evidence_Item":
            assessment_ids = self._flow_ids("TAA_Assessment", flow_id, "assessment_id")
            links = self._rows_where_in(
                "TAA_Assessment_Evidence", "assessment_id", assessment_ids, limit=limit
            )
            evidence_ids = [
                row.get("evidence_item_id")
                for row in links
                if row.get("evidence_item_id") is not None
            ]
            return self._rows_where_in(
                table_name, "evidence_item_id", evidence_ids, limit=limit
            )
        return []

    def supports_flow_linkage(self, table_name: str) -> bool:
        if not self.table_exists(table_name):
            return False
        if "flow_id" in self.columns(table_name):
            return True
        return table_name in {
            "TAA_Evidence_Item",
            "TES_Order",
            "TES_Fill",
            "TEA_Reconciliation",
            "TEA_Execution_Result",
            "PMA_Portfolio_State",
        }

    def _status_from_row(self, row: dict[str, Any] | None) -> str | None:
        if not row:
            return None
        if "resolved" in row and row.get("resolved") is not None:
            return "RESOLVED" if bool(row.get("resolved")) else "UNRESOLVED"
        for key in (
            "status",
            "validation_status",
            "result",
            "result_status",
            "certainty_status",
            "certainty",
            "feasibility_status",
            "state_type_status",
            "state",
        ):
            value = row.get(key)
            if value is not None:
                return str(value)
        return None

    def stage_summaries(self, flow_id: str) -> list[StageSummary]:
        summaries: list[StageSummary] = []
        for label, table in STAGE_TABLES:
            available = self.table_exists(table)
            flow_linked = available and self.supports_flow_linkage(table)
            if flow_linked:
                rows = self.rows_related_to_flow(table, flow_id, limit=200)
                summaries.append(
                    StageSummary(
                        label=label,
                        table_name=table,
                        available=True,
                        flow_linked=True,
                        count=len(rows),
                        status=self._status_from_row(rows[0] if rows else None),
                    )
                )
            else:
                summaries.append(
                    StageSummary(
                        label=label,
                        table_name=table,
                        available=available,
                        flow_linked=False,
                        count=None,
                        status=None,
                    )
                )
        return summaries

    def first_row_for_flow(self, table_name: str, flow_id: str) -> dict[str, Any] | None:
        rows = self.rows_for_flow(table_name, flow_id, limit=1)
        return rows[0] if rows else None

    @staticmethod
    def _first_value(row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = row.get(key)
            if value is not None and value != "":
                return value
        return None

    @staticmethod
    def _looks_like_horizon(value: Any) -> bool:
        if value is None:
            return False
        normalized = str(value).strip().upper().replace("-", "_").replace(" ", "_")
        return normalized in {
            "TACTICAL",
            "STRATEGIC",
            "SHORT_TERM",
            "MEDIUM_TERM",
            "LONG_TERM",
            "INTRADAY",
        }

    def taa_reasoning(self, flow_id: str) -> dict[str, Any] | None:
        """Normalize persisted TAA assessment shapes for human display.

        Some historical V2ET PAPER flows predate the current Assessment contract and
        persisted the horizon-like value (for example TACTICAL) in assessment_type.
        The UI normalizes that historical representation without modifying CATS state.
        """
        row = self.first_row_for_flow("TAA_Assessment", flow_id)
        if not row:
            return None

        raw_type = self._first_value(
            row,
            "assessment_type",
            "assessment_kind",
            "assessment_class",
        )
        horizon = self._first_value(
            row,
            "horizon",
            "assessment_horizon",
            "relevance_horizon",
            "decision_horizon",
            "temporal_relevance",
        )
        assessment_type = raw_type
        normalized_historical_shape = False

        # Earlier V2ET persistence used assessment_type for TACTICAL/STRATEGIC.
        # Some historical rows also contain the same value in a horizon column.
        # Whenever assessment_type itself is horizon-like, present it as the horizon
        # and expose the architectural TAA role as CANDIDATE.
        if self._looks_like_horizon(raw_type):
            if horizon is None:
                horizon = raw_type
            assessment_type = "CANDIDATE"
            normalized_historical_shape = True

        summary = self._first_value(
            row,
            "summary",
            "assessment_summary",
            "reasoning_summary",
            "narrative_summary",
            "analysis_summary",
            "assessment",
            "rationale_summary",
            "rationale",
        )

        return {
            "assessment_id": self._first_value(row, "assessment_id", "contract_id"),
            "status": self._first_value(row, "status", "assessment_status"),
            "assessment_type": assessment_type,
            "horizon": horizon,
            "confidence": row.get("confidence"),
            "summary": summary,
            "created_at": self._first_value(
                row, "created_at", "evaluated_at", "assessment_timestamp"
            ),
            "evidence_item_ids": row.get("evidence_item_ids"),
            "normalized_historical_shape": normalized_historical_shape,
            "raw_assessment_type": raw_type,
        }

    def tss_measurements_for_flow(self, flow_id: str) -> list[dict[str, Any]]:
        """Return TSS measurements by joining the flow-linked measurement set to its values."""
        required_tables = {"TSS_Measurement_Set", "TSS_Measurement"}
        if not required_tables.issubset(self._tables):
            return []
        set_cols = set(self.columns("TSS_Measurement_Set"))
        measurement_cols = set(self.columns("TSS_Measurement"))
        if not {"tss_measurement_set_id", "flow_id"}.issubset(set_cols):
            return []
        if not {"tss_measurement_set_id", "measurement_type"}.issubset(measurement_cols):
            return []

        fields = [
            "s.tss_measurement_set_id AS tss_measurement_set_id",
            "s.financial_instrument_id AS financial_instrument_id" if "financial_instrument_id" in set_cols else "NULL AS financial_instrument_id",
            "s.observed_at AS observed_at" if "observed_at" in set_cols else "NULL AS observed_at",
            "m.measurement_type AS measurement_type",
            "m.value_numeric AS value_numeric" if "value_numeric" in measurement_cols else "NULL AS value_numeric",
            "m.value_text AS value_text" if "value_text" in measurement_cols else "NULL AS value_text",
            "m.unit AS unit" if "unit" in measurement_cols else "NULL AS unit",
        ]
        sql = text(
            "SELECT " + ", ".join(fields) + " "
            f"FROM {self._q('TSS_Measurement_Set')} s "
            f"JOIN {self._q('TSS_Measurement')} m "
            f"ON m.{self._q('tss_measurement_set_id')} = s.{self._q('tss_measurement_set_id')} "
            f"WHERE s.{self._q('flow_id')} = :flow_id"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"flow_id": str(flow_id)}).mappings().all()
        return self._rowdicts(rows)

    @staticmethod
    def _price_priority(measurement_type: Any) -> int | None:
        if measurement_type is None:
            return None
        normalized = str(measurement_type).strip().upper().replace("-", "_").replace(" ", "_")
        priorities = {
            "CURRENT_PRICE": 0,
            "LAST_PRICE": 1,
            "LATEST_PRICE": 2,
            "MARKET_PRICE": 3,
            "CLOSE_PRICE": 4,
            "CLOSE": 5,
            "PRICE": 6,
        }
        if normalized in priorities:
            return priorities[normalized]
        if normalized.endswith("_PRICE") and not any(x in normalized for x in ("SPREAD", "LIMIT", "STOP", "ENTRY")):
            return 20
        return None

    def reference_prices_for_flow(self, flow_id: str) -> dict[str, dict[str, Any]]:
        """Select the best persisted historical price per instrument for UI valuation.

        TSS is preferred because it represents the market measurement used by the flow.
        Older persisted flows may not have a directly linked TSS measurement set; in that
        case the UI may use the broker-confirmed fill price from the same execution lineage.
        The fallback is display-only and is always labeled as a broker fill price.
        """
        selected: dict[str, dict[str, Any]] = {}
        selected_priority: dict[str, int] = {}
        for row in self.tss_measurements_for_flow(flow_id):
            instrument_id = row.get("financial_instrument_id")
            priority = self._price_priority(row.get("measurement_type"))
            value = row.get("value_numeric")
            if instrument_id is None or priority is None or value is None:
                continue
            key = str(instrument_id)
            if key not in selected_priority or priority < selected_priority[key]:
                selected_priority[key] = priority
                selected[key] = {
                    "price": float(value),
                    "measurement_type": row.get("measurement_type"),
                    "unit": row.get("unit"),
                    "observed_at": row.get("observed_at"),
                    "source": "TSS",
                }

        # Historical V2ET runs may predate persisted TSS measurement linkage. Use a
        # broker-confirmed fill price from the same execution only when TSS is absent.
        required = {"TEA_Execution", "TES_Fill"}
        if required.issubset(self._tables):
            execution_cols = set(self.columns("TEA_Execution"))
            fill_cols = set(self.columns("TES_Fill"))
            if {
                "execution_id",
                "financial_instrument_id",
                "flow_id",
            }.issubset(execution_cols) and {"execution_id", "price"}.issubset(fill_cols):
                filled_at_expr = (
                    f"f.{self._q('filled_at')}" if "filled_at" in fill_cols else "NULL"
                )
                order_sql = (
                    f" ORDER BY f.{self._q('filled_at')} DESC"
                    if "filled_at" in fill_cols
                    else ""
                )
                sql = text(
                    f"""
                    SELECT
                        e.{self._q('financial_instrument_id')} AS financial_instrument_id,
                        f.{self._q('price')} AS price,
                        {filled_at_expr} AS filled_at
                    FROM {self._q('TEA_Execution')} e
                    JOIN {self._q('TES_Fill')} f
                      ON f.{self._q('execution_id')} = e.{self._q('execution_id')}
                    WHERE e.{self._q('flow_id')} = :flow_id
                    {order_sql}
                    """
                )
                with self.engine.connect() as conn:
                    fill_rows = self._rowdicts(
                        conn.execute(sql, {"flow_id": str(flow_id)}).mappings().all()
                    )
                for row in fill_rows:
                    instrument_id = row.get("financial_instrument_id")
                    price = row.get("price")
                    if instrument_id is None or price is None:
                        continue
                    key = str(instrument_id)
                    if key in selected:
                        continue
                    selected[key] = {
                        "price": float(price),
                        "measurement_type": "BROKER_FILL",
                        "unit": "USD",
                        "observed_at": row.get("filled_at"),
                        "source": "TES_Fill",
                    }
        return selected

    def accepted_position_for_flow(
        self,
        flow_id: str,
        financial_instrument_id: Any,
    ) -> dict[str, Any] | None:
        """Return the accepted post-execution position reached by the selected flow."""
        states = self.rows_related_to_flow("PMA_Portfolio_State", flow_id, limit=50)
        accepted = [
            row
            for row in states
            if str(row.get("status") or "").upper() == "ACCEPTED"
        ]
        if not accepted:
            return None
        state = accepted[0]
        state_id = state.get("portfolio_state_id")
        if state_id is None:
            return None
        positions = self._rows_where_in(
            "PMA_Position", "portfolio_state_id", [state_id], limit=200
        )
        for position in positions:
            if str(position.get("financial_instrument_id")) == str(financial_instrument_id):
                return position
        return None

    def selected_decision_transition(self, flow_id: str) -> list[dict[str, Any]]:
        """Return actual-vs-target transition plus a human-readable USD equivalent.

        USD amounts are a display projection only. They use the best persisted TSS price from
        the selected flow and never call a live market-data service.
        """
        required_tables = {
            "PMA_Portfolio_Decision",
            "PMA_Position",
            "PMA_Decision_Target",
            "FIN_Financial_Instrument",
        }
        if not required_tables.issubset(self._tables):
            return []

        decision_cols = set(self.columns("PMA_Portfolio_Decision"))
        position_cols = set(self.columns("PMA_Position"))
        target_cols = set(self.columns("PMA_Decision_Target"))
        instrument_cols = set(self.columns("FIN_Financial_Instrument"))
        required = (
            {"portfolio_decision_id", "source_portfolio_state_id", "flow_id"}.issubset(decision_cols)
            and {"portfolio_state_id", "financial_instrument_id", "quantity"}.issubset(position_cols)
            and {"portfolio_decision_id", "financial_instrument_id", "target_quantity"}.issubset(target_cols)
            and {"financial_instrument_id"}.issubset(instrument_cols)
        )
        if not required:
            return []

        symbol_expr = (
            f"i.{self._q('symbol')}"
            if "symbol" in instrument_cols
            else f"CAST(i.{self._q('financial_instrument_id')} AS TEXT)"
        )
        target_weight_expr = f"t.{self._q('target_weight')}" if "target_weight" in target_cols else "NULL"
        decision_type_expr = f"d.{self._q('decision_type')}" if "decision_type" in decision_cols else "NULL"

        sql = text(
            f"""
            SELECT
                t.{self._q('financial_instrument_id')} AS financial_instrument_id,
                {symbol_expr} AS symbol,
                {decision_type_expr} AS decision_type,
                COALESCE(p.{self._q('quantity')}, 0) AS current_quantity,
                t.{self._q('target_quantity')} AS target_quantity,
                t.{self._q('target_quantity')} - COALESCE(p.{self._q('quantity')}, 0) AS delta_quantity,
                {target_weight_expr} AS target_weight
            FROM {self._q('PMA_Portfolio_Decision')} d
            JOIN {self._q('PMA_Decision_Target')} t
              ON t.{self._q('portfolio_decision_id')} = d.{self._q('portfolio_decision_id')}
            JOIN {self._q('FIN_Financial_Instrument')} i
              ON i.{self._q('financial_instrument_id')} = t.{self._q('financial_instrument_id')}
            LEFT JOIN {self._q('PMA_Position')} p
              ON p.{self._q('portfolio_state_id')} = d.{self._q('source_portfolio_state_id')}
             AND p.{self._q('financial_instrument_id')} = t.{self._q('financial_instrument_id')}
            WHERE d.{self._q('flow_id')} = :flow_id
            ORDER BY symbol
            """
        )
        with self.engine.connect() as conn:
            rows = self._rowdicts(conn.execute(sql, {"flow_id": str(flow_id)}).mappings().all())

        prices = self.reference_prices_for_flow(flow_id)
        for row in rows:
            price_info = prices.get(str(row.get("financial_instrument_id")))
            if not price_info:
                row.update(
                    {
                        "reference_price": None,
                        "reference_price_type": None,
                        "reference_price_observed_at": None,
                        "current_value_usd": None,
                        "target_value_usd": None,
                        "delta_value_usd": None,
                    }
                )
                continue
            price = float(price_info["price"])
            row.update(
                {
                    "reference_price": price,
                    "reference_price_type": price_info.get("measurement_type"),
                    "reference_price_observed_at": price_info.get("observed_at"),
                    "current_value_usd": float(row["current_quantity"]) * price,
                    "target_value_usd": float(row["target_quantity"]) * price,
                    "delta_value_usd": float(row["delta_quantity"]) * price,
                }
            )
        return rows

    def execution_snapshot(self, flow_id: str) -> dict[str, Any]:
        """Compact persisted execution view for a human reader."""
        pma = self.first_row_for_flow("PMA_Portfolio_Decision", flow_id) or {}
        sys = self.first_row_for_flow("SYS_Validation_Result", flow_id) or {}
        tea = self.first_row_for_flow("TEA_Execution", flow_id) or {}
        order_rows = self.rows_related_to_flow("TES_Order", flow_id, limit=20)
        fill_rows = self.rows_related_to_flow("TES_Fill", flow_id, limit=20)
        recon_rows = self.rows_related_to_flow("TEA_Reconciliation", flow_id, limit=20)
        result_rows = self.rows_related_to_flow("TEA_Execution_Result", flow_id, limit=20)
        order = order_rows[0] if order_rows else {}
        fill = fill_rows[0] if fill_rows else {}
        recon = recon_rows[0] if recon_rows else {}
        result = result_rows[0] if result_rows else {}

        order_qty = order.get("quantity")
        fill_qty = fill.get("quantity")
        fill_price = fill.get("price") or recon.get("average_fill_price")
        trade_value = None
        if fill_qty is not None and fill_price is not None:
            trade_value = float(fill_qty) * float(fill_price)
        elif order_qty is not None and fill_price is not None:
            trade_value = float(order_qty) * float(fill_price)

        reconciliation_status = recon.get("result") or recon.get("status")
        if reconciliation_status is None and recon.get("resolved") is not None:
            reconciliation_status = "RESOLVED" if bool(recon.get("resolved")) else "UNRESOLVED"

        instrument_id = tea.get("financial_instrument_id") or order.get("financial_instrument_id")
        final_position = (
            self.accepted_position_for_flow(flow_id, instrument_id)
            if instrument_id is not None
            else None
        )
        final_quantity = None if final_position is None else final_position.get("quantity")
        final_value = None if final_position is None else final_position.get("market_value")
        if final_value is None and final_quantity is not None and fill_price is not None:
            final_value = float(final_quantity) * float(fill_price)

        return {
            "decision_type": pma.get("decision_type"),
            "decision_status": pma.get("status"),
            "validation": sys.get("result") or sys.get("validation_status") or sys.get("status"),
            "execution_status": tea.get("status") or tea.get("state_type_status"),
            "execution_side": tea.get("side") or order.get("side"),
            "execution_quantity": tea.get("target_quantity") or tea.get("quantity") or order_qty,
            "order_status": order.get("status"),
            "order_side": order.get("side"),
            "order_quantity": order_qty,
            "fill_quantity": fill_qty,
            "fill_price": fill_price,
            "trade_value_usd": trade_value,
            "reconciliation": reconciliation_status,
            "reconciliation_certainty": recon.get("certainty_status") or recon.get("certainty_after"),
            "execution_result_status": result.get("result_status") or result.get("status"),
            "certainty": result.get("certainty_status") or tea.get("certainty_status") or recon.get("certainty_status") or recon.get("certainty_after"),
            "final_position_quantity": final_quantity,
            "final_position_value_usd": final_value,
        }
