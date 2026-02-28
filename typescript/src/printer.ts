/**
 * Pure AST printer and serializer utilities for the BSL SDK.
 *
 * These functions operate entirely on typed AST data structures and
 * produce string output. They do not make network calls and have no
 * side effects. No external dependencies are required.
 *
 * @example
 * ```ts
 * import { createBslPrinter } from "@aumos/bsl";
 *
 * const printer = createBslPrinter();
 *
 * // Pretty-print a diagnostic to a human-readable string
 * const line = printer.formatDiagnostic(diagnostic);
 * console.log(line); // "[BSL001] ERROR at 3:12: Missing must constraint"
 *
 * // Get a summary of an AgentSpec
 * const summary = printer.summarizeSpec(spec);
 * console.log(summary.behavior_count); // 3
 * ```
 */

import type {
  AgentSpec,
  Behavior,
  Constraint,
  Diagnostic,
  Expression,
  Invariant,
  ShouldConstraint,
  Span,
} from "./types.js";

// ---------------------------------------------------------------------------
// Expression printer (recursive, no external dependencies)
// ---------------------------------------------------------------------------

/**
 * Render an Expression AST node back to a BSL source-like string.
 * This is a best-effort printer, not a round-trip-exact formatter.
 *
 * @param expr - The Expression node to render.
 * @returns A human-readable string representation.
 */
export function printExpression(expr: Expression): string {
  switch (expr.kind) {
    case "Identifier":
      return expr.name;

    case "DotAccess":
      return expr.parts.join(".");

    case "StringLit":
      return JSON.stringify(expr.value);

    case "NumberLit":
      return String(expr.value);

    case "BoolLit":
      return expr.value ? "true" : "false";

    case "BinaryOpExpr": {
      const opStr = binOpToString(expr.op);
      return `${printExpression(expr.left)} ${opStr} ${printExpression(expr.right)}`;
    }

    case "UnaryOpExpr":
      return `not ${printExpression(expr.operand)}`;

    case "FunctionCall": {
      const args = expr.arguments.map(printExpression).join(", ");
      return `${expr.name}(${args})`;
    }

    case "ContainsExpr":
      return `${printExpression(expr.subject)} contains ${printExpression(expr.value)}`;

    case "InListExpr": {
      const items = expr.items.map(printExpression).join(", ");
      return `${printExpression(expr.subject)} in [${items}]`;
    }

    case "BeforeExpr":
      return `${printExpression(expr.left)} before ${printExpression(expr.right)}`;

    case "AfterExpr":
      return `${printExpression(expr.left)} after ${printExpression(expr.right)}`;
  }
}

function binOpToString(op: string): string {
  const opMap: Readonly<Record<string, string>> = {
    AND: "and",
    OR: "or",
    EQ: "==",
    NEQ: "!=",
    LT: "<",
    GT: ">",
    LTE: "<=",
    GTE: ">=",
    BEFORE: "before",
    AFTER: "after",
    CONTAINS: "contains",
    IN: "in",
  };
  return opMap[op] ?? op.toLowerCase();
}

// ---------------------------------------------------------------------------
// AgentSpec summary
// ---------------------------------------------------------------------------

/** High-level statistics about a parsed AgentSpec. */
export interface SpecSummary {
  /** The agent name from the BSL specification. */
  readonly agent_name: string;
  /** Optional version string from the spec. */
  readonly version: string | null;
  /** Optional model identifier from the spec. */
  readonly model: string | null;
  /** Optional owner / team name from the spec. */
  readonly owner: string | null;
  /** Number of behavior blocks declared. */
  readonly behavior_count: number;
  /** Number of invariant blocks declared. */
  readonly invariant_count: number;
  /** Number of degradation rules declared. */
  readonly degradation_count: number;
  /** Number of composition clauses declared. */
  readonly composition_count: number;
  /** Sorted list of behavior names. */
  readonly behavior_names: readonly string[];
  /** Sorted list of invariant names. */
  readonly invariant_names: readonly string[];
  /** Total number of hard constraints (must + must_not) across all behaviors. */
  readonly total_must_constraints: number;
  /** Total number of soft constraints (should) across all behaviors. */
  readonly total_should_constraints: number;
}

// ---------------------------------------------------------------------------
// BslPrinter interface
// ---------------------------------------------------------------------------

/** Collection of pure BSL AST printing and summarising functions. */
export interface BslPrinter {
  /**
   * Render a Diagnostic to a human-readable single-line string.
   * Format: "[{code}] {SEVERITY} at {line}:{col}: {message} [(hint: {suggestion})]"
   *
   * @param diagnostic - The Diagnostic to format.
   * @returns A human-readable string representation.
   */
  formatDiagnostic(diagnostic: Diagnostic): string;

  /**
   * Format a list of Diagnostics as a multi-line report.
   * Errors are listed before warnings, sorted by source location within each group.
   *
   * @param diagnostics - Array of diagnostics to format.
   * @returns A formatted multi-line string, or an empty string if no diagnostics.
   */
  formatDiagnosticReport(diagnostics: readonly Diagnostic[]): string;

  /**
   * Produce a SpecSummary with high-level statistics about a parsed AgentSpec.
   *
   * @param spec - The root AgentSpec AST node.
   * @returns A SpecSummary with counts and name lists.
   */
  summarizeSpec(spec: AgentSpec): SpecSummary;

  /**
   * Render a Behavior block to a BSL-like source string.
   *
   * @param behavior - The Behavior AST node to render.
   * @param indentWidth - Number of spaces per indent level. Defaults to 2.
   * @returns A multi-line string approximating BSL source format.
   */
  printBehavior(behavior: Behavior, indentWidth?: number): string;

  /**
   * Render an Invariant block to a BSL-like source string.
   *
   * @param invariant - The Invariant AST node to render.
   * @param indentWidth - Number of spaces per indent level. Defaults to 2.
   * @returns A multi-line string approximating BSL source format.
   */
  printInvariant(invariant: Invariant, indentWidth?: number): string;

  /**
   * Render an Expression to a human-readable string.
   * Delegates to the module-level printExpression utility.
   *
   * @param expr - The Expression node to render.
   * @returns A human-readable string representation.
   */
  printExpression(expr: Expression): string;

  /**
   * Format a source Span to a "line:col" location string.
   *
   * @param span - The Span to format.
   * @returns A string like "3:12".
   */
  formatSpan(span: Span): string;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function indent(level: number, width: number): string {
  return " ".repeat(level * width);
}

function printConstraintLines(
  prefix: string,
  constraints: readonly Constraint[],
  indentWidth: number,
): string[] {
  return constraints.map(
    (c) => `${indent(1, indentWidth)}${prefix} ${printExpression(c.expression)}`,
  );
}

function printShouldLines(
  constraints: readonly ShouldConstraint[],
  indentWidth: number,
): string[] {
  return constraints.map((c) => {
    const pct = c.percentage !== null ? ` ${c.percentage}% of cases` : "";
    return `${indent(1, indentWidth)}should ${printExpression(c.expression)}${pct}`;
  });
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a BslPrinter instance.
 *
 * @returns A BslPrinter with all formatting methods.
 */
export function createBslPrinter(): BslPrinter {
  return {
    formatDiagnostic(diagnostic: Diagnostic): string {
      const loc = `${diagnostic.span.line}:${diagnostic.span.col}`;
      const prefix = `[${diagnostic.code}] ${diagnostic.severity}`;
      const hint = diagnostic.suggestion
        ? ` (hint: ${diagnostic.suggestion})`
        : "";
      return `${prefix} at ${loc}: ${diagnostic.message}${hint}`;
    },

    formatDiagnosticReport(diagnostics: readonly Diagnostic[]): string {
      if (diagnostics.length === 0) {
        return "";
      }

      const errors = diagnostics.filter((d) => d.severity === "ERROR");
      const warnings = diagnostics.filter((d) => d.severity === "WARNING");
      const rest = diagnostics.filter(
        (d) => d.severity !== "ERROR" && d.severity !== "WARNING",
      );

      const sorted = [
        ...errors.slice().sort((a, b) => a.span.line - b.span.line || a.span.col - b.span.col),
        ...warnings.slice().sort((a, b) => a.span.line - b.span.line || a.span.col - b.span.col),
        ...rest.slice().sort((a, b) => a.span.line - b.span.line || a.span.col - b.span.col),
      ];

      return sorted.map((d) => this.formatDiagnostic(d)).join("\n");
    },

    summarizeSpec(spec: AgentSpec): SpecSummary {
      const totalMust = spec.behaviors.reduce(
        (sum, b) => sum + b.must_constraints.length + b.must_not_constraints.length,
        0,
      );
      const totalShould = spec.behaviors.reduce(
        (sum, b) => sum + b.should_constraints.length,
        0,
      );

      return {
        agent_name: spec.name,
        version: spec.version,
        model: spec.model,
        owner: spec.owner,
        behavior_count: spec.behaviors.length,
        invariant_count: spec.invariants.length,
        degradation_count: spec.degradations.length,
        composition_count: spec.compositions.length,
        behavior_names: spec.behaviors
          .map((b) => b.name)
          .slice()
          .sort(),
        invariant_names: spec.invariants
          .map((i) => i.name)
          .slice()
          .sort(),
        total_must_constraints: totalMust,
        total_should_constraints: totalShould,
      };
    },

    printBehavior(behavior: Behavior, indentWidth = 2): string {
      const lines: string[] = [`behavior ${behavior.name} {`];

      if (behavior.when_clause !== null) {
        lines.push(
          `${indent(1, indentWidth)}when ${printExpression(behavior.when_clause)}`,
        );
      }

      lines.push(
        ...printConstraintLines("must", behavior.must_constraints, indentWidth),
        ...printConstraintLines("must_not", behavior.must_not_constraints, indentWidth),
        ...printShouldLines(behavior.should_constraints, indentWidth),
        ...printConstraintLines("may", behavior.may_constraints, indentWidth),
      );

      if (behavior.confidence !== null) {
        const pct = behavior.confidence.is_percentage ? "%" : "";
        lines.push(
          `${indent(1, indentWidth)}confidence ${behavior.confidence.operator} ${behavior.confidence.value}${pct}`,
        );
      }
      if (behavior.latency !== null) {
        const pct = behavior.latency.is_percentage ? "%" : "";
        lines.push(
          `${indent(1, indentWidth)}latency ${behavior.latency.operator} ${behavior.latency.value}${pct}`,
        );
      }
      if (behavior.cost !== null) {
        const pct = behavior.cost.is_percentage ? "%" : "";
        lines.push(
          `${indent(1, indentWidth)}cost ${behavior.cost.operator} ${behavior.cost.value}${pct}`,
        );
      }
      if (behavior.escalation !== null) {
        lines.push(
          `${indent(1, indentWidth)}escalate_to_human when ${printExpression(behavior.escalation.condition)}`,
        );
      }
      if (behavior.audit !== "NONE") {
        lines.push(
          `${indent(1, indentWidth)}audit ${behavior.audit.toLowerCase()}`,
        );
      }

      lines.push("}");
      return lines.join("\n");
    },

    printInvariant(invariant: Invariant, indentWidth = 2): string {
      const lines: string[] = [`invariant ${invariant.name} {`];

      lines.push(
        ...printConstraintLines("must", invariant.constraints, indentWidth),
        ...printConstraintLines("must_not", invariant.prohibitions, indentWidth),
      );

      const scopeStr =
        invariant.applies_to === "ALL_BEHAVIORS"
          ? "all_behaviors"
          : invariant.named_behaviors.join(", ");
      lines.push(`${indent(1, indentWidth)}applies_to ${scopeStr}`);
      lines.push(
        `${indent(1, indentWidth)}severity ${invariant.severity.toLowerCase()}`,
      );

      lines.push("}");
      return lines.join("\n");
    },

    printExpression(expr: Expression): string {
      return printExpression(expr);
    },

    formatSpan(span: Span): string {
      return `${span.line}:${span.col}`;
    },
  };
}
