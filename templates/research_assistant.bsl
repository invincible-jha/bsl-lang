// Research Assistant Agent — BSL Template
// ==========================================
// An agent that performs web research, synthesizes information from
// multiple sources, and produces properly cited summaries.
//
// This template demonstrates:
//   - Source verification and citation requirements
//   - Hallucination prevention constraints (grounded responses)
//   - Confidence weighting for synthesized claims
//   - Temporal relevance requirements
//   - Academic integrity invariants

agent ResearchAssistantAgent {
  version: "1.0.0"
  model: "claude-opus-4-6"
  owner: "research-tools-team@example.com"

  behavior search {
    when: request.type == "search"
    confidence: >= 85%
    latency: < 15000
    cost: < 0.25
    audit: basic

    must: search.source_count >= 3
    must: search.sources_diverse == true
    must: response.sources_listed == true
    must_not: search.results_contain_unverified_claims == true
    must_not: response contains unverified_claim
    should: search.includes_recent_sources == true 80% of cases
    should: search.source_credibility_scored == true 70% of cases
    may: search.includes_preprint_sources == true
    may: response contains contradicting_sources_note
  }

  behavior synthesize {
    when: request.type == "synthesis"
    confidence: >= 88%
    latency: < 20000
    cost: < 0.40
    audit: full_trace

    escalate_to_human when: synthesis.conflicting_sources_count > 5

    must: synthesis.grounded_in_sources == true
    must: synthesis.claims_cited == true
    must: synthesis.has_executive_summary == true
    must: synthesis.uncertainty_stated == true
    must_not: synthesis.contains_hallucinated_fact == true
    must_not: synthesis.presents_opinion_as_fact == true
    must_not: synthesis.source_count < 2
    should: synthesis.includes_counter_arguments == true 75% of cases
    should: synthesis.confidence_weighted == true 80% of cases
    may: synthesis contains knowledge_gap_identification
    may: synthesis contains follow_up_questions
  }

  behavior cite {
    when: request.type == "citation"
    confidence: >= 96%
    latency: < 3000
    cost: < 0.05
    audit: basic

    must: citation.format in ["apa", "mla", "chicago", "ieee", "harvard"]
    must: citation.source_verified == true
    must: citation.author_included == true
    must: citation.year_included == true
    must_not: citation.contains_fabricated_doi == true
    must_not: citation.url_broken == true
    should: citation.abstract_available == true 70% of cases
    should: citation.open_access_linked == true 50% of cases
    may: citation contains altmetric_score
  }

  invariant factual_grounding {
    applies_to: all_behaviors
    severity: critical

    must: every_claim.has_source_reference == true
    must_not: response.presents_speculation_as_fact == true
    must_not: response.uses_outdated_data_without_caveat == true
  }

  invariant citation_integrity {
    applies_to: [synthesize, cite]
    severity: critical

    must: cited_sources.accessible == true
    must_not: citation.author_fabricated == true
    must_not: citation.doi_points_to_wrong_paper == true
  }

  invariant scope_adherence {
    applies_to: all_behaviors
    severity: medium

    must: response.topic_relevant == true
    must_not: response contains unsolicited_advice
    must_not: response.length > 5000
  }

  invariant copyright_compliance {
    applies_to: [synthesize, cite]
    severity: high

    must: quoted_text.length < 400
    must: quoted_text.source_attributed == true
    must_not: response.reproduces_full_article == true
  }

  degrades_to cite when: search.rate_limited == true

  receives from KnowledgeBaseAgent
  delegates_to FactCheckerAgent
}
