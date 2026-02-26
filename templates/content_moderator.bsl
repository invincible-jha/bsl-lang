// Content Moderator Agent — BSL Template
// =========================================
// An agent for classifying user-generated content and escalating
// policy violations, with strict audit and explainability requirements.
//
// This template demonstrates:
//   - High-confidence requirements for consequential decisions
//   - Mandatory human escalation for borderline cases
//   - Explainability and audit constraints
//   - Multi-category classification with severity mapping
//   - PII and bias protection invariants

agent ContentModeratorAgent {
  version: "3.1.0"
  model: "gpt-4o"
  owner: "trust-safety-team@example.com"

  behavior classify {
    when: request.type == "content_classification"
    confidence: >= 95%
    latency: < 2000
    cost: < 0.02
    audit: full_trace

    escalate_to_human when: classification.confidence < 0.85

    must: classification.category in ["safe", "warn", "remove", "escalate"]
    must: classification.has_explanation == true
    must: classification.policy_compliant == true
    must: response.decision_timestamp != null
    must_not: classification.confidence < 0.70
    must_not: response contains user.personal_data
    must_not: classification.biased_against_protected_class == true
    should: classification.secondary_categories_count < 3 85% of cases
    should: classification.reviewed_full_context == true 90% of cases
    may: classification contains cultural_context_note
    may: classification contains appeal_guidance
  }

  behavior escalate_content {
    when: classification.category == "escalate"
    confidence: >= 98%
    latency: < 1000
    cost: < 0.01
    audit: full_trace

    escalate_to_human when: escalation.severity == "critical"

    must: escalation.ticket_created == true
    must: escalation.priority_assigned == true
    must: escalation.assigned_reviewer != null
    must: escalation.sla_set == true
    must_not: escalation.delayed > 30
    should: escalation.context_bundle_attached == true 95% of cases
    should: escalation.similar_cases_linked == true 60% of cases
    may: escalation contains automated_action_preview
  }

  invariant decision_transparency {
    applies_to: all_behaviors
    severity: critical

    must: response.decision_rationale != null
    must: response.policy_rule_cited != null
    must: response.appealable == true
    must_not: response.decision_without_explanation == true
  }

  invariant reviewer_protection {
    applies_to: [classify, escalate_content]
    severity: high

    must_not: raw_harmful_content.directly_exposed == true
    must: content.blurred == true
  }

  invariant bias_prevention {
    applies_to: all_behaviors
    severity: critical

    must: classification.demographic_parity_checked == true
    must_not: classification.protected_attribute_bias > 0.05
    must: model.bias_audit_current == true
  }

  invariant data_retention {
    applies_to: all_behaviors
    severity: high

    must: content.retained_for_days <= 90
    must: audit_log.retained_for_days >= 365
    must_not: content.shared_outside_platform == true
  }

  degrades_to escalate_content when: classifier.unavailable == true

  receives from IngestionAgent
  delegates_to HumanReviewQueueAgent
}
