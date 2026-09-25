"""Contrato único para lectores, validadores, plantillas y diccionario."""
from dataclasses import dataclass

VERSION = "1.0.0"
RULES_VERSION = "1.1.0"


@dataclass(frozen=True)
class Field:
    kind: str = "text"
    required: bool = False
    choices: tuple = ()
    temporal: str = "audit"


TABLE_COLUMNS = {
    "sources": "source_id source_type sanitized_reference document_date imported_at evidence_level",
    "opportunities": "opportunity_id created_at status converted outcome_at outcome_source_id outcome_basis initial_destination final_destination requested_scope_initial sold_scope sale_extent final_sale_amount final_sale_currency exclude_from_training exclusion_reason review_status",
    "quotes": "quote_id opportunity_id sent_at date_precision version_number first_priced_quote_status channel_at_quote lead_source_at_quote request_type_at_quote preselected_product_at_quote repeat_customer_at_quote reactivated_lead_at_quote date_flexibility_at_quote credit_available_at_quote financing_available_at_quote source_id",
    "quote_options": "option_id quote_id option_order product_scope origin destination_summary destination_count departure_date return_date nights passengers adults children currency price_scope gross_price discount_amount net_price quoted_price_per_person points_available points_proposed points_value_quoted quoted_cash_balance source_id",
    "quote_components": "component_id option_id component_order component_type origin destination start_date end_date nights provider hotel_category room_type meal_plan passengers_covered flight_direction number_of_connections max_connection_minutes overnight_connection personal_item carry_on checked_bag amount currency price_scope source_id",
    "transactions": "transaction_id opportunity_id transaction_date transaction_type product_type amount currency amount_usd exchange_rate exchange_rate_date related_transaction_id source_id",
    "field_evidence": "evidence_id entity_type entity_id field_name source_id locator known_at time_precision review_status",
    "quality_issues": "issue_id entity_type entity_id field_name issue_code severity resolution_status resolution_note evidence_source_id",
    "reconciliation_log": "decision_id source_record_id opportunity_id decision_type rationale evidence_source_id decided_at case_id supersedes_decision_id before_json after_json",
    "review_queue": "case_id case_type entity_type entity_id proposed_opportunity_id evidence_source_id reason current_json proposed_json status last_decision_id",
    "outcome_history": "outcome_event_id opportunity_id previous_status new_status converted outcome_at recorded_at source_id reason supersedes_event_id details_json",
    "load_runs": "run_id schema_version rules_version input_fingerprint generated_at cutoff input_counts output_counts",
    "opportunity_links": "link_id alias_opportunity_id canonical_opportunity_id decision_id",
    "import_records": "record_version_id entity_type entity_id content_fingerprint run_id recorded_at normalized_json",
}
KEYS = {t: s.split()[0] for t, s in TABLE_COLUMNS.items()}
BOOLS = set("converted exclude_from_training preselected_product_at_quote repeat_customer_at_quote reactivated_lead_at_quote date_flexibility_at_quote credit_available_at_quote financing_available_at_quote overnight_connection personal_item carry_on checked_bag".split())
INTS = set("version_number option_order component_order destination_count nights passengers adults children passengers_covered number_of_connections max_connection_minutes points_available points_proposed".split())
DECIMALS = set("final_sale_amount gross_price discount_amount net_price quoted_price_per_person points_value_quoted quoted_cash_balance amount amount_usd exchange_rate".split())
DATES = set("departure_date return_date start_date end_date exchange_rate_date document_date cutoff".split())
TIMES = set("created_at outcome_at sent_at transaction_date imported_at known_at decided_at recorded_at generated_at".split())
ENUMS = {
    "status": ("open", "won", "lost", "needs_review"),
    "sale_extent": ("full", "partial", "unknown"),
    "review_status": ("pending", "verified", "not_applicable"),
    "first_priced_quote_status": ("confirmed", "candidate", "unknown"),
    "date_precision": ("day", "timestamp", "unknown"),
    "time_precision": ("day", "timestamp", "unknown"),
    "channel_at_quote": ("web", "whatsapp", "branch", "phone", "other"),
    "lead_source_at_quote": ("santander_web", "referral", "other"),
    "request_type_at_quote": ("quote_request", "purchase_error", "other"),
    "price_scope": ("group", "per_person", "component", "unknown"),
    "component_type": ("flight", "hotel", "transfer", "insurance", "excursion", "event_ticket", "other"),
    "transaction_type": ("sale", "add_on", "refund", "cancellation", "adjustment"),
    "evidence_level": ("supplied_summary", "original_verified", "user_confirmation", "artificial"),
    "source_type": ("summary", "pdf", "chat", "sale_record", "user_confirmation", "artificial", "other"),
    "severity": ("error", "warning"),
    "resolution_status": ("pending", "resolved", "accepted"),
    "flight_direction": ("outbound", "inbound", "other"),
}
INPUT_TABLES = ("sources", "opportunities", "quotes", "quote_options", "quote_components", "transactions", "field_evidence")
FOREIGN_KEYS = {
    "opportunities": {"outcome_source_id": "sources"},
    "quotes": {"opportunity_id": "opportunities", "source_id": "sources"},
    "quote_options": {"quote_id": "quotes", "source_id": "sources"},
    "quote_components": {"option_id": "quote_options", "source_id": "sources"},
    "transactions": {"opportunity_id": "opportunities", "related_transaction_id": "transactions", "source_id": "sources"},
    "field_evidence": {"source_id": "sources"},
}
REQUIRED = {
    "sources": {"source_type", "sanitized_reference", "evidence_level"},
    "opportunities": {"status", "exclude_from_training", "review_status"},
    "quotes": {"opportunity_id", "source_id", "first_priced_quote_status", "date_precision"},
    "quote_options": {"quote_id", "source_id", "price_scope"},
    "quote_components": {"option_id", "source_id", "component_type"},
    "transactions": {"opportunity_id", "source_id", "transaction_type"},
    "field_evidence": {"entity_type", "entity_id", "field_name", "source_id", "review_status", "time_precision"},
}


def fields(table):
    result = {}
    for name in TABLE_COLUMNS[table].split():
        kind = "bool" if name in BOOLS else "integer" if name in INTS else "decimal" if name in DECIMALS else "date" if name in DATES else "time" if name in TIMES else "text"
        temporal = "initial_requires_evidence" if table in ("quotes", "quote_options", "quote_components") else "audit"
        if table in ("opportunities", "transactions", "outcome_history"):
            temporal = "descriptive_or_outcome_not_feature"
        choices = ENUMS.get(name, ())
        if table == "review_queue" and name == "status":
            choices = ("pending", "confirmed", "rejected")
        result[name] = Field(kind, name == KEYS[table] or name in REQUIRED.get(table, ()), choices, temporal)
    return result


def empty_tables():
    return {table: [] for table in TABLE_COLUMNS}
