// healthcare.bsl — HIPAA-oriented invariants for compiler tests.
// Demonstrates domain-specific invariants with critical severity.

agent HealthcareAgent {
  version: "2.0"
  model: "gpt-4o"
  owner: "hipaa-team@hospital.example.com"

  behavior diagnose {
    when: request.type == "diagnosis"
    confidence: >= 95%
    latency: < 2000
    cost: < 0.10
    audit: full_trace

    escalate_to_human when: patient.risk_score > 8

    must: response contains "disclaimer"
    must: response.medical_advice_flag == true
    must_not: response contains patient.ssn
    must_not: response contains patient.dob
    should: response contains "consult_physician" 90% of cases
  }

  behavior schedule {
    when: request.type == "scheduling"
    confidence: >= 88%
    latency: < 1000
    audit: basic

    must: appointment.time_slot != "unavailable"
    must: response contains confirmation_code
    must_not: response contains other_patient.name
  }

  invariant hipaa_compliance {
    applies_to: all_behaviors
    severity: critical

    must: response.data_classification == "protected"
    must_not: response contains patient.ssn
    must_not: response contains patient.credit_card
    must_not: response.logged contains phi_data
  }

  invariant data_minimization {
    applies_to: [diagnose, schedule]
    severity: high

    must_not: response contains unnecessary_patient_data
    must: response.fields_returned < 20
  }
}
