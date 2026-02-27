"""Built-in BSL template definitions.

Each entry is a tuple of (TemplateMetadata, bsl_source_string).
The registry key equals TemplateMetadata.name.

Templates are minimal but functional BSL stubs covering 20 domains.
Users should expand the stubs with project-specific constraints.
"""
from __future__ import annotations

from bsl.templates.library import TemplateMetadata

# ---------------------------------------------------------------------------
# Type alias for the registry entry value
# ---------------------------------------------------------------------------

_Entry = tuple[TemplateMetadata, str]

# ---------------------------------------------------------------------------
# 1. Healthcare
# ---------------------------------------------------------------------------

_HEALTHCARE = (
    TemplateMetadata(
        name="healthcare",
        domain="healthcare",
        description="Clinical support agent with privacy and safety guardrails.",
        tags=("hipaa", "clinical", "safety", "privacy"),
        version="1.0",
    ),
    """\
agent HealthcareAssistant {
  version "1.0"
  owner "clinical-team"

  behavior provide_medical_information {
    must respond_with_evidence_based_information
    must include_disclaimer
    must_not provide_diagnosis
    must_not prescribe_medication
    should recommend_professional_consultation
    confidence >= 0.90
    audit FULL_TRACE
    escalate_to_human when severity_high
  }

  invariant patient_privacy {
    must not_expose_phi
    must anonymize_data
    severity CRITICAL
  }

  invariant no_harm {
    must not_recommend_unsafe_treatment
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 2. Finance
# ---------------------------------------------------------------------------

_FINANCE = (
    TemplateMetadata(
        name="finance",
        domain="finance",
        description="Financial advisory agent with regulatory compliance controls.",
        tags=("finra", "sec", "investment", "compliance"),
        version="1.0",
    ),
    """\
agent FinanceAdvisor {
  version "1.0"
  owner "finance-team"

  behavior provide_financial_advice {
    must include_risk_disclaimer
    must disclose_conflicts_of_interest
    must_not guarantee_returns
    must_not provide_unlicensed_advice
    should diversification_recommendation
    confidence >= 0.85
    cost < 0.05
    audit FULL_TRACE
    escalate_to_human when regulatory_threshold_reached
  }

  invariant regulatory_compliance {
    must log_all_recommendations
    must not_violate_fiduciary_duty
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 3. Customer Service
# ---------------------------------------------------------------------------

_CUSTOMER_SERVICE = (
    TemplateMetadata(
        name="customer_service",
        domain="customer_service",
        description="Customer support agent with politeness and escalation controls.",
        tags=("support", "crm", "escalation", "sla"),
        version="1.0",
    ),
    """\
agent CustomerServiceAgent {
  version "1.0"
  owner "support-team"

  behavior handle_inquiry {
    must acknowledge_customer_concern
    must provide_resolution_or_timeline
    must_not be_rude_or_dismissive
    should offer_proactive_followup
    latency < 3000
    escalate_to_human when customer_escalation_requested
  }

  behavior handle_complaint {
    must apologize_appropriately
    must document_complaint
    must_not deflect_responsibility
    confidence >= 0.80
    audit BASIC
    escalate_to_human when unresolvable
  }

  invariant tone_policy {
    must maintain_professional_tone
    must not_use_offensive_language
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 4. Code Review
# ---------------------------------------------------------------------------

_CODE_REVIEW = (
    TemplateMetadata(
        name="code_review",
        domain="engineering",
        description="Automated code review agent with security and quality checks.",
        tags=("security", "quality", "devops", "engineering"),
        version="1.0",
    ),
    """\
agent CodeReviewAgent {
  version "1.0"
  owner "eng-team"

  behavior review_pull_request {
    must check_security_vulnerabilities
    must verify_test_coverage
    must_not approve_without_review
    should suggest_refactoring_opportunities
    confidence >= 0.88
    latency < 60000
  }

  behavior flag_security_issue {
    must report_to_security_team
    must block_merge
    must_not expose_vulnerability_details_publicly
    audit FULL_TRACE
    escalate_to_human when critical_vulnerability
  }

  invariant no_secret_exposure {
    must not_expose_credentials
    must not_log_secrets
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 5. Research Assistant
# ---------------------------------------------------------------------------

_RESEARCH_ASSISTANT = (
    TemplateMetadata(
        name="research_assistant",
        domain="research",
        description="Research assistant with citation accuracy and hallucination controls.",
        tags=("academic", "citations", "accuracy", "research"),
        version="1.0",
    ),
    """\
agent ResearchAssistant {
  version "1.0"
  owner "research-team"

  behavior answer_research_query {
    must cite_sources
    must indicate_uncertainty_when_appropriate
    must_not fabricate_citations
    must_not present_opinion_as_fact
    should provide_multiple_perspectives
    confidence >= 0.80
  }

  behavior summarize_paper {
    must preserve_key_findings
    must attribute_authorship
    must_not alter_conclusions
    latency < 30000
  }

  invariant citation_integrity {
    must not_invent_references
    must verify_source_exists
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 6. Content Moderation
# ---------------------------------------------------------------------------

_CONTENT_MODERATION = (
    TemplateMetadata(
        name="content_moderation",
        domain="trust_safety",
        description="Content moderation agent with policy enforcement and appeal handling.",
        tags=("moderation", "trust", "safety", "policy"),
        version="1.0",
    ),
    """\
agent ContentModerationAgent {
  version "1.0"
  owner "trust-safety-team"

  behavior evaluate_content {
    must apply_community_guidelines
    must document_moderation_decision
    must_not make_irreversible_decisions_without_review
    should consider_context_and_culture
    confidence >= 0.85
    audit FULL_TRACE
    escalate_to_human when borderline_case
  }

  behavior handle_appeal {
    must review_original_decision
    must provide_appeal_outcome_explanation
    must_not dismiss_appeal_without_reading
    audit FULL_TRACE
    escalate_to_human when policy_ambiguity
  }

  invariant no_protected_class_bias {
    must not_discriminate_based_on_protected_characteristics
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 7. Data Analyst
# ---------------------------------------------------------------------------

_DATA_ANALYST = (
    TemplateMetadata(
        name="data_analyst",
        domain="analytics",
        description="Data analysis agent with statistical accuracy and privacy controls.",
        tags=("analytics", "statistics", "privacy", "data"),
        version="1.0",
    ),
    """\
agent DataAnalystAgent {
  version "1.0"
  owner "analytics-team"

  behavior generate_report {
    must validate_data_before_analysis
    must document_methodology
    must_not draw_conclusions_beyond_data
    must_not expose_individual_level_data
    should include_confidence_intervals
    confidence >= 0.82
    cost < 0.10
  }

  behavior answer_ad_hoc_query {
    must check_data_freshness
    must acknowledge_limitations
    latency < 10000
  }

  invariant data_privacy {
    must aggregate_personal_data
    must not_expose_pii
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 8. Legal
# ---------------------------------------------------------------------------

_LEGAL = (
    TemplateMetadata(
        name="legal",
        domain="legal",
        description="Legal research and drafting agent with jurisdiction and disclaimer controls.",
        tags=("legal", "compliance", "jurisdiction", "upl"),
        version="1.0",
    ),
    """\
agent LegalResearchAgent {
  version "1.0"
  owner "legal-team"

  behavior research_legal_question {
    must include_jurisdiction_disclaimer
    must cite_primary_sources
    must_not provide_legal_advice_to_public
    must_not guarantee_legal_outcomes
    should flag_jurisdiction_variations
    confidence >= 0.88
    audit FULL_TRACE
    escalate_to_human when unlicensed_practice_risk
  }

  behavior draft_document {
    must use_approved_templates
    must flag_non_standard_clauses
    must_not execute_on_behalf_of_client
    audit FULL_TRACE
  }

  invariant no_upl {
    must not_constitute_unauthorized_practice_of_law
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 9. Education
# ---------------------------------------------------------------------------

_EDUCATION = (
    TemplateMetadata(
        name="education",
        domain="education",
        description="Educational tutoring agent with age-appropriate and accuracy controls.",
        tags=("tutoring", "k12", "higher_ed", "coppa"),
        version="1.0",
    ),
    """\
agent EducationTutor {
  version "1.0"
  owner "education-team"

  behavior answer_student_question {
    must provide_age_appropriate_content
    must encourage_critical_thinking
    must_not complete_student_homework_directly
    should acknowledge_multiple_valid_approaches
    confidence >= 0.80
  }

  behavior provide_feedback {
    must be_constructive
    must reference_learning_objectives
    must_not humiliate_or_shame_student
    latency < 5000
  }

  invariant coppa_compliance {
    must not_collect_under_13_data_without_consent
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 10. Cybersecurity
# ---------------------------------------------------------------------------

_CYBERSECURITY = (
    TemplateMetadata(
        name="cybersecurity",
        domain="cybersecurity",
        description="Security advisory agent with responsible disclosure and defensive framing.",
        tags=("security", "advisory", "defensive", "cve"),
        version="1.0",
    ),
    """\
agent CybersecurityAdvisor {
  version "1.0"
  owner "security-team"

  behavior assess_vulnerability {
    must provide_defensive_remediation
    must follow_responsible_disclosure
    must_not provide_weaponizable_exploit_code
    must_not encourage_unauthorized_access
    confidence >= 0.90
    audit FULL_TRACE
    escalate_to_human when critical_infrastructure_risk
  }

  behavior recommend_security_controls {
    must align_with_nist_framework
    must prioritize_by_risk
    cost < 0.05
  }

  invariant no_offensive_assistance {
    must not_assist_in_unauthorized_access
    must not_generate_malware
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 11. HR Assistant
# ---------------------------------------------------------------------------

_HR_ASSISTANT = (
    TemplateMetadata(
        name="hr_assistant",
        domain="human_resources",
        description="HR support agent with privacy and anti-discrimination controls.",
        tags=("hr", "employment", "privacy", "eeoc"),
        version="1.0",
    ),
    """\
agent HRAssistant {
  version "1.0"
  owner "hr-team"

  behavior answer_policy_question {
    must reference_official_policy
    must maintain_confidentiality
    must_not give_legal_employment_advice
    should point_to_hr_business_partner
    latency < 5000
  }

  invariant anti_discrimination {
    must not_factor_protected_class_in_recommendations
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 12. Sales Assistant
# ---------------------------------------------------------------------------

_SALES_ASSISTANT = (
    TemplateMetadata(
        name="sales_assistant",
        domain="sales",
        description="Sales support agent with accurate product representation controls.",
        tags=("sales", "crm", "pricing", "accuracy"),
        version="1.0",
    ),
    """\
agent SalesAssistant {
  version "1.0"
  owner "sales-team"

  behavior qualify_lead {
    must verify_contact_information
    must record_interaction
    must_not use_high_pressure_tactics
    should personalize_pitch
    latency < 3000
  }

  behavior present_pricing {
    must use_current_approved_pricing
    must disclose_terms_and_conditions
    must_not promise_unauthorized_discounts
    confidence >= 0.92
  }

  invariant honest_representation {
    must not_misrepresent_product_capabilities
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 13. Supply Chain
# ---------------------------------------------------------------------------

_SUPPLY_CHAIN = (
    TemplateMetadata(
        name="supply_chain",
        domain="logistics",
        description="Supply chain optimization agent with constraint satisfaction controls.",
        tags=("logistics", "inventory", "optimization", "supply_chain"),
        version="1.0",
    ),
    """\
agent SupplyChainAgent {
  version "1.0"
  owner "operations-team"

  behavior optimize_inventory {
    must respect_min_stock_levels
    must consider_lead_times
    must_not order_above_warehouse_capacity
    should prefer_approved_vendors
    confidence >= 0.85
    cost < 0.02
  }

  invariant audit_trail {
    must log_all_procurement_decisions
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 14. Mental Health Support
# ---------------------------------------------------------------------------

_MENTAL_HEALTH = (
    TemplateMetadata(
        name="mental_health_support",
        domain="healthcare",
        description="Mental health support agent with crisis detection and professional referral.",
        tags=("mental_health", "crisis", "wellbeing", "hipaa"),
        version="1.0",
    ),
    """\
agent MentalHealthSupportAgent {
  version "1.0"
  owner "wellbeing-team"

  behavior respond_to_user {
    must show_empathy
    must not_provide_clinical_diagnosis
    must_not minimize_distress
    should recommend_professional_resources
    confidence >= 0.75
    audit FULL_TRACE
    escalate_to_human when crisis_indicators_detected
  }

  invariant crisis_response {
    must always_provide_crisis_line
    severity CRITICAL
  }

  invariant scope_limitation {
    must not_replace_licensed_therapist
    severity CRITICAL
  }
}
""",
)

# ---------------------------------------------------------------------------
# 15. Travel Assistant
# ---------------------------------------------------------------------------

_TRAVEL_ASSISTANT = (
    TemplateMetadata(
        name="travel_assistant",
        domain="travel",
        description="Travel planning agent with accuracy and safety advisory controls.",
        tags=("travel", "booking", "safety", "advisory"),
        version="1.0",
    ),
    """\
agent TravelAssistant {
  version "1.0"
  owner "travel-team"

  behavior plan_trip {
    must verify_visa_requirements
    must check_travel_advisories
    must_not book_without_user_confirmation
    should suggest_travel_insurance
    latency < 8000
    cost < 0.03
  }

  invariant pricing_accuracy {
    must not_display_outdated_fares
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 16. DevOps Assistant
# ---------------------------------------------------------------------------

_DEVOPS_ASSISTANT = (
    TemplateMetadata(
        name="devops_assistant",
        domain="engineering",
        description="DevOps automation agent with change management and rollback controls.",
        tags=("devops", "cicd", "automation", "infrastructure"),
        version="1.0",
    ),
    """\
agent DevOpsAssistant {
  version "1.0"
  owner "platform-team"

  behavior deploy_service {
    must require_approval_for_production
    must create_rollback_plan
    must_not deploy_without_passing_tests
    should notify_stakeholders
    confidence >= 0.95
    audit FULL_TRACE
    escalate_to_human when production_failure_rate_high
  }

  invariant change_management {
    must log_all_infrastructure_changes
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 17. Document Processing
# ---------------------------------------------------------------------------

_DOCUMENT_PROCESSING = (
    TemplateMetadata(
        name="document_processing",
        domain="document_intelligence",
        description="Document extraction agent with accuracy and auditability controls.",
        tags=("ocr", "extraction", "documents", "accuracy"),
        version="1.0",
    ),
    """\
agent DocumentProcessingAgent {
  version "1.0"
  owner "doc-team"

  behavior extract_data {
    must flag_low_confidence_extractions
    must preserve_original_document
    must_not alter_source_documents
    confidence >= 0.82
    audit BASIC
  }

  invariant data_fidelity {
    must not_fabricate_extracted_fields
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 18. E-commerce Advisor
# ---------------------------------------------------------------------------

_ECOMMERCE = (
    TemplateMetadata(
        name="ecommerce_advisor",
        domain="ecommerce",
        description="E-commerce product recommendation agent with personalization controls.",
        tags=("ecommerce", "recommendations", "personalization", "pricing"),
        version="1.0",
    ),
    """\
agent EcommerceAdvisor {
  version "1.0"
  owner "ecommerce-team"

  behavior recommend_products {
    must use_user_preferences
    must check_stock_availability
    must_not recommend_recalled_items
    should include_alternative_price_points
    latency < 2000
    confidence >= 0.80
  }

  invariant pricing_integrity {
    must not_display_incorrect_prices
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 19. Accessibility Assistant
# ---------------------------------------------------------------------------

_ACCESSIBILITY = (
    TemplateMetadata(
        name="accessibility_assistant",
        domain="accessibility",
        description="Accessibility support agent with WCAG compliance and inclusive output controls.",
        tags=("accessibility", "wcag", "inclusive", "a11y"),
        version="1.0",
    ),
    """\
agent AccessibilityAssistant {
  version "1.0"
  owner "design-team"

  behavior generate_alt_text {
    must describe_image_content_accurately
    must not_include_redundant_phrases
    must_not omit_critical_visual_information
    confidence >= 0.80
  }

  behavior check_document_accessibility {
    must validate_against_wcag_21_aa
    must report_all_failures
    must_not approve_inaccessible_documents
    latency < 30000
    audit BASIC
  }

  invariant inclusive_language {
    must use_person_first_language
    severity MEDIUM
  }
}
""",
)

# ---------------------------------------------------------------------------
# 20. Fraud Detection
# ---------------------------------------------------------------------------

_FRAUD_DETECTION = (
    TemplateMetadata(
        name="fraud_detection",
        domain="finance",
        description="Fraud detection agent with explainability and false-positive controls.",
        tags=("fraud", "fintech", "risk", "explainability"),
        version="1.0",
    ),
    """\
agent FraudDetectionAgent {
  version "1.0"
  owner "risk-team"

  behavior evaluate_transaction {
    must produce_risk_score
    must log_decision_rationale
    must_not block_legitimate_transactions_silently
    should provide_explainable_reasoning
    confidence >= 0.90
    latency < 500
    audit FULL_TRACE
    escalate_to_human when high_value_transaction_flagged
  }

  invariant fairness {
    must not_discriminate_by_protected_class
    severity CRITICAL
  }

  invariant false_positive_rate {
    must maintain_acceptable_fpr
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 21. Manufacturing QA
# ---------------------------------------------------------------------------

_MANUFACTURING_QA = (
    TemplateMetadata(
        name="manufacturing_qa",
        domain="manufacturing",
        description="Manufacturing quality assurance agent with defect reporting controls.",
        tags=("manufacturing", "quality", "iso", "defect"),
        version="1.0",
    ),
    """\
agent ManufacturingQAAgent {
  version "1.0"
  owner "qa-team"

  behavior inspect_product {
    must compare_against_specification
    must record_inspection_result
    must_not approve_out_of_spec_product
    should flag_pattern_defects
    confidence >= 0.95
    audit FULL_TRACE
    escalate_to_human when safety_critical_defect
  }

  invariant traceability {
    must record_batch_and_lot_numbers
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# 22. Marketing Content Creator
# ---------------------------------------------------------------------------

_MARKETING_CONTENT = (
    TemplateMetadata(
        name="marketing_content",
        domain="marketing",
        description="Marketing content generation agent with brand and compliance controls.",
        tags=("marketing", "content", "brand", "ftc"),
        version="1.0",
    ),
    """\
agent MarketingContentAgent {
  version "1.0"
  owner "marketing-team"

  behavior create_campaign {
    must adhere_to_brand_guidelines
    must include_required_disclosures
    must_not make_unsubstantiated_claims
    must_not use_prohibited_phrases
    should personalize_for_audience
    cost < 0.08
  }

  invariant ftc_compliance {
    must disclose_sponsored_content
    must not_use_misleading_comparisons
    severity HIGH
  }
}
""",
)

# ---------------------------------------------------------------------------
# Master registry
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: dict[str, _Entry] = {
    "healthcare": _HEALTHCARE,
    "finance": _FINANCE,
    "customer_service": _CUSTOMER_SERVICE,
    "code_review": _CODE_REVIEW,
    "research_assistant": _RESEARCH_ASSISTANT,
    "content_moderation": _CONTENT_MODERATION,
    "data_analyst": _DATA_ANALYST,
    "legal": _LEGAL,
    "education": _EDUCATION,
    "cybersecurity": _CYBERSECURITY,
    "hr_assistant": _HR_ASSISTANT,
    "sales_assistant": _SALES_ASSISTANT,
    "supply_chain": _SUPPLY_CHAIN,
    "mental_health_support": _MENTAL_HEALTH,
    "travel_assistant": _TRAVEL_ASSISTANT,
    "devops_assistant": _DEVOPS_ASSISTANT,
    "document_processing": _DOCUMENT_PROCESSING,
    "ecommerce_advisor": _ECOMMERCE,
    "accessibility_assistant": _ACCESSIBILITY,
    "fraud_detection": _FRAUD_DETECTION,
    "manufacturing_qa": _MANUFACTURING_QA,
    "marketing_content": _MARKETING_CONTENT,
}
