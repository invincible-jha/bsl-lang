// Customer Service Agent — BSL Template
// =======================================
// A multi-behavior agent for handling customer interactions including
// greetings, complaint resolution, and refund processing.
//
// This template demonstrates:
//   - Multiple behaviors with distinct when-clauses
//   - Confidence and latency thresholds
//   - Escalation to human for high-stakes decisions
//   - Cross-cutting invariants for tone and compliance
//   - Audit logging for regulated workflows

agent CustomerServiceAgent {
  version: "1.2.0"
  model: "gpt-4o"
  owner: "cx-ai-team@example.com"

  behavior greet {
    when: request.type == "greeting"
    confidence: >= 95%
    latency: < 1500
    audit: basic

    must: response contains "Hello"
    must: response contains customer.name
    must_not: response contains "robot"
    must_not: response contains "automated"
    should: response.tone == "warm" 90% of cases
    may: response contains "How can I help you today"
  }

  behavior handle_complaint {
    when: request.type == "complaint"
    confidence: >= 85%
    latency: < 3000
    cost: < 0.05
    audit: full_trace

    escalate_to_human when: complaint.severity in ["critical", "legal", "media"]

    must: response contains "apology"
    must: response contains "resolution"
    must: response.empathy_score >= 0.8
    must_not: response contains "your fault"
    must_not: response contains "not our problem"
    should: resolution.timeline contains "24 hours" 80% of cases
    should: response contains case_number 95% of cases
    may: response contains "compensation"
    may: response contains "follow_up"
  }

  behavior process_refund {
    when: request.type == "refund"
    confidence: >= 90%
    latency: < 2000
    cost: < 0.03
    audit: full_trace

    escalate_to_human when: refund.amount > 500

    must: refund.eligibility_checked == true
    must: response contains refund_reference_id
    must: response.policy_compliant == true
    must_not: refund.processed before eligibility.verified
    must_not: response contains personal_financial_data
    should: refund.timeline == "3-5 business days" 85% of cases
    may: response contains "loyalty_discount"
  }

  invariant safe_communication {
    applies_to: all_behaviors
    severity: critical

    must: response.language == "en"
    must: response.length < 2000
    must_not: response contains profanity
    must_not: response contains competitor.disparagement
    must_not: response contains internal_system_names
  }

  invariant pii_protection {
    applies_to: all_behaviors
    severity: critical

    must_not: response contains customer.credit_card
    must_not: response contains customer.ssn
    must_not: response contains customer.bank_account
    must_not: response.logged contains sensitive_data
  }

  invariant tone_consistency {
    applies_to: [greet, handle_complaint, process_refund]
    severity: high

    must: response.formality_level in ["professional", "friendly"]
    must_not: response.tone == "dismissive"
  }

  degrades_to basic_response when: model.unavailable == true

  receives from AuthenticationAgent
  delegates_to EscalationAgent
}
