/**
 * TypeScript type definitions for the AumOS Behavioral Specification Language (BSL).
 *
 * Mirrors the Python types defined in:
 *   bsl.grammar.tokens      — TokenType enum, Token dataclass, KEYWORDS map
 *   bsl.ast.nodes           — all AST node types, Span, expression union
 *   bsl.validator.diagnostics — DiagnosticSeverity, Diagnostic
 *
 * All interfaces use readonly fields to match Python's frozen dataclass patterns.
 * The type hierarchy closely follows the Python AST to enable faithful
 * round-tripping between Python-produced ASTs and TypeScript consumers.
 */

// ---------------------------------------------------------------------------
// Shared API result wrapper
// ---------------------------------------------------------------------------

/** Standard error payload returned by the BSL API. */
export interface ApiError {
  readonly error: string;
  readonly detail: string;
}

/**
 * Discriminated union result type for all client operations.
 * Consistent with the pattern used across all @aumos SDK packages.
 */
export type ApiResult<T> =
  | { readonly ok: true; readonly data: T }
  | { readonly ok: false; readonly error: ApiError; readonly status: number };

// ---------------------------------------------------------------------------
// Token types (from bsl.grammar.tokens)
// ---------------------------------------------------------------------------

/**
 * Exhaustive enumeration of all BSL token types.
 * Maps to TokenType(Enum) in Python.
 *
 * Categories:
 *   Declaration keywords: AGENT, BEHAVIOR, INVARIANT
 *   Constraint modalities: MUST, MUST_NOT, SHOULD, MAY
 *   Structural keywords: WHEN, DEGRADES_TO, DELEGATES_TO, RECEIVES
 *   Metadata fields: VERSION, MODEL, OWNER, CONFIDENCE, LATENCY, COST
 *   Special clauses: ESCALATE_TO_HUMAN, AUDIT, APPLIES_TO, SEVERITY
 *   Set operators: IN, OF, CASES, ALL_BEHAVIORS
 *   Logical operators: AND, OR, NOT
 *   Temporal operators: BEFORE, AFTER
 *   String/list operators: CONTAINS
 *   Comparison operators: EQ, NEQ, LT, GT, LTE, GTE
 *   Punctuation: COLON, LBRACE, RBRACE, LBRACKET, RBRACKET, LPAREN, RPAREN, COMMA, DOT, PERCENT
 *   Literals: STRING, NUMBER, BOOL
 *   Identifiers: IDENT
 *   Whitespace/structure: NEWLINE, EOF, COMMENT
 */
export type TokenType =
  // Declaration keywords
  | "AGENT"
  | "BEHAVIOR"
  | "INVARIANT"
  // Constraint modalities
  | "MUST"
  | "MUST_NOT"
  | "SHOULD"
  | "MAY"
  // Structural keywords
  | "WHEN"
  | "DEGRADES_TO"
  | "DELEGATES_TO"
  | "RECEIVES"
  // Metadata field keywords
  | "VERSION"
  | "MODEL"
  | "OWNER"
  | "CONFIDENCE"
  | "LATENCY"
  | "COST"
  // Special clause keywords
  | "ESCALATE_TO_HUMAN"
  | "AUDIT"
  | "APPLIES_TO"
  | "SEVERITY"
  // Set / collection operators
  | "IN"
  | "OF"
  | "CASES"
  | "ALL_BEHAVIORS"
  // Logical operators
  | "AND"
  | "OR"
  | "NOT"
  // Temporal operators
  | "BEFORE"
  | "AFTER"
  // String / list membership
  | "CONTAINS"
  // Comparison operators
  | "EQ"
  | "NEQ"
  | "LT"
  | "GT"
  | "LTE"
  | "GTE"
  // Punctuation
  | "COLON"
  | "LBRACE"
  | "RBRACE"
  | "LBRACKET"
  | "RBRACKET"
  | "LPAREN"
  | "RPAREN"
  | "COMMA"
  | "DOT"
  | "PERCENT"
  // Literals
  | "STRING"
  | "NUMBER"
  | "BOOL"
  // Identifiers
  | "IDENT"
  // Whitespace / structure
  | "NEWLINE"
  | "EOF"
  | "COMMENT";

/**
 * A single scanned BSL token with source-location metadata.
 * Maps to the Token frozen dataclass in Python.
 */
export interface Token {
  /** The TokenType variant for this token. */
  readonly type: TokenType;
  /** The raw text as it appeared in the source. */
  readonly value: string;
  /** 1-based line number in the source file. */
  readonly line: number;
  /** 1-based column number of the first character of the token. */
  readonly col: number;
  /** 0-based byte offset from the start of the source string. */
  readonly offset: number;
}

/**
 * The complete BSL keyword vocabulary.
 * Maps literal keyword text to its TokenType.
 * Mirrors the KEYWORDS dict in Python.
 */
export const BSL_KEYWORDS: Readonly<Record<string, TokenType>> = {
  agent: "AGENT",
  behavior: "BEHAVIOR",
  invariant: "INVARIANT",
  must: "MUST",
  must_not: "MUST_NOT",
  should: "SHOULD",
  may: "MAY",
  when: "WHEN",
  degrades_to: "DEGRADES_TO",
  delegates_to: "DELEGATES_TO",
  receives: "RECEIVES",
  version: "VERSION",
  model: "MODEL",
  owner: "OWNER",
  confidence: "CONFIDENCE",
  latency: "LATENCY",
  cost: "COST",
  escalate_to_human: "ESCALATE_TO_HUMAN",
  audit: "AUDIT",
  applies_to: "APPLIES_TO",
  severity: "SEVERITY",
  in: "IN",
  of: "OF",
  cases: "CASES",
  all_behaviors: "ALL_BEHAVIORS",
  and: "AND",
  or: "OR",
  not: "NOT",
  before: "BEFORE",
  after: "AFTER",
  contains: "CONTAINS",
  true: "BOOL",
  false: "BOOL",
} as const;

// ---------------------------------------------------------------------------
// Source location (from bsl.ast.nodes.Span)
// ---------------------------------------------------------------------------

/**
 * Half-open byte range [start, end) within the source text.
 * Maps to the Span frozen dataclass in Python.
 */
export interface Span {
  /** 0-based byte offset of the first character. */
  readonly start: number;
  /** 0-based byte offset past the last character. */
  readonly end: number;
  /** 1-based line number of the first character. */
  readonly line: number;
  /** 1-based column number of the first character. */
  readonly col: number;
}

/** A sentinel Span used when position info is unavailable. */
export const UNKNOWN_SPAN: Span = {
  start: 0,
  end: 0,
  line: 0,
  col: 0,
} as const;

// ---------------------------------------------------------------------------
// Enums shared across AST node types (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/**
 * Scope of an invariant: all behaviors or a named subset.
 * Maps to AppliesTo(Enum) in Python.
 */
export type AppliesTo = "ALL_BEHAVIORS" | "NAMED";

/**
 * Severity level for an invariant violation.
 * Maps to Severity(Enum) in Python.
 */
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

/**
 * Audit trace detail level for a behavior.
 * Maps to AuditLevel(Enum) in Python.
 */
export type AuditLevel = "NONE" | "BASIC" | "FULL_TRACE";

/**
 * Binary operator kinds used in expressions.
 * Maps to BinOp(Enum) in Python.
 */
export type BinOp =
  | "AND"
  | "OR"
  | "EQ"
  | "NEQ"
  | "LT"
  | "GT"
  | "LTE"
  | "GTE"
  | "BEFORE"
  | "AFTER"
  | "CONTAINS"
  | "IN";

/** Unary operator kinds. Maps to UnaryOpKind(Enum) in Python. */
export type UnaryOpKind = "NOT";

// ---------------------------------------------------------------------------
// Literal sub-types (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/** A double-quoted string literal value. */
export interface StringLit {
  readonly kind: "StringLit";
  readonly value: string;
  readonly span: Span;
}

/** An integer or floating-point literal value. */
export interface NumberLit {
  readonly kind: "NumberLit";
  readonly value: number;
  readonly span: Span;
}

/** A boolean literal (true or false). */
export interface BoolLit {
  readonly kind: "BoolLit";
  readonly value: boolean;
  readonly span: Span;
}

/** Discriminated union of all literal types. */
export type Literal = StringLit | NumberLit | BoolLit;

// ---------------------------------------------------------------------------
// Expression sub-types (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/** A bare identifier reference, e.g. response. */
export interface Identifier {
  readonly kind: "Identifier";
  readonly name: string;
  readonly span: Span;
}

/**
 * A dotted member access, e.g. response.status.
 * The parts tuple holds the components split at each dot.
 */
export interface DotAccess {
  readonly kind: "DotAccess";
  readonly parts: readonly string[];
  readonly span: Span;
}

/** A binary operator expression, e.g. a == b or x and y. */
export interface BinaryOpExpr {
  readonly kind: "BinaryOpExpr";
  readonly op: BinOp;
  readonly left: Expression;
  readonly right: Expression;
  readonly span: Span;
}

/** A unary operator expression, e.g. not flagged. */
export interface UnaryOpExpr {
  readonly kind: "UnaryOpExpr";
  readonly op: UnaryOpKind;
  readonly operand: Expression;
  readonly span: Span;
}

/** A function-call expression, e.g. len(items). */
export interface FunctionCall {
  readonly kind: "FunctionCall";
  readonly name: string;
  readonly arguments: readonly Expression[];
  readonly span: Span;
}

/** A contains membership test, e.g. response contains "error". */
export interface ContainsExpr {
  readonly kind: "ContainsExpr";
  readonly subject: Expression;
  readonly value: Expression;
  readonly span: Span;
}

/** An in [...] membership test, e.g. status in [200, 201]. */
export interface InListExpr {
  readonly kind: "InListExpr";
  readonly subject: Expression;
  readonly items: readonly Expression[];
  readonly span: Span;
}

/** A temporal ordering expression: a before b. */
export interface BeforeExpr {
  readonly kind: "BeforeExpr";
  readonly left: Expression;
  readonly right: Expression;
  readonly span: Span;
}

/** A temporal ordering expression: a after b. */
export interface AfterExpr {
  readonly kind: "AfterExpr";
  readonly left: Expression;
  readonly right: Expression;
  readonly span: Span;
}

/**
 * Discriminated union of all BSL expression node types.
 * The kind field is the discriminant — use it to narrow to a specific variant.
 */
export type Expression =
  | Identifier
  | DotAccess
  | Literal
  | BinaryOpExpr
  | UnaryOpExpr
  | FunctionCall
  | ContainsExpr
  | InListExpr
  | BeforeExpr
  | AfterExpr;

// ---------------------------------------------------------------------------
// Constraint nodes (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/** A must, must_not, or may constraint wrapping an expression. */
export interface Constraint {
  readonly kind: "Constraint";
  readonly expression: Expression;
  readonly span: Span;
}

/**
 * A should constraint with an optional percentage-of-cases qualifier.
 * When percentage is not null, the should clause applies in at least
 * that percentage of cases (0–100).
 */
export interface ShouldConstraint {
  readonly kind: "ShouldConstraint";
  readonly expression: Expression;
  readonly percentage: number | null;
  readonly span: Span;
}

// ---------------------------------------------------------------------------
// Threshold and escalation clauses (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/**
 * A threshold specification, e.g. < 500 or >= 95%.
 * operator is one of: "<", ">", "<=", ">=", "==", "!=".
 */
export interface ThresholdClause {
  readonly kind: "ThresholdClause";
  /** One of: "<", ">", "<=", ">=", "==", "!=". */
  readonly operator: string;
  /** The numeric threshold value. */
  readonly value: number;
  /** Whether the value is expressed as a percentage. */
  readonly is_percentage: boolean;
  readonly span: Span;
}

/** An escalate_to_human when clause. */
export interface EscalationClause {
  readonly kind: "EscalationClause";
  readonly condition: Expression;
  readonly span: Span;
}

// ---------------------------------------------------------------------------
// Behavior node (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/**
 * A named behavior block within an agent specification.
 * Maps to the Behavior frozen dataclass in Python.
 */
export interface Behavior {
  readonly kind: "Behavior";
  /** The identifier for this behavior. */
  readonly name: string;
  /** Optional precondition expression (when clause). */
  readonly when_clause: Expression | null;
  /** Hard constraints that must always hold. */
  readonly must_constraints: readonly Constraint[];
  /** Hard prohibitions that must never hold. */
  readonly must_not_constraints: readonly Constraint[];
  /** Soft constraints with optional percentage-of-cases qualifier. */
  readonly should_constraints: readonly ShouldConstraint[];
  /** Permitted (but not required) actions. */
  readonly may_constraints: readonly Constraint[];
  /** Optional minimum confidence threshold. */
  readonly confidence: ThresholdClause | null;
  /** Optional maximum latency threshold. */
  readonly latency: ThresholdClause | null;
  /** Optional cost threshold. */
  readonly cost: ThresholdClause | null;
  /** Optional escalation-to-human clause. */
  readonly escalation: EscalationClause | null;
  /** Audit level for this behavior. */
  readonly audit: AuditLevel;
  readonly span: Span;
}

// ---------------------------------------------------------------------------
// Invariant node (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/**
 * A named invariant block that applies across behaviors.
 * Maps to the Invariant frozen dataclass in Python.
 */
export interface Invariant {
  readonly kind: "Invariant";
  /** The identifier for this invariant. */
  readonly name: string;
  /** Expressions that must hold. */
  readonly constraints: readonly Constraint[];
  /** Expressions that must not hold. */
  readonly prohibitions: readonly Constraint[];
  /** Scope selector: ALL_BEHAVIORS or NAMED. */
  readonly applies_to: AppliesTo;
  /**
   * When applies_to is NAMED, the list of behavior names
   * this invariant covers.
   */
  readonly named_behaviors: readonly string[];
  /** How serious a violation of this invariant is. */
  readonly severity: Severity;
  readonly span: Span;
}

// ---------------------------------------------------------------------------
// Degradation and composition nodes (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/** A degrades_to fallback specification. */
export interface Degradation {
  readonly kind: "Degradation";
  /** The name of the fallback behavior or agent. */
  readonly fallback: string;
  /** The condition under which degradation is triggered. */
  readonly condition: Expression;
  readonly span: Span;
}

/** A receives from composition clause. */
export interface Receives {
  readonly kind: "Receives";
  /** The agent from which this agent receives input. */
  readonly source_agent: string;
  readonly span: Span;
}

/** A delegates_to composition clause. */
export interface Delegates {
  readonly kind: "Delegates";
  /** The agent to which this agent delegates. */
  readonly target_agent: string;
  readonly span: Span;
}

/** Discriminated union of composition clause types. */
export type Composition = Receives | Delegates;

// ---------------------------------------------------------------------------
// AgentSpec — top-level AST node (from bsl.ast.nodes)
// ---------------------------------------------------------------------------

/**
 * The root AST node representing a complete BSL agent specification.
 * Maps to the AgentSpec frozen dataclass in Python.
 */
export interface AgentSpec {
  readonly kind: "AgentSpec";
  /** The agent identifier. */
  readonly name: string;
  /** Optional version string (semver). */
  readonly version: string | null;
  /** Optional model identifier, e.g. "gpt-4o". */
  readonly model: string | null;
  /** Optional owner / team name. */
  readonly owner: string | null;
  /** Ordered list of behavior declarations. */
  readonly behaviors: readonly Behavior[];
  /** Ordered list of invariant declarations. */
  readonly invariants: readonly Invariant[];
  /** Degradation (fallback) rules. */
  readonly degradations: readonly Degradation[];
  /** Composition (receives/delegates) clauses. */
  readonly compositions: readonly Composition[];
  /** Source location of the entire agent block. */
  readonly span: Span;
}

// ---------------------------------------------------------------------------
// Diagnostic types (from bsl.validator.diagnostics)
// ---------------------------------------------------------------------------

/**
 * Severity levels for diagnostics, aligned with LSP conventions.
 * Maps to DiagnosticSeverity(Enum) in Python.
 */
export type DiagnosticSeverity = "ERROR" | "WARNING" | "INFORMATION" | "HINT";

/**
 * A single validation or lint finding.
 * Maps to the Diagnostic frozen dataclass in Python.
 */
export interface Diagnostic {
  /** How serious this finding is. */
  readonly severity: DiagnosticSeverity;
  /** A short machine-readable identifier, e.g. "BSL001". */
  readonly code: string;
  /** Human-readable description of the problem. */
  readonly message: string;
  /** Source location of the offending code. */
  readonly span: Span;
  /** Optional human-readable fix suggestion. */
  readonly suggestion: string | null;
  /** The rule name that produced this diagnostic. */
  readonly rule: string;
}

/**
 * Return true if a Diagnostic should block a successful validation.
 * Matches the is_error property on Python's Diagnostic dataclass.
 */
export function isDiagnosticError(diagnostic: Diagnostic): boolean {
  return diagnostic.severity === "ERROR";
}
