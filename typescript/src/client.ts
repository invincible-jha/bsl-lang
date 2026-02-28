/**
 * HTTP client for the BSL validation and formatting API.
 *
 * Uses the Fetch API (available natively in Node 18+, browsers, and Deno).
 * No external dependencies required.
 *
 * @example
 * ```ts
 * import { createBslClient } from "@aumos/bsl";
 *
 * const client = createBslClient({ baseUrl: "http://localhost:8095" });
 *
 * // Validate a BSL source string
 * const result = await client.validate({
 *   source: `agent my-agent {\n  behavior greet {\n    must respond == true\n  }\n}`,
 *   strict: false,
 * });
 *
 * if (result.ok) {
 *   if (result.data.valid) {
 *     console.log("Valid BSL specification");
 *   } else {
 *     for (const diagnostic of result.data.diagnostics) {
 *       console.error(`[${diagnostic.code}] ${diagnostic.message}`);
 *     }
 *   }
 * }
 * ```
 */

import type {
  AgentSpec,
  ApiError,
  ApiResult,
  Diagnostic,
  Token,
} from "./types.js";

// ---------------------------------------------------------------------------
// Client configuration
// ---------------------------------------------------------------------------

/** Configuration options for the BslClient. */
export interface BslClientConfig {
  /** Base URL of the BSL API server (e.g. "http://localhost:8095"). */
  readonly baseUrl: string;
  /** Optional request timeout in milliseconds. Defaults to 30000. */
  readonly timeoutMs?: number;
  /** Optional extra HTTP headers sent with every request. */
  readonly headers?: Readonly<Record<string, string>>;
}

// ---------------------------------------------------------------------------
// Request and response types
// ---------------------------------------------------------------------------

/** Request body for the BSL validate endpoint. */
export interface ValidateRequest {
  /** The BSL source text to validate. */
  readonly source: string;
  /**
   * When true, WARNING-level diagnostics are promoted to ERROR severity,
   * causing validation to fail on warnings.
   * Mirrors the strict parameter on Python's Validator.
   */
  readonly strict?: boolean;
}

/** Response from the BSL validate endpoint. */
export interface ValidateResponse {
  /** Whether the source passed validation with no ERROR-level diagnostics. */
  readonly valid: boolean;
  /** All diagnostics produced by validation, sorted by source location. */
  readonly diagnostics: readonly Diagnostic[];
  /** Number of ERROR-level diagnostics. */
  readonly error_count: number;
  /** Number of WARNING-level diagnostics. */
  readonly warning_count: number;
}

/** Request body for the BSL format endpoint. */
export interface FormatRequest {
  /** The BSL source text to format. */
  readonly source: string;
  /**
   * Number of spaces per indent level.
   * Defaults to 2 on the server side.
   */
  readonly indent_width?: number;
}

/** Response from the BSL format endpoint. */
export interface FormatResponse {
  /** The formatted BSL source text. */
  readonly formatted: string;
  /** Whether the source was changed by formatting. */
  readonly changed: boolean;
}

/** Request body for the BSL parse endpoint. */
export interface ParseRequest {
  /** The BSL source text to parse. */
  readonly source: string;
}

/** Response from the BSL parse endpoint. */
export interface ParseResponse {
  /** Whether parsing succeeded without fatal errors. */
  readonly success: boolean;
  /** The root AgentSpec AST node, or null if parsing failed. */
  readonly spec: AgentSpec | null;
  /**
   * Parse errors encountered. These correspond to ERROR-level diagnostics
   * produced during parsing (before semantic validation).
   */
  readonly errors: readonly Diagnostic[];
}

/** Request body for the BSL lex endpoint. */
export interface LexRequest {
  /** The BSL source text to tokenise. */
  readonly source: string;
}

/** Response from the BSL lex endpoint. */
export interface LexResponse {
  /** The token stream produced by the lexer, excluding COMMENT tokens. */
  readonly tokens: readonly Token[];
  /** Number of tokens in the stream (excluding EOF). */
  readonly token_count: number;
}

/** Request body for the BSL check endpoint (parse + validate in one call). */
export interface CheckRequest {
  /** The BSL source text to check. */
  readonly source: string;
  /** When true, treat warnings as errors. Defaults to false. */
  readonly strict?: boolean;
}

/** Response from the BSL check endpoint. */
export interface CheckResponse {
  /** Whether the source is syntactically and semantically valid. */
  readonly valid: boolean;
  /** The root AgentSpec AST node, or null if parsing failed. */
  readonly spec: AgentSpec | null;
  /** All diagnostics (parse errors + semantic diagnostics) sorted by location. */
  readonly diagnostics: readonly Diagnostic[];
  /** Number of ERROR-level diagnostics. */
  readonly error_count: number;
  /** Number of WARNING-level diagnostics. */
  readonly warning_count: number;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function fetchJson<T>(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    clearTimeout(timeoutId);

    const body = (await response.json()) as unknown;

    if (!response.ok) {
      const errorBody = body as Partial<ApiError>;
      return {
        ok: false,
        error: {
          error: errorBody.error ?? "Unknown error",
          detail: errorBody.detail ?? "",
        },
        status: response.status,
      };
    }

    return { ok: true, data: body as T };
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: { error: "Network error", detail: message },
      status: 0,
    };
  }
}

function buildHeaders(
  extraHeaders: Readonly<Record<string, string>> | undefined,
): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...extraHeaders,
  };
}

// ---------------------------------------------------------------------------
// Client interface
// ---------------------------------------------------------------------------

/** Typed HTTP client for the BSL API server. */
export interface BslClient {
  /**
   * Validate a BSL source string against the full semantic rule set.
   *
   * @param request - Source text and optional strict-mode flag.
   * @returns ValidateResponse with valid flag and sorted diagnostics.
   */
  validate(request: ValidateRequest): Promise<ApiResult<ValidateResponse>>;

  /**
   * Format a BSL source string according to the canonical style.
   *
   * @param request - Source text and optional indent width.
   * @returns FormatResponse with the formatted source and a changed flag.
   */
  format(request: FormatRequest): Promise<ApiResult<FormatResponse>>;

  /**
   * Parse a BSL source string and return the AgentSpec AST.
   *
   * @param request - Source text to parse.
   * @returns ParseResponse with the AgentSpec root node and any parse errors.
   */
  parse(request: ParseRequest): Promise<ApiResult<ParseResponse>>;

  /**
   * Tokenise a BSL source string and return the full token stream.
   *
   * @param request - Source text to lex.
   * @returns LexResponse with the token list and count.
   */
  lex(request: LexRequest): Promise<ApiResult<LexResponse>>;

  /**
   * Parse and validate a BSL source string in a single call.
   *
   * Combines the parse and validate steps, returning the AST alongside all
   * diagnostics (parse errors + semantic validation findings) in one request.
   *
   * @param request - Source text, optional strict flag.
   * @returns CheckResponse with spec, valid flag, and all diagnostics.
   */
  check(request: CheckRequest): Promise<ApiResult<CheckResponse>>;

  /**
   * Retrieve a list of all built-in validation rule identifiers.
   *
   * @returns Array of rule IDs in alphabetical order.
   */
  listRules(): Promise<ApiResult<readonly string[]>>;
}

// ---------------------------------------------------------------------------
// Client factory
// ---------------------------------------------------------------------------

/**
 * Create a typed HTTP client for the BSL API server.
 *
 * @param config - Client configuration including base URL.
 * @returns A BslClient instance backed by the Fetch API.
 */
export function createBslClient(config: BslClientConfig): BslClient {
  const { baseUrl, timeoutMs = 30_000, headers: extraHeaders } = config;
  const baseHeaders = buildHeaders(extraHeaders);

  return {
    async validate(
      request: ValidateRequest,
    ): Promise<ApiResult<ValidateResponse>> {
      return fetchJson<ValidateResponse>(
        `${baseUrl}/validate`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(request),
        },
        timeoutMs,
      );
    },

    async format(request: FormatRequest): Promise<ApiResult<FormatResponse>> {
      return fetchJson<FormatResponse>(
        `${baseUrl}/format`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(request),
        },
        timeoutMs,
      );
    },

    async parse(request: ParseRequest): Promise<ApiResult<ParseResponse>> {
      return fetchJson<ParseResponse>(
        `${baseUrl}/parse`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(request),
        },
        timeoutMs,
      );
    },

    async lex(request: LexRequest): Promise<ApiResult<LexResponse>> {
      return fetchJson<LexResponse>(
        `${baseUrl}/lex`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(request),
        },
        timeoutMs,
      );
    },

    async check(request: CheckRequest): Promise<ApiResult<CheckResponse>> {
      return fetchJson<CheckResponse>(
        `${baseUrl}/check`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(request),
        },
        timeoutMs,
      );
    },

    async listRules(): Promise<ApiResult<readonly string[]>> {
      return fetchJson<readonly string[]>(
        `${baseUrl}/rules`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },
  };
}

