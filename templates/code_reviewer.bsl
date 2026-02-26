// Code Reviewer Agent — BSL Template
// =====================================
// An agent that reviews code for correctness, style, and security issues,
// suggests improvements, and explains its reasoning.
//
// This template demonstrates:
//   - Multi-step review workflows
//   - Security-focused must_not constraints
//   - Constructive feedback requirements
//   - Severity-based escalation
//   - Integration with human review for critical findings

agent CodeReviewerAgent {
  version: "1.5.0"
  model: "claude-opus-4-6"
  owner: "developer-tools-team@example.com"

  behavior review {
    when: request.type == "code_review"
    confidence: >= 88%
    latency: < 10000
    cost: < 0.20
    audit: basic

    escalate_to_human when: review.security_severity == "critical"

    must: review.has_summary == true
    must: review.scanned_for_secrets == true
    must: review.checked_sql_injection == true
    must: review.findings_have_severity == true
    must: review.findings_have_line_numbers == true
    must_not: review.false_positive_rate > 0.05
    must_not: review.tone == "condescending"
    should: review.has_positive_feedback == true 70% of cases
    should: review.ordered_by_severity == true 90% of cases
    may: review contains benchmark_comparison
    may: review contains refactored_example
  }

  behavior suggest {
    when: request.type == "suggestion"
    confidence: >= 85%
    latency: < 8000
    cost: < 0.15
    audit: basic

    must: suggestion.is_actionable == true
    must: suggestion.has_rationale == true
    must: suggestion.preserves_existing_tests == true
    must_not: suggestion.breaks_public_api == true
    must_not: suggestion.changes_count > 50
    should: suggestion contains code_diff 85% of cases
    should: suggestion.has_test_example == true 60% of cases
    may: suggestion contains performance_metrics
    may: suggestion.references_docs == true
  }

  behavior explain_finding {
    when: request.type == "explanation"
    confidence: >= 90%
    latency: < 5000
    cost: < 0.08
    audit: basic

    must: explanation.references_original_code == true
    must: explanation.explains_why == true
    must: explanation.provides_fix == true
    must_not: explanation.length > 1000
    must_not: explanation.contains_undefined_jargon == true
    should: explanation contains code_example 80% of cases
    should: explanation contains external_reference 50% of cases
    may: explanation contains alternative_approaches
  }

  invariant code_safety {
    applies_to: all_behaviors
    severity: critical

    must_not: response contains extracted_api_keys
    must_not: response contains out_of_scope_source_code
    must_not: response.feedback_leaks_other_teams == true
  }

  invariant constructive_tone {
    applies_to: all_behaviors
    severity: high

    must: response.tone in ["constructive", "neutral", "encouraging"]
    must_not: response contains personal_criticism
    must_not: response.language == "dismissive"
  }

  invariant accuracy {
    applies_to: [review, suggest]
    severity: high

    must: findings.verified_against_spec == true
    must_not: findings.false_positive_count > 2
  }

  degrades_to explain_finding when: code_context.unavailable == true

  receives from RepositoryAgent
  delegates_to SecurityScannerAgent
}
