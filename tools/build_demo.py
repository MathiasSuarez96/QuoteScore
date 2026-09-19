"""Datos totalmente inventados; no se basan en cartera ni en el contexto privado."""
from pathlib import Path

from src.data.schema import INPUT_TABLES, fields
from src.data.store import write_csv


def demo_tables():
    tables = {t: [] for t in INPUT_TABLES}

    def add(table, **values):
        row = {name: None for name in fields(table)}
        row.update({k: str(v) if v is not None else None for k, v in values.items()})
        tables[table].append(row)
        return row

    add("sources", source_id="SRC_DEMO", source_type="artificial", sanitized_reference="fictional-fixture-001", document_date="2025-02-03", imported_at="2025-02-10T12:00:00+00:00", evidence_level="artificial")
    for i in range(1, 5):
        add("opportunities", opportunity_id=f"OP_DEMO_{i}", created_at="2025-02-01", status="open", exclude_from_training=0, review_status="verified", requested_scope_initial="package" if i == 1 else "hotel_only")
    for i in range(1, 4):
        q = add("quotes", quote_id=f"Q_DEMO_{i}", opportunity_id=f"OP_DEMO_{i}", sent_at="2025-02-03", date_precision="day", version_number=1, first_priced_quote_status="confirmed", channel_at_quote="whatsapp", lead_source_at_quote="referral", request_type_at_quote="quote_request", repeat_customer_at_quote=0, source_id="SRC_DEMO")
        o = add("quote_options", option_id=f"OPT_DEMO_{i}", quote_id=q["quote_id"], option_order=1, product_scope="package" if i == 1 else "hotel_only", destination_summary=f"Destino ficticio {i}", destination_count=1, departure_date="2025-05-12", return_date="2025-05-16", nights=4, passengers=2, adults=2, children=0, currency="USD", price_scope="group", gross_price=800, discount_amount=40, net_price=760, points_available=0, points_proposed=0, points_value_quoted=0, source_id="SRC_DEMO")
        if i == 2:
            o.update(passengers="3", price_scope="unknown", net_price=None)
        for table, row, key in (("quotes", q, "quote_id"), ("quote_options", o, "option_id")):
            for name, value in row.items():
                if value is not None:
                    add("field_evidence", evidence_id=f"E_{row[key]}_{name}", entity_type=table, entity_id=row[key], field_name=name, source_id="SRC_DEMO", locator=f"fictional:{row[key]}:{name}", known_at="2025-02-03", time_precision="day", review_status="verified")
    add("quote_components", component_id="COMP_DEMO_1", option_id="OPT_DEMO_1", component_order=1, component_type="hotel", destination="Destino ficticio 1", start_date="2025-05-12", end_date="2025-05-16", nights=4, provider="Hotel inventado", meal_plan="breakfast", passengers_covered=2, source_id="SRC_DEMO")
    add("transactions", transaction_id="TX_DEMO_1", opportunity_id="OP_DEMO_1", transaction_date="2025-02-06", transaction_type="sale", product_type="flight_only", amount=500, currency="USD", source_id="SRC_DEMO")
    return tables


def build(directory=Path("examples/artificial/input")):
    for table, rows in demo_tables().items():
        write_csv(directory / (table + ".csv"), fields(table), rows)


if __name__ == "__main__":
    build()
