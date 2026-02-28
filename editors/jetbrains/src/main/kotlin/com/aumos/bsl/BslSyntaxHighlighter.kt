package com.aumos.bsl

import com.aumos.bsl.lexer.BslLexer
import com.aumos.bsl.lexer.BslTokenTypes
import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.colors.TextAttributesKey.createTextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType

/**
 * Maps BSL token types to editor color attributes.
 *
 * Fallback keys reference IntelliJ's [DefaultLanguageHighlighterColors], which
 * means BSL tokens inherit a sensible appearance from the active color scheme
 * even without a custom BSL theme.
 */
class BslSyntaxHighlighter : SyntaxHighlighterBase() {

    companion object {

        // ── Public TextAttributesKeys (used by BslColorSettingsPage) ──────────

        @JvmField
        val KEYWORD_DECLARATION: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_DECLARATION",
            DefaultLanguageHighlighterColors.KEYWORD,
        )

        @JvmField
        val KEYWORD_MODALITY: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_MODALITY",
            DefaultLanguageHighlighterColors.KEYWORD,
        )

        @JvmField
        val KEYWORD_CLAUSE: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_CLAUSE",
            DefaultLanguageHighlighterColors.KEYWORD,
        )

        @JvmField
        val KEYWORD_METADATA: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_METADATA",
            DefaultLanguageHighlighterColors.INSTANCE_FIELD,
        )

        @JvmField
        val KEYWORD_OPERATOR: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_OPERATOR",
            DefaultLanguageHighlighterColors.OPERATION_SIGN,
        )

        @JvmField
        val KEYWORD_SEVERITY: TextAttributesKey = createTextAttributesKey(
            "BSL_KEYWORD_SEVERITY",
            DefaultLanguageHighlighterColors.CONSTANT,
        )

        @JvmField
        val IDENTIFIER: TextAttributesKey = createTextAttributesKey(
            "BSL_IDENTIFIER",
            DefaultLanguageHighlighterColors.IDENTIFIER,
        )

        @JvmField
        val STRING: TextAttributesKey = createTextAttributesKey(
            "BSL_STRING",
            DefaultLanguageHighlighterColors.STRING,
        )

        @JvmField
        val NUMBER: TextAttributesKey = createTextAttributesKey(
            "BSL_NUMBER",
            DefaultLanguageHighlighterColors.NUMBER,
        )

        @JvmField
        val BOOL: TextAttributesKey = createTextAttributesKey(
            "BSL_BOOL",
            DefaultLanguageHighlighterColors.KEYWORD,
        )

        @JvmField
        val OPERATOR: TextAttributesKey = createTextAttributesKey(
            "BSL_OPERATOR",
            DefaultLanguageHighlighterColors.OPERATION_SIGN,
        )

        @JvmField
        val BRACES: TextAttributesKey = createTextAttributesKey(
            "BSL_BRACES",
            DefaultLanguageHighlighterColors.BRACES,
        )

        @JvmField
        val BRACKETS: TextAttributesKey = createTextAttributesKey(
            "BSL_BRACKETS",
            DefaultLanguageHighlighterColors.BRACKETS,
        )

        @JvmField
        val PARENTHESES: TextAttributesKey = createTextAttributesKey(
            "BSL_PARENTHESES",
            DefaultLanguageHighlighterColors.PARENTHESES,
        )

        @JvmField
        val DOT: TextAttributesKey = createTextAttributesKey(
            "BSL_DOT",
            DefaultLanguageHighlighterColors.DOT,
        )

        @JvmField
        val COMMA: TextAttributesKey = createTextAttributesKey(
            "BSL_COMMA",
            DefaultLanguageHighlighterColors.COMMA,
        )

        @JvmField
        val COLON: TextAttributesKey = createTextAttributesKey(
            "BSL_COLON",
            DefaultLanguageHighlighterColors.SEMICOLON,
        )

        @JvmField
        val LINE_COMMENT: TextAttributesKey = createTextAttributesKey(
            "BSL_LINE_COMMENT",
            DefaultLanguageHighlighterColors.LINE_COMMENT,
        )

        @JvmField
        val BLOCK_COMMENT: TextAttributesKey = createTextAttributesKey(
            "BSL_BLOCK_COMMENT",
            DefaultLanguageHighlighterColors.BLOCK_COMMENT,
        )

        @JvmField
        val BAD_CHARACTER: TextAttributesKey = createTextAttributesKey(
            "BSL_BAD_CHARACTER",
            HighlighterColors.BAD_CHARACTER,
        )

        // ── Internal attribute arrays (single-element, as required by the API) ─

        private val KEYWORD_DECLARATION_KEYS = arrayOf(KEYWORD_DECLARATION)
        private val KEYWORD_MODALITY_KEYS    = arrayOf(KEYWORD_MODALITY)
        private val KEYWORD_CLAUSE_KEYS      = arrayOf(KEYWORD_CLAUSE)
        private val KEYWORD_METADATA_KEYS    = arrayOf(KEYWORD_METADATA)
        private val KEYWORD_OPERATOR_KEYS    = arrayOf(KEYWORD_OPERATOR)
        private val KEYWORD_SEVERITY_KEYS    = arrayOf(KEYWORD_SEVERITY)
        private val IDENTIFIER_KEYS          = arrayOf(IDENTIFIER)
        private val STRING_KEYS              = arrayOf(STRING)
        private val NUMBER_KEYS              = arrayOf(NUMBER)
        private val BOOL_KEYS                = arrayOf(BOOL)
        private val OPERATOR_KEYS            = arrayOf(OPERATOR)
        private val BRACES_KEYS              = arrayOf(BRACES)
        private val BRACKETS_KEYS            = arrayOf(BRACKETS)
        private val PARENTHESES_KEYS         = arrayOf(PARENTHESES)
        private val DOT_KEYS                 = arrayOf(DOT)
        private val COMMA_KEYS               = arrayOf(COMMA)
        private val COLON_KEYS               = arrayOf(COLON)
        private val LINE_COMMENT_KEYS        = arrayOf(LINE_COMMENT)
        private val BLOCK_COMMENT_KEYS       = arrayOf(BLOCK_COMMENT)
        private val BAD_CHARACTER_KEYS       = arrayOf(BAD_CHARACTER)
        private val EMPTY                    = emptyArray<TextAttributesKey>()
    }

    override fun getHighlightingLexer(): Lexer = BslLexer()

    override fun getTokenHighlights(tokenType: IElementType): Array<TextAttributesKey> =
        when (tokenType) {
            BslTokenTypes.KEYWORD_DECLARATION -> KEYWORD_DECLARATION_KEYS
            BslTokenTypes.KEYWORD_MODALITY    -> KEYWORD_MODALITY_KEYS
            BslTokenTypes.KEYWORD_CLAUSE      -> KEYWORD_CLAUSE_KEYS
            BslTokenTypes.KEYWORD_METADATA    -> KEYWORD_METADATA_KEYS
            BslTokenTypes.KEYWORD_OPERATOR    -> KEYWORD_OPERATOR_KEYS
            BslTokenTypes.KEYWORD_SEVERITY    -> KEYWORD_SEVERITY_KEYS
            BslTokenTypes.IDENTIFIER          -> IDENTIFIER_KEYS
            BslTokenTypes.STRING_LITERAL      -> STRING_KEYS
            BslTokenTypes.NUMBER_LITERAL      -> NUMBER_KEYS
            BslTokenTypes.BOOL_LITERAL        -> BOOL_KEYS
            BslTokenTypes.OPERATOR_COMPARISON -> OPERATOR_KEYS
            BslTokenTypes.OPERATOR_PERCENT    -> OPERATOR_KEYS
            BslTokenTypes.LBRACE,
            BslTokenTypes.RBRACE              -> BRACES_KEYS
            BslTokenTypes.LBRACKET,
            BslTokenTypes.RBRACKET            -> BRACKETS_KEYS
            BslTokenTypes.LPAREN,
            BslTokenTypes.RPAREN              -> PARENTHESES_KEYS
            BslTokenTypes.DOT                 -> DOT_KEYS
            BslTokenTypes.COMMA               -> COMMA_KEYS
            BslTokenTypes.COLON               -> COLON_KEYS
            BslTokenTypes.LINE_COMMENT        -> LINE_COMMENT_KEYS
            BslTokenTypes.BLOCK_COMMENT       -> BLOCK_COMMENT_KEYS
            BslTokenTypes.BAD_CHARACTER       -> BAD_CHARACTER_KEYS
            else                              -> EMPTY
        }
}
