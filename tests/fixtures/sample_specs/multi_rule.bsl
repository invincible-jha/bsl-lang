// multi_rule.bsl — Multiple invariants, behaviors, and escalation clauses.
// Used to stress-test the compiler's ability to handle complex specs.

agent MultiRuleAgent {
  version: "3.0"
  model: "gpt-4o"
  owner: "platform-team@example.com"

  behavior classify {
    when: request.type == "classification"
    confidence: >= 80%
    latency: < 500
    audit: basic

    must: response.category in ["A", "B", "C"]
    must: response.score >= 0
    must_not: response.category == "unknown"
    should: response.confidence_score >= 0.7 80% of cases
  }

  behavior summarize {
    when: request.type == "summary"
    confidence: >= 85%
    latency: < 3000
    cost: < 0.05
    audit: full_trace

    escalate_to_human when: document.length > 50000

    must: response.length < 500
    must: response contains summary_marker
    must_not: response contains original_text
    should: response.readability_score >= 60 75% of cases
    may: response contains "key_points"
  }

  behavior translate {
    when: request.type == "translation"
    confidence: >= 92%
    latency: < 2000
    audit: basic

    must: response.target_language == request.target_lang
    must: response.length > 0
    must_not: response contains untranslated_tokens
  }

  invariant safety_baseline {
    applies_to: all_behaviors
    severity: critical

    must: response.toxicity_score < 0.1
    must_not: response contains hate_speech
    must_not: response contains violent_content
  }

  invariant cost_control {
    applies_to: [summarize, translate]
    severity: medium

    must: request.token_count < 100000
    must_not: response.token_count > 4000
  }

  invariant audit_trail {
    applies_to: all_behaviors
    severity: high

    must: request.trace_id != "missing"
    must: response.timestamp != "missing"
  }

  degrades_to BasicFallbackAgent when: model.unavailable == true
  receives from InputValidatorAgent
  delegates_to OutputFormatterAgent
}
