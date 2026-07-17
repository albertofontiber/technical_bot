"""Apply the frozen S174 labels to the sealed, source-receipted audit packet."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/s174_prerequisite_blind_audit_packet_v1.json"
OUT = ROOT / "evals/s174_prerequisite_blind_adjudication_v1.json"
SOURCE_FILE_SHA = "1282e22a82dd92f6c3644692e9df3bdde1cf0f82ae90e7e751104fc712785c42"
SOURCE_PACKET_SHA = "e34f048a04ada50139e8f1e4c070cbe4591f05e8af7a571a78882e9eec4a4c6e"


# Labels were assigned only after the packet selection and ordering had been sealed.
# Reasons intentionally name the frozen decision boundary instead of scoring relevance.
LABELS = {
    "s174_audit_01": (False, "anchors_belong_to_unrelated_sentences"),
    "s174_audit_02": (False, "password_security_recommendation_not_authorization_precondition"),
    "s174_audit_03": (False, "example_application_not_distributive_requirement"),
    "s174_audit_04": (False, "anchors_belong_to_unrelated_sentences"),
    "s174_audit_05": (False, "administrative_RMA_or_commercial_authorization"),
    "s174_audit_06": (False, "licence_enables_mode_but_per_loop_anchor_governs_capacity"),
    "s174_audit_07": (False, "feature_enablement_in_one_licence_not_distributive_scope"),
    "s174_audit_08": (True, "authorized_level_two_required_to_continue_emergency_operation"),
    "s174_audit_09": (False, "anchors_belong_to_unrelated_sentences"),
    "s174_audit_10": (False, "restricted_level_mentioned_without_access_precondition"),
    "s174_audit_11": (False, "configuration_and_licence_file_heading_not_entitlement"),
    "s174_audit_12": (True, "level_two_required_before_function_keys_can_be_selected"),
    "s174_audit_13": (False, "licensed_by_feature_not_allowed_distributive_unit"),
    "s174_audit_14": (True, "installer_password_required_before_user_password_change"),
    "s174_audit_15": (True, "level_two_password_is_a_step_in_interface_disablement"),
    "s174_audit_16": (False, "anchors_belong_to_unrelated_sentences"),
    "s174_audit_17": (False, "licensed_by_feature_not_allowed_distributive_unit"),
    "s174_audit_18": (True, "access_code_required_to_reenter_technical_interface"),
    "s174_audit_19": (False, "entitlement_assumption_without_per_unit_scope"),
    "s174_audit_20": (True, "one_clip_licence_per_loop_and_one_tpp_licence_per_channel"),
    "s174_audit_21": (False, "must_know_imported_passwords_not_access_precondition"),
    "s174_audit_22": (False, "internal_panel_key_not_user_authorization"),
    "s174_audit_23": (False, "licence_heading_not_entitlement_statement"),
    "s174_audit_24": (False, "receiver_module_licence_not_distributive_scope"),
    "s174_audit_25": (True, "operator_password_required_before_enabling_configured_delay"),
    "s174_audit_26": (False, "licence_file_features_not_per_allowed_unit"),
    "s174_audit_27": (True, "programming_key_required_before_level_three_configuration"),
    "s174_audit_28": (True, "minimum_country_licence_process_repeated_for_each_panel"),
    "s174_audit_29": (False, "anchors_belong_to_unrelated_sections"),
    "s174_audit_30": (False, "user_level_description_without_restricted_governed_action"),
    "s174_audit_31": (False, "access_level_cross_reference_not_bound_to_firmware_procedure"),
    "s174_audit_32": (False, "administrative_RMA_or_commercial_authorization"),
    "s174_audit_33": (True, "authorized_operator_level_and_password_govern_listed_operations"),
    "s174_audit_34": (False, "feature_enablement_in_one_licence_not_distributive_scope"),
    "s174_audit_35": (False, "permission_configuration_and_level_description_without_precondition"),
    "s174_audit_36": (True, "additional_licence_bound_to_each_loop_changed_to_clip"),
    "s174_audit_37": (False, "access_level_display_context_not_action_precondition"),
}

GATE = {
    "access_true_positives_min": 3,
    "access_manufacturers_min": 3,
    "quantified_entitlement_true_positives_min": 2,
    "quantified_entitlement_manufacturers_min": 2,
    "exact_source_receipts": 1.0,
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def main() -> None:
    if file_sha(SOURCE) != SOURCE_FILE_SHA:
        raise ValueError("S174 sealed audit packet file drift")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if source["packet_sha256"] != SOURCE_PACKET_SHA:
        raise ValueError("S174 sealed audit packet semantic drift")
    ids = {row["audit_id"] for row in source["items"]}
    if ids != set(LABELS) or len(ids) != len(source["items"]):
        raise ValueError("S174 adjudication labels do not exactly cover packet")

    adjudications = []
    true_by_facet = defaultdict(list)
    manufacturers_by_facet = defaultdict(set)
    for row in source["items"]:
        is_true_positive, reason = LABELS[row["audit_id"]]
        adjudication = {
            "audit_id": row["audit_id"],
            "candidate_id": row["candidate_id"],
            "facet": row["facet"],
            "manufacturer": row["manufacturer"],
            "exact_source_receipt": row["exact_source_receipt"],
            "is_true_positive": is_true_positive,
            "reason": reason,
            "quote_sha256": row["quote_sha256"],
            "content_sha256": row["content_sha256"],
        }
        adjudications.append(adjudication)
        if is_true_positive:
            true_by_facet[row["facet"]].append(row["audit_id"])
            manufacturers_by_facet[row["facet"]].add(row["manufacturer"])

    access_tp = len(true_by_facet["access_prerequisite"])
    access_manufacturers = len(manufacturers_by_facet["access_prerequisite"])
    entitlement_tp = len(true_by_facet["quantified_entitlement"])
    entitlement_manufacturers = len(
        manufacturers_by_facet["quantified_entitlement"]
    )
    exact_receipt_rate = sum(
        row["exact_source_receipt"] for row in adjudications
    ) / len(adjudications)
    checks = {
        "access_true_positives": access_tp >= GATE["access_true_positives_min"],
        "access_manufacturers": access_manufacturers
        >= GATE["access_manufacturers_min"],
        "quantified_entitlement_true_positives": entitlement_tp
        >= GATE["quantified_entitlement_true_positives_min"],
        "quantified_entitlement_manufacturers": entitlement_manufacturers
        >= GATE["quantified_entitlement_manufacturers_min"],
        "exact_source_receipts": exact_receipt_rate >= GATE["exact_source_receipts"],
    }
    applicability_passed = all(checks.values())
    body = {
        "instrument": "s174_prerequisite_blind_adjudication_v1",
        "status": "NO_GO" if not applicability_passed else "APPLICABILITY_GO",
        "source_packet": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_packet_file_sha256": SOURCE_FILE_SHA,
        "source_packet_semantic_sha256": SOURCE_PACKET_SHA,
        "adjudications": adjudications,
        "summary": {
            "candidates": len(adjudications),
            "exact_source_receipt_rate": exact_receipt_rate,
            "access_true_positives": access_tp,
            "access_true_positive_manufacturers": sorted(
                manufacturers_by_facet["access_prerequisite"]
            ),
            "quantified_entitlement_true_positives": entitlement_tp,
            "quantified_entitlement_true_positive_manufacturers": sorted(
                manufacturers_by_facet["quantified_entitlement"]
            ),
        },
        "gate": {"thresholds": GATE, "checks": checks, "passed": applicability_passed},
        "decision": {
            "frontier_runtime_validation_authorized": applicability_passed,
            "runtime_or_production_release_authorized": False,
            "known_target_recovery_credit": "local_only",
            "reason": (
                "quantified entitlement language did not generalize across the "
                "required manufacturer count"
                if not applicability_passed
                else "applicability only; a separate runtime selector gate is required"
            ),
        },
        "resources": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "production_changes": 0,
        },
    }
    body["adjudication_sha256"] = stable_sha(body)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
