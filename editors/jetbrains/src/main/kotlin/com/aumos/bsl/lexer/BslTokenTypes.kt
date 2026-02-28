package com.aumos.bsl.lexer

import com.aumos.bsl.BslLanguage
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.TokenSet

/**
 * Token element types for the BSL lexer.
 *
 * Each constant corresponds to one token category from the BSL grammar defined
 * in [bsl.grammar.tokens.TokenType].  The IntelliJ Platform uses these objects
 * to associate token ranges with syntax-highlight attributes.
 */
class BslTokenType(debugName: String) : IElementType(debugName, BslLanguage)

object BslTokenTypes {

    // ── Declaration keywords ───────────────────────────────────────────────────
    /** agent  behavior  invariant */
    @JvmField val KEYWORD_DECLARATION: IElementType = BslTokenType("KEYWORD_DECLARATION")

    // ── Modality keywords ──────────────────────────────────────────────────────
    /** must  must_not  should  may */
    @JvmField val KEYWORD_MODALITY: IElementType = BslTokenType("KEYWORD_MODALITY")

    // ── Clause / structural keywords ──────────────────────────────────────────
    /** when  degrades_to  delegates_to  receives  escalate_to_human
     *  applies_to  all_behaviors  cases  of  in */
    @JvmField val KEYWORD_CLAUSE: IElementType = BslTokenType("KEYWORD_CLAUSE")

    // ── Metadata field keywords ────────────────────────────────────────────────
    /** version  model  owner  confidence  latency  cost  audit  severity */
    @JvmField val KEYWORD_METADATA: IElementType = BslTokenType("KEYWORD_METADATA")

    // ── Logical / temporal operator keywords ──────────────────────────────────
    /** and  or  not  before  after  contains */
    @JvmField val KEYWORD_OPERATOR: IElementType = BslTokenType("KEYWORD_OPERATOR")

    // ── Severity / constant keywords ──────────────────────────────────────────
    /** critical  high  medium  low  none  basic  full_trace */
    @JvmField val KEYWORD_SEVERITY: IElementType = BslTokenType("KEYWORD_SEVERITY")

    // ── Identifiers ───────────────────────────────────────────────────────────
    @JvmField val IDENTIFIER: IElementType = BslTokenType("IDENTIFIER")

    // ── Literals ──────────────────────────────────────────────────────────────
    @JvmField val STRING_LITERAL: IElementType = BslTokenType("STRING_LITERAL")
    @JvmField val NUMBER_LITERAL: IElementType = BslTokenType("NUMBER_LITERAL")
    @JvmField val BOOL_LITERAL: IElementType = BslTokenType("BOOL_LITERAL")

    // ── Operators ─────────────────────────────────────────────────────────────
    /** ==  !=  <  >  <=  >= */
    @JvmField val OPERATOR_COMPARISON: IElementType = BslTokenType("OPERATOR_COMPARISON")
    /** % */
    @JvmField val OPERATOR_PERCENT: IElementType = BslTokenType("OPERATOR_PERCENT")

    // ── Punctuation ───────────────────────────────────────────────────────────
    @JvmField val LBRACE: IElementType = BslTokenType("LBRACE")
    @JvmField val RBRACE: IElementType = BslTokenType("RBRACE")
    @JvmField val LBRACKET: IElementType = BslTokenType("LBRACKET")
    @JvmField val RBRACKET: IElementType = BslTokenType("RBRACKET")
    @JvmField val LPAREN: IElementType = BslTokenType("LPAREN")
    @JvmField val RPAREN: IElementType = BslTokenType("RPAREN")
    @JvmField val COLON: IElementType = BslTokenType("COLON")
    @JvmField val COMMA: IElementType = BslTokenType("COMMA")
    @JvmField val DOT: IElementType = BslTokenType("DOT")

    // ── Comments ──────────────────────────────────────────────────────────────
    @JvmField val LINE_COMMENT: IElementType = BslTokenType("LINE_COMMENT")
    @JvmField val BLOCK_COMMENT: IElementType = BslTokenType("BLOCK_COMMENT")

    // ── Whitespace ────────────────────────────────────────────────────────────
    @JvmField val WHITE_SPACE: IElementType = BslTokenType("WHITE_SPACE")

    // ── Bad character ─────────────────────────────────────────────────────────
    @JvmField val BAD_CHARACTER: IElementType = BslTokenType("BAD_CHARACTER")

    // ── Token sets used by the parser definition ──────────────────────────────

    /** All tokens the platform treats as whitespace (skipped by the AST builder). */
    @JvmField val WHITESPACE_SET: TokenSet = TokenSet.create(WHITE_SPACE)

    /** All comment token types. */
    @JvmField val COMMENT_SET: TokenSet = TokenSet.create(LINE_COMMENT, BLOCK_COMMENT)

    /** All string literal token types. */
    @JvmField val STRING_SET: TokenSet = TokenSet.create(STRING_LITERAL)

    /** All keyword token types (used for brace-matching and commenter hints). */
    @JvmField val KEYWORD_SET: TokenSet = TokenSet.create(
        KEYWORD_DECLARATION,
        KEYWORD_MODALITY,
        KEYWORD_CLAUSE,
        KEYWORD_METADATA,
        KEYWORD_OPERATOR,
        KEYWORD_SEVERITY,
    )
}
