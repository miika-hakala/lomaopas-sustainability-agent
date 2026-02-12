from typing import Dict, Any, Optional
from lomaopas_sus.models import ExtractedFacts, SustainabilityScore, ScoreBreakdown

def compute_facts_diff(
    current_facts: Optional[ExtractedFacts],
    new_facts: ExtractedFacts,
    current_score: Optional[SustainabilityScore],
    new_score: SustainabilityScore
) -> Dict[str, Any]:
    """
    Computes a diff between current and new ExtractedFacts and their scores.
    Returns a dictionary with summary, changes, and metrics.
    """
    diff = {
        "summary": "No changes detected." if not current_facts else "",
        "changes": [],
        "metrics": {
            "claims_added": 0,
            "claims_removed": 0,
            "label_delta": 0,
            "score_delta": 0.0,
            "certifications_added": 0,
            "certifications_removed": 0,
            "evidence_changes": 0
        }
    }

    if not current_facts:
        diff["summary"] = "First snapshot for this entity."
        # Count all claims in new_facts as added
        new_facts_dict = new_facts.model_dump(exclude_unset=True)
        for category, data in new_facts_dict.items():
            if isinstance(data, dict):
                for fact_name, value in data.items():
                    if value not in [None, False, [], ""]: # Consider a claim made
                        diff["metrics"]["claims_added"] += 1
                        diff["changes"].append({
                            "field": f"{category}.{fact_name}",
                            "type": "added",
                            "before": None,
                            "after": value
                        })
            elif isinstance(data, list) and category != "evidence_snippets":
                for item in data:
                    if item not in [None, False, "", []]:
                        diff["metrics"]["claims_added"] += 1
                        diff["changes"].append({
                            "field": f"{category}",
                            "type": "added_item",
                            "before": None,
                            "after": item
                        })
        # Removed: if new_score.label:
        # Removed:     diff["metrics"]["label_delta"] = 1 # Assuming "first" means a positive change in label existence

        if new_facts.certifications.eco_certifications:
            diff["metrics"]["certifications_added"] += len(new_facts.certifications.eco_certifications)
        if new_facts.certifications.other_sustainability_badges:
            diff["metrics"]["certifications_added"] += len(new_facts.certifications.other_sustainability_badges)


        return diff

    current_facts_dict = current_facts.model_dump(exclude_unset=True)
    new_facts_dict = new_facts.model_dump(exclude_unset=True)

    # Compare scores
    # label_delta logic will now be based on total_score_final delta,
    # as label is a derived concept, not directly in SustainabilityScore model.
    if current_score and new_score:
        diff["metrics"]["score_delta"] = new_score.total_score_final - current_score.total_score_final
        # A simple heuristic for label_delta: significant score change implies label change
        if abs(diff["metrics"]["score_delta"]) > 5.0: # Example threshold for "significant"
            diff["metrics"]["label_delta"] = diff["metrics"]["score_delta"] / abs(diff["metrics"]["score_delta"]) # +1 or -1
        else:
            diff["metrics"]["label_delta"] = 0


    all_categories = set(current_facts_dict.keys()).union(new_facts_dict.keys())

    for category in all_categories:
        current_data = current_facts_dict.get(category, {})
        new_data = new_facts_dict.get(category, {})

        if category == "evidence_snippets":
            current_evidence_urls = {f"{e.url}-{e.snippet}" for e in current_facts.evidence_snippets}
            new_evidence_urls = {f"{e.url}-{e.snippet}" for e in new_facts.evidence_snippets}
            if current_evidence_urls != new_evidence_urls:
                diff["metrics"]["evidence_changes"] = 1 # Simple flag for now
            continue

        if isinstance(current_data, dict) and isinstance(new_data, dict):
            all_facts_in_category = set(current_data.keys()).union(new_data.keys())
            for fact_name in all_facts_in_category:
                current_value = current_data.get(fact_name)
                new_value = new_data.get(fact_name)

                if current_value != new_value:
                    if current_value is None or current_value == [] or current_value == False or current_value == "":
                        diff["metrics"]["claims_added"] += 1
                        change_type = "added"
                    elif new_value is None or new_value == [] or new_value == False or new_value == "":
                        diff["metrics"]["claims_removed"] += 1
                        change_type = "removed"
                    else:
                        change_type = "changed"

                    diff["changes"].append({
                        "field": f"{category}.{fact_name}",
                        "type": change_type,
                        "before": current_value,
                        "after": new_value
                    })
                    if category == "certifications":
                        if change_type == "added":
                            diff["metrics"]["certifications_added"] += 1
                        elif change_type == "removed":
                            diff["metrics"]["certifications_removed"] += 1
        elif isinstance(current_data, list) and isinstance(new_data, list):
            # Handle list changes for non-evidence categories
            if current_data != new_data:
                added_items = [item for item in new_data if item not in current_data]
                removed_items = [item for item in current_data if item not in new_data]
                
                for item in added_items:
                    diff["metrics"]["claims_added"] += 1
                    diff["changes"].append({
                        "field": category,
                        "type": "added_item",
                        "before": None,
                        "after": item
                    })
                    if category == "certifications" and item:
                        diff["metrics"]["certifications_added"] += 1
                for item in removed_items:
                    diff["metrics"]["claims_removed"] += 1
                    diff["changes"].append({
                        "field": category,
                        "type": "removed_item",
                        "before": item,
                        "after": None
                    })
                    if category == "certifications" and item:
                        diff["metrics"]["certifications_removed"] += 1
        else:
            # Type change or one is dict, other is list/primitive (unlikely with ExtractedFacts structure)
            if current_data != new_data:
                diff["metrics"]["claims_added"] += 1 # Assume new type is an addition for simplicity
                diff["metrics"]["claims_removed"] += 1 # And old type is a removal
                diff["changes"].append({
                    "field": category,
                    "type": "type_changed",
                    "before": current_data,
                    "after": new_data
                })

    if not diff["changes"] and current_facts: # Only if current_facts exists, otherwise it's always a first snapshot.
        diff["summary"] = "No significant changes detected."
    elif diff["changes"]:
        diff["summary"] = f"{len(diff['changes'])} changes detected."

    return diff


def should_auto_accept_diff(
    diff: Dict[str, Any],
    is_first_snapshot: bool,
    auto_accept_threshold_claims: int = 1,
    auto_accept_threshold_label_delta: float = 0.1 # e.g., 0.1 for 10% change in label score
) -> bool:
    """
    Determines if a diff should be auto-accepted based on predefined heuristics.
    """
    if is_first_snapshot:
        return True

    metrics = diff["metrics"]

    # Heuristic 1: Label delta
    # Assuming label_delta represents change in score that would affect label, or direct label comparison
    if abs(metrics["label_delta"]) > auto_accept_threshold_label_delta:
        return False

    # Heuristic 2: Number of added/removed claims
    if (metrics["claims_added"] + metrics["claims_removed"]) > auto_accept_threshold_claims:
        return False

    # Heuristic 3: No certification removed
    if metrics["certifications_removed"] > 0:
        return False
    
    # Heuristic 4: No significant evidence changes
    if metrics["evidence_changes"] > 0: # If evidence changed, might warrant review
        return False

    return True

