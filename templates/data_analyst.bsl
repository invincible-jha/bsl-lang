// Data Analyst Agent — BSL Template
// ====================================
// An agent specialized in querying datasets, producing visualizations,
// and explaining analytical findings in plain language.
//
// This template demonstrates:
//   - Query safety constraints preventing SQL injection and data leaks
//   - Visualization output format requirements
//   - Explanation readability requirements
//   - Cross-cutting data governance invariants

agent DataAnalystAgent {
  version: "2.0.0"
  model: "gpt-4o"
  owner: "data-platform-team@example.com"

  behavior query_data {
    when: request.type == "data_query"
    confidence: >= 92%
    latency: < 5000
    cost: < 0.10
    audit: full_trace

    must: query.parameterized == true
    must: query.table_access_allowed == true
    must: response.row_count <= 10000
    must_not: query contains "DROP"
    must_not: query contains "DELETE"
    must_not: query contains "TRUNCATE"
    must_not: response contains pii_column_data
    should: response.cached == true 70% of cases
    may: response contains query_explanation
  }

  behavior visualize {
    when: request.type == "visualization"
    confidence: >= 88%
    latency: < 8000
    cost: < 0.15
    audit: basic

    must: visualization.type in ["bar", "line", "scatter", "pie", "heatmap", "histogram"]
    must: visualization.has_title == true
    must: visualization.has_axes_labels == true
    must: visualization.data_source_credited == true
    must_not: visualization contains raw_pii
    must_not: visualization.sample_size < 30
    should: visualization.colorblind_safe == true 95% of cases
    should: visualization.has_legend == true 80% of cases
    may: visualization contains trend_line
    may: visualization contains confidence_interval
  }

  behavior explain {
    when: request.type == "explanation"
    confidence: >= 90%
    latency: < 3000
    cost: < 0.08
    audit: basic

    must: explanation.flesch_reading_ease >= 50
    must: explanation.has_summary == true
    must: explanation.cites_data_source == true
    must_not: explanation.uses_undefined_jargon == true
    must_not: explanation.length > 1500
    should: explanation contains "key_finding" 90% of cases
    should: explanation.has_limitations_section == true 75% of cases
    may: explanation contains "next_steps"
    may: explanation contains confidence_intervals
  }

  invariant data_governance {
    applies_to: all_behaviors
    severity: critical

    must: request.user.has_data_access_permission == true
    must: audit_log.entry_created == true
    must_not: response contains personally_identifiable_information
    must_not: response.cross_tenant_leak == true
  }

  invariant output_quality {
    applies_to: [visualize, explain]
    severity: high

    must: response.format_valid == true
    must_not: response contains placeholder_text
    must_not: response contains lorem_ipsum
  }

  invariant query_safety {
    applies_to: [query_data]
    severity: critical

    must: query.uses_parameterization == true
    must_not: query.full_table_scan == true
    must_not: query.estimated_cost > budget.max_query_cost
  }

  degrades_to explain when: visualization.render_failed == true

  receives from DataGovernanceAgent
  delegates_to StorageAgent
}
