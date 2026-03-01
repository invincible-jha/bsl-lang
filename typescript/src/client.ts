/**
 * HTTP client for the BSL validation and formatting API.
 *
 * Delegates all HTTP transport to `@aumos/sdk-core` which provides
 * automatic retry with exponential back-off, timeout management via
 * `AbortSignal.timeout`, interceptor support, and a typed error hierarchy.
 *
 * The public-facing `ApiResult<T>` envelope is preserved for full
 * backward compatibility with existing callers.
 *
 * @example
 * ```ts
 * import { createBslClient } from "@aumos/bsl";
 *
 * const client = createBslClient({ baseUrl: "http://localhost:8095" });
 *
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

import {
  createHttpClient,
  HttpError,
  NetworkError,
  TimeoutError,
  AumosError,
  type HttpClient,
} from "@aumos/sdk-core";

import type {
  AgentSpec,
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
  /** Parse errors encountered. */
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
// Internal adapter
// ---------------------------------------------------------------------------

async function callApi<T>(
  operation: () => Promise<{ readonly data: T; readonly status: number }>,
): Promise<ApiResult<T>> {
  try {
    const response = await operation();
    return { ok: true, data: response.data };
  } catch (error: unknown) {
    if (error instanceof HttpError) {
      return {
        ok: false,
        error: { error: error.message, detail: String(error.body ?? "") },
        status: error.statusCode,
      };
    }
    if (error instanceof TimeoutError) {
      return {
        ok: false,
        error: { error: "Request timed out", detail: error.message },
        status: 0,
      };
    }
    if (error instanceof NetworkError) {
      return {
        ok: false,
        error: { error: "Network error", detail: error.message },
        status: 0,
      };
    }
    if (error instanceof AumosError) {
      return {
        ok: false,
        error: { error: error.code, detail: error.message },
        status: error.statusCode ?? 0,
      };
    }
    const message = error instanceof Error ? error.message : String(error);
    return {
      ok: false,
      error: { error: "Unexpected error", detail: message },
      status: 0,
    };
  }
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
 * @returns A BslClient instance.
 */
export function createBslClient(config: BslClientConfig): BslClient {
  const http: HttpClient = createHttpClient({
    baseUrl: config.baseUrl,
    timeout: config.timeoutMs ?? 30_000,
    defaultHeaders: config.headers,
  });

  return {
    validate(request: ValidateRequest): Promise<ApiResult<ValidateResponse>> {
      return callApi(() => http.post<ValidateResponse>("/validate", request));
    },

    format(request: FormatRequest): Promise<ApiResult<FormatResponse>> {
      return callApi(() => http.post<FormatResponse>("/format", request));
    },

    parse(request: ParseRequest): Promise<ApiResult<ParseResponse>> {
      return callApi(() => http.post<ParseResponse>("/parse", request));
    },

    lex(request: LexRequest): Promise<ApiResult<LexResponse>> {
      return callApi(() => http.post<LexResponse>("/lex", request));
    },

    check(request: CheckRequest): Promise<ApiResult<CheckResponse>> {
      return callApi(() => http.post<CheckResponse>("/check", request));
    },

    listRules(): Promise<ApiResult<readonly string[]>> {
      return callApi(() => http.get<readonly string[]>("/rules"));
    },
  };
}
