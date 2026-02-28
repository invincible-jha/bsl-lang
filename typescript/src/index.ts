/**
 * @aumos/bsl
 *
 * TypeScript client for the AumOS Behavioral Specification Language (BSL).
 * Provides HTTP client, pure AST printer utilities, and complete type definitions
 * for BSL tokens, AST nodes, and validation diagnostics.
 */

// --- Client and configuration ---
export type {
  BslClient,
  BslClientConfig,
  ValidateRequest,
  ValidateResponse,
  FormatRequest,
  FormatResponse,
  ParseRequest,
  ParseResponse,
  LexRequest,
  LexResponse,
  CheckRequest,
  CheckResponse,
} from "./client.js";
export { createBslClient } from "./client.js";

// --- Core types ---
export type {
  // API wrapper
  ApiError,
  ApiResult,

  // Token types
  TokenType,
  Token,

  // Source location
  Span,

  // Enum types
  AppliesTo,
  Severity,
  AuditLevel,
  BinOp,
  UnaryOpKind,

  // Literal nodes
  StringLit,
  NumberLit,
  BoolLit,
  Literal,

  // Expression nodes
  Identifier,
  DotAccess,
  BinaryOpExpr,
  UnaryOpExpr,
  FunctionCall,
  ContainsExpr,
  InListExpr,
  BeforeExpr,
  AfterExpr,
  Expression,

  // Constraint nodes
  Constraint,
  ShouldConstraint,

  // Threshold and escalation
  ThresholdClause,
  EscalationClause,

  // Top-level AST nodes
  Behavior,
  Invariant,
  Degradation,
  Receives,
  Delegates,
  Composition,
  AgentSpec,

  // Diagnostic types
  DiagnosticSeverity,
  Diagnostic,
} from "./types.js";

// Named constants and type guards from types
export { BSL_KEYWORDS, UNKNOWN_SPAN, isDiagnosticError } from "./types.js";

// --- AST printer utilities ---
export type { BslPrinter, SpecSummary } from "./printer.js";
export { createBslPrinter, printExpression } from "./printer.js";
