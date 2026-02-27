// basic.bsl — Simple invariant specification for compiler tests.
// Tests a single agent with one behavior and one invariant.

agent BasicAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "test@example.com"

  behavior respond {
    must: response contains "Hello"
    must_not: response contains "error"
    confidence: >= 90%
    audit: basic
  }

  invariant no_pii {
    applies_to: all_behaviors
    severity: critical

    must_not: response contains "SSN"
    must_not: response contains "credit_card"
  }
}
