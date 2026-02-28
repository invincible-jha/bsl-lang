/**
 * BSL Language — VS Code Extension Entry Point
 *
 * Activates on any BSL file and provides:
 *   - On-save validation via `bsl-lang validate`
 *   - On-save lint via `bsl-lang lint`
 *   - On-save formatting via `bsl-lang format` (when enabled)
 *   - Status bar item showing BSL spec validity
 *   - Commands: bsl.validate, bsl.format, bsl.lint
 *
 * All diagnostics are surfaced through the VS Code Problems panel.
 */

import * as vscode from "vscode";
import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

// ── Constants ─────────────────────────────────────────────────────────────────

const BSL_LANGUAGE_ID = "bsl";
const DIAGNOSTICS_SOURCE = "bsl-lang";
const STATUS_BAR_PRIORITY = 100;

// ── Types ─────────────────────────────────────────────────────────────────────

interface BslDiagnosticLine {
  line: number;
  column: number;
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
}

interface BslCommandResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

// ── Configuration helpers ─────────────────────────────────────────────────────

function getBslExecutablePath(): string {
  const configuration = vscode.workspace.getConfiguration("bsl");
  return configuration.get<string>("executablePath") ?? "bsl-lang";
}

function isValidateOnSaveEnabled(): boolean {
  const configuration = vscode.workspace.getConfiguration("bsl");
  return configuration.get<boolean>("validateOnSave") ?? true;
}

function isLintOnSaveEnabled(): boolean {
  const configuration = vscode.workspace.getConfiguration("bsl");
  return configuration.get<boolean>("lintOnSave") ?? true;
}

function isFormatOnSaveEnabled(): boolean {
  const configuration = vscode.workspace.getConfiguration("bsl");
  return configuration.get<boolean>("formatOnSave") ?? false;
}

function isStrictModeEnabled(): boolean {
  const configuration = vscode.workspace.getConfiguration("bsl");
  return configuration.get<boolean>("strict") ?? false;
}

// ── BSL CLI runner ────────────────────────────────────────────────────────────

async function runBslCommand(
  subcommand: string,
  filePath: string,
  extraArgs: string[] = []
): Promise<BslCommandResult> {
  const executablePath = getBslExecutablePath();
  const args = [subcommand, filePath, ...extraArgs];

  if (isStrictModeEnabled() && subcommand !== "format") {
    args.push("--strict");
  }

  try {
    const { stdout, stderr } = await execFileAsync(executablePath, args, {
      timeout: 30_000,
      encoding: "utf8",
    });
    return { stdout, stderr, exitCode: 0 };
  } catch (error: unknown) {
    const nodeError = error as NodeJS.ErrnoException & {
      stdout?: string;
      stderr?: string;
      code?: number | string;
    };

    // Non-zero exit code from bsl-lang is normal (means validation found issues)
    if (
      nodeError.code !== "ENOENT" &&
      nodeError.code !== "EACCES" &&
      nodeError.code !== undefined &&
      typeof nodeError.code === "number"
    ) {
      return {
        stdout: nodeError.stdout ?? "",
        stderr: nodeError.stderr ?? "",
        exitCode: nodeError.code,
      };
    }

    // ENOENT — executable not found
    if (nodeError.code === "ENOENT") {
      throw new Error(
        `BSL executable not found at '${executablePath}'. ` +
          `Install with: pip install bsl-lang  — or set bsl.executablePath in settings.`
      );
    }

    throw error;
  }
}

// ── Diagnostic parsing ────────────────────────────────────────────────────────

/**
 * Parse bsl-lang JSON diagnostic output into VS Code Diagnostic objects.
 *
 * Expected JSON format (one object per line, or array):
 *   {"line":1,"column":5,"severity":"error","code":"BSL001","message":"..."}
 */
function parseDiagnostics(
  output: string,
  documentUri: vscode.Uri
): vscode.Diagnostic[] {
  const diagnostics: vscode.Diagnostic[] = [];

  if (!output.trim()) {
    return diagnostics;
  }

  // Try JSON array first, then newline-delimited JSON objects
  let entries: BslDiagnosticLine[] = [];
  const trimmed = output.trim();

  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      entries = parsed as BslDiagnosticLine[];
    } else if (typeof parsed === "object" && parsed !== null) {
      entries = [parsed as BslDiagnosticLine];
    }
  } catch {
    // Fall back to newline-delimited JSON
    for (const rawLine of trimmed.split("\n")) {
      const stripped = rawLine.trim();
      if (!stripped) {
        continue;
      }
      try {
        const entry = JSON.parse(stripped) as BslDiagnosticLine;
        entries.push(entry);
      } catch {
        // Skip non-JSON lines (e.g. summary footer lines)
      }
    }
  }

  for (const entry of entries) {
    const lineIndex = Math.max(0, (entry.line ?? 1) - 1);
    const columnIndex = Math.max(0, (entry.column ?? 1) - 1);
    const range = new vscode.Range(lineIndex, columnIndex, lineIndex, columnIndex + 1);

    const severity = mapSeverity(entry.severity);
    const diagnostic = new vscode.Diagnostic(range, entry.message ?? "Unknown issue", severity);
    diagnostic.source = DIAGNOSTICS_SOURCE;
    diagnostic.code = entry.code;

    diagnostics.push(diagnostic);
  }

  return diagnostics;
}

function mapSeverity(severity: string | undefined): vscode.DiagnosticSeverity {
  switch (severity) {
    case "error":
      return vscode.DiagnosticSeverity.Error;
    case "warning":
      return vscode.DiagnosticSeverity.Warning;
    case "info":
      return vscode.DiagnosticSeverity.Information;
    default:
      return vscode.DiagnosticSeverity.Warning;
  }
}

// ── Status bar ────────────────────────────────────────────────────────────────

function createStatusBarItem(): vscode.StatusBarItem {
  const item = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    STATUS_BAR_PRIORITY
  );
  item.command = "bsl.validate";
  item.tooltip = "BSL: Click to validate current file";
  return item;
}

function updateStatusBar(
  statusBarItem: vscode.StatusBarItem,
  state: "ok" | "error" | "warning" | "running" | "hidden"
): void {
  switch (state) {
    case "ok":
      statusBarItem.text = "$(check) BSL";
      statusBarItem.backgroundColor = undefined;
      statusBarItem.show();
      break;
    case "error":
      statusBarItem.text = "$(error) BSL";
      statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.errorBackground"
      );
      statusBarItem.show();
      break;
    case "warning":
      statusBarItem.text = "$(warning) BSL";
      statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground"
      );
      statusBarItem.show();
      break;
    case "running":
      statusBarItem.text = "$(sync~spin) BSL";
      statusBarItem.backgroundColor = undefined;
      statusBarItem.show();
      break;
    case "hidden":
      statusBarItem.hide();
      break;
  }
}

// ── Core operations ───────────────────────────────────────────────────────────

async function validateDocument(
  document: vscode.TextDocument,
  diagnosticCollection: vscode.DiagnosticCollection,
  statusBarItem: vscode.StatusBarItem
): Promise<void> {
  if (document.languageId !== BSL_LANGUAGE_ID) {
    return;
  }

  updateStatusBar(statusBarItem, "running");

  try {
    const result = await runBslCommand("validate", document.uri.fsPath, [
      "--output",
      "json",
    ]);

    const output = result.stdout || result.stderr;
    const newDiagnostics = parseDiagnostics(output, document.uri);
    diagnosticCollection.set(document.uri, newDiagnostics);

    const hasErrors = newDiagnostics.some(
      (d) => d.severity === vscode.DiagnosticSeverity.Error
    );
    const hasWarnings = newDiagnostics.some(
      (d) => d.severity === vscode.DiagnosticSeverity.Warning
    );

    if (hasErrors) {
      updateStatusBar(statusBarItem, "error");
    } else if (hasWarnings) {
      updateStatusBar(statusBarItem, "warning");
    } else {
      updateStatusBar(statusBarItem, "ok");
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showErrorMessage(`BSL Validate: ${message}`);
    updateStatusBar(statusBarItem, "hidden");
  }
}

async function lintDocument(
  document: vscode.TextDocument,
  lintDiagnosticCollection: vscode.DiagnosticCollection
): Promise<void> {
  if (document.languageId !== BSL_LANGUAGE_ID) {
    return;
  }

  try {
    const result = await runBslCommand("lint", document.uri.fsPath, [
      "--output",
      "json",
    ]);

    const output = result.stdout || result.stderr;
    const newDiagnostics = parseDiagnostics(output, document.uri);
    lintDiagnosticCollection.set(document.uri, newDiagnostics);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showWarningMessage(`BSL Lint: ${message}`);
  }
}

async function formatDocument(
  document: vscode.TextDocument
): Promise<vscode.TextEdit[]> {
  if (document.languageId !== BSL_LANGUAGE_ID) {
    return [];
  }

  try {
    const result = await runBslCommand("format", document.uri.fsPath, [
      "--stdout",
    ]);

    if (result.exitCode !== 0 || !result.stdout) {
      return [];
    }

    const fullRange = new vscode.Range(
      document.positionAt(0),
      document.positionAt(document.getText().length)
    );

    return [vscode.TextEdit.replace(fullRange, result.stdout)];
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showErrorMessage(`BSL Format: ${message}`);
    return [];
  }
}

// ── Extension activation ──────────────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext): void {
  const validationDiagnostics = vscode.languages.createDiagnosticCollection(
    `${DIAGNOSTICS_SOURCE}-validate`
  );
  const lintDiagnostics = vscode.languages.createDiagnosticCollection(
    `${DIAGNOSTICS_SOURCE}-lint`
  );

  context.subscriptions.push(validationDiagnostics, lintDiagnostics);

  const statusBarItem = createStatusBarItem();
  context.subscriptions.push(statusBarItem);

  // Show status bar when a BSL file is active
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && editor.document.languageId === BSL_LANGUAGE_ID) {
        updateStatusBar(statusBarItem, "ok");
      } else {
        updateStatusBar(statusBarItem, "hidden");
      }
    })
  );

  // On-save: validate and/or lint and/or format
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      if (document.languageId !== BSL_LANGUAGE_ID) {
        return;
      }

      const validatePromise = isValidateOnSaveEnabled()
        ? validateDocument(document, validationDiagnostics, statusBarItem)
        : Promise.resolve();

      const lintPromise = isLintOnSaveEnabled()
        ? lintDocument(document, lintDiagnostics)
        : Promise.resolve();

      await Promise.all([validatePromise, lintPromise]);
    })
  );

  // Clear diagnostics when a BSL document is closed
  context.subscriptions.push(
    vscode.workspace.onDidCloseTextDocument((document) => {
      validationDiagnostics.delete(document.uri);
      lintDiagnostics.delete(document.uri);
    })
  );

  // ── Command: bsl.validate ──────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("bsl.validate", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showInformationMessage("BSL: No active editor.");
        return;
      }
      if (editor.document.languageId !== BSL_LANGUAGE_ID) {
        vscode.window.showInformationMessage(
          "BSL: Active file is not a .bsl file."
        );
        return;
      }
      await validateDocument(editor.document, validationDiagnostics, statusBarItem);
      const count = validationDiagnostics.get(editor.document.uri)?.length ?? 0;
      if (count === 0) {
        vscode.window.showInformationMessage("BSL: Validation passed — no issues found.");
      }
    })
  );

  // ── Command: bsl.format ───────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("bsl.format", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showInformationMessage("BSL: No active editor.");
        return;
      }
      if (editor.document.languageId !== BSL_LANGUAGE_ID) {
        vscode.window.showInformationMessage(
          "BSL: Active file is not a .bsl file."
        );
        return;
      }
      const edits = await formatDocument(editor.document);
      if (edits.length === 0) {
        vscode.window.showInformationMessage("BSL: No formatting changes.");
        return;
      }
      const workspaceEdit = new vscode.WorkspaceEdit();
      workspaceEdit.set(editor.document.uri, edits);
      await vscode.workspace.applyEdit(workspaceEdit);
      vscode.window.showInformationMessage("BSL: File formatted.");
    })
  );

  // ── Command: bsl.lint ────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("bsl.lint", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showInformationMessage("BSL: No active editor.");
        return;
      }
      if (editor.document.languageId !== BSL_LANGUAGE_ID) {
        vscode.window.showInformationMessage(
          "BSL: Active file is not a .bsl file."
        );
        return;
      }
      await lintDocument(editor.document, lintDiagnostics);
      const count = lintDiagnostics.get(editor.document.uri)?.length ?? 0;
      if (count === 0) {
        vscode.window.showInformationMessage("BSL: Lint passed — no issues found.");
      }
    })
  );

  // Register as a formatting provider (triggered by Format Document command / editor.formatOnSave)
  context.subscriptions.push(
    vscode.languages.registerDocumentFormattingEditProvider(BSL_LANGUAGE_ID, {
      provideDocumentFormattingEdits(
        document: vscode.TextDocument
      ): Promise<vscode.TextEdit[]> {
        return formatDocument(document);
      },
    })
  );

  // Validate the currently open BSL file on activation
  if (
    vscode.window.activeTextEditor &&
    vscode.window.activeTextEditor.document.languageId === BSL_LANGUAGE_ID
  ) {
    void validateDocument(
      vscode.window.activeTextEditor.document,
      validationDiagnostics,
      statusBarItem
    );
  }
}

export function deactivate(): void {
  // Diagnostic collections and status bar are disposed via context.subscriptions
}
