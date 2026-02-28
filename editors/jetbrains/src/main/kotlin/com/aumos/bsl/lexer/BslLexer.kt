package com.aumos.bsl.lexer

import com.intellij.lexer.LexerBase
import com.intellij.psi.tree.IElementType

/**
 * Hand-written BSL lexer.
 *
 * The IntelliJ Platform calls [advance] repeatedly and reads [tokenType],
 * [tokenStart], and [tokenEnd] after each advance to construct the token
 * stream used by the syntax highlighter and parser.
 *
 * This lexer mirrors the token vocabulary of the Python BSL lexer
 * (bsl.grammar.tokens.KEYWORDS) without depending on it at runtime.
 */
class BslLexer : LexerBase() {

    private var buffer: CharSequence = ""
    private var bufferEnd: Int = 0
    private var tokenStart: Int = 0
    private var tokenEnd: Int = 0
    private var currentTokenType: IElementType? = null

    // ── Keyword tables (mirrors bsl.grammar.tokens.KEYWORDS) ──────────────────

    private val declarationKeywords: Set<String> = setOf(
        "agent", "behavior", "invariant",
    )

    private val modalityKeywords: Set<String> = setOf(
        "must", "must_not", "should", "may",
    )

    private val clauseKeywords: Set<String> = setOf(
        "when", "degrades_to", "delegates_to", "receives",
        "escalate_to_human", "applies_to", "all_behaviors",
        "cases", "of", "in",
    )

    private val metadataKeywords: Set<String> = setOf(
        "version", "model", "owner", "confidence",
        "latency", "cost", "audit", "severity",
    )

    private val operatorKeywords: Set<String> = setOf(
        "and", "or", "not", "before", "after", "contains",
    )

    private val boolLiterals: Set<String> = setOf("true", "false")

    private val severityKeywords: Set<String> = setOf(
        "critical", "high", "medium", "low", "none", "basic", "full_trace",
    )

    // ── LexerBase API ─────────────────────────────────────────────────────────

    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer = buffer
        this.bufferEnd = endOffset
        this.tokenStart = startOffset
        this.tokenEnd = startOffset
        this.currentTokenType = null
        advance()
    }

    override fun getState(): Int = 0  // Stateless lexer — no multi-line string/comment state needed

    override fun getTokenType(): IElementType? = currentTokenType

    override fun getTokenStart(): Int = tokenStart

    override fun getTokenEnd(): Int = tokenEnd

    override fun getBufferSequence(): CharSequence = buffer

    override fun getBufferEnd(): Int = bufferEnd

    override fun advance() {
        tokenStart = tokenEnd

        if (tokenStart >= bufferEnd) {
            currentTokenType = null
            return
        }

        val char = buffer[tokenStart]

        currentTokenType = when {
            // Whitespace
            char.isWhitespace() -> consumeWhitespace()

            // Line comment: //
            char == '/' && peek(1) == '/' -> consumeLineComment()

            // Block comment: /* ... */
            char == '/' && peek(1) == '*' -> consumeBlockComment()

            // String literal: "..."
            char == '"' -> consumeString()

            // Number literal
            char.isDigit() -> consumeNumber()

            // Identifiers and keywords (including underscore-joined multi-word keywords)
            char.isLetter() || char == '_' -> consumeIdentifierOrKeyword()

            // Two-character comparison operators
            char == '=' && peek(1) == '=' -> consumeFixed(2, BslTokenTypes.OPERATOR_COMPARISON)
            char == '!' && peek(1) == '=' -> consumeFixed(2, BslTokenTypes.OPERATOR_COMPARISON)
            char == '<' && peek(1) == '=' -> consumeFixed(2, BslTokenTypes.OPERATOR_COMPARISON)
            char == '>' && peek(1) == '=' -> consumeFixed(2, BslTokenTypes.OPERATOR_COMPARISON)

            // Single-character operators / punctuation
            char == '<' -> consumeFixed(1, BslTokenTypes.OPERATOR_COMPARISON)
            char == '>' -> consumeFixed(1, BslTokenTypes.OPERATOR_COMPARISON)
            char == '{' -> consumeFixed(1, BslTokenTypes.LBRACE)
            char == '}' -> consumeFixed(1, BslTokenTypes.RBRACE)
            char == '[' -> consumeFixed(1, BslTokenTypes.LBRACKET)
            char == ']' -> consumeFixed(1, BslTokenTypes.RBRACKET)
            char == '(' -> consumeFixed(1, BslTokenTypes.LPAREN)
            char == ')' -> consumeFixed(1, BslTokenTypes.RPAREN)
            char == ':' -> consumeFixed(1, BslTokenTypes.COLON)
            char == ',' -> consumeFixed(1, BslTokenTypes.COMMA)
            char == '.' -> consumeFixed(1, BslTokenTypes.DOT)
            char == '%' -> consumeFixed(1, BslTokenTypes.OPERATOR_PERCENT)

            // Unknown character — mark as bad so the IDE underlines it
            else -> consumeFixed(1, BslTokenTypes.BAD_CHARACTER)
        }
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    private fun peek(offset: Int): Char {
        val index = tokenStart + offset
        return if (index < bufferEnd) buffer[index] else '\u0000'
    }

    private fun consumeFixed(length: Int, type: IElementType): IElementType {
        tokenEnd = tokenStart + length
        return type
    }

    private fun consumeWhitespace(): IElementType {
        tokenEnd = tokenStart + 1
        while (tokenEnd < bufferEnd && buffer[tokenEnd].isWhitespace()) {
            tokenEnd++
        }
        return BslTokenTypes.WHITE_SPACE
    }

    private fun consumeLineComment(): IElementType {
        tokenEnd = tokenStart + 2
        while (tokenEnd < bufferEnd && buffer[tokenEnd] != '\n') {
            tokenEnd++
        }
        return BslTokenTypes.LINE_COMMENT
    }

    private fun consumeBlockComment(): IElementType {
        tokenEnd = tokenStart + 2
        while (tokenEnd < bufferEnd) {
            if (buffer[tokenEnd] == '*' && tokenEnd + 1 < bufferEnd && buffer[tokenEnd + 1] == '/') {
                tokenEnd += 2
                break
            }
            tokenEnd++
        }
        return BslTokenTypes.BLOCK_COMMENT
    }

    private fun consumeString(): IElementType {
        tokenEnd = tokenStart + 1  // skip opening quote
        while (tokenEnd < bufferEnd) {
            val ch = buffer[tokenEnd]
            tokenEnd++
            if (ch == '\\') {
                // Skip escape sequence character
                if (tokenEnd < bufferEnd) tokenEnd++
                continue
            }
            if (ch == '"') break
        }
        return BslTokenTypes.STRING_LITERAL
    }

    private fun consumeNumber(): IElementType {
        tokenEnd = tokenStart + 1
        while (tokenEnd < bufferEnd && buffer[tokenEnd].isDigit()) {
            tokenEnd++
        }
        // Optional decimal part
        if (tokenEnd < bufferEnd && buffer[tokenEnd] == '.') {
            val nextAfterDot = tokenEnd + 1
            if (nextAfterDot < bufferEnd && buffer[nextAfterDot].isDigit()) {
                tokenEnd = nextAfterDot + 1
                while (tokenEnd < bufferEnd && buffer[tokenEnd].isDigit()) {
                    tokenEnd++
                }
            }
        }
        return BslTokenTypes.NUMBER_LITERAL
    }

    private fun consumeIdentifierOrKeyword(): IElementType {
        tokenEnd = tokenStart + 1
        while (tokenEnd < bufferEnd) {
            val ch = buffer[tokenEnd]
            if (ch.isLetterOrDigit() || ch == '_') {
                tokenEnd++
            } else {
                break
            }
        }
        val word = buffer.subSequence(tokenStart, tokenEnd).toString()
        return classifyWord(word)
    }

    private fun classifyWord(word: String): IElementType = when (word) {
        in declarationKeywords -> BslTokenTypes.KEYWORD_DECLARATION
        in modalityKeywords    -> BslTokenTypes.KEYWORD_MODALITY
        in clauseKeywords      -> BslTokenTypes.KEYWORD_CLAUSE
        in metadataKeywords    -> BslTokenTypes.KEYWORD_METADATA
        in operatorKeywords    -> BslTokenTypes.KEYWORD_OPERATOR
        in boolLiterals        -> BslTokenTypes.BOOL_LITERAL
        in severityKeywords    -> BslTokenTypes.KEYWORD_SEVERITY
        else                   -> BslTokenTypes.IDENTIFIER
    }
}
