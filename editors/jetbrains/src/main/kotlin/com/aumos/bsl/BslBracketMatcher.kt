package com.aumos.bsl

import com.aumos.bsl.lexer.BslTokenTypes
import com.intellij.lang.BracePair
import com.intellij.lang.PairedBraceMatcher
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IElementType

/**
 * Enables bracket matching and auto-closing for BSL's three bracket kinds.
 *
 * The IDE uses this to highlight the matching bracket when the caret sits on
 * `{`, `}`, `[`, `]`, `(`, or `)`, and to auto-insert the closing bracket
 * when the user types the opening one.
 */
class BslBracketMatcher : PairedBraceMatcher {

    private val pairs = arrayOf(
        BracePair(BslTokenTypes.LBRACE,   BslTokenTypes.RBRACE,   true),
        BracePair(BslTokenTypes.LBRACKET, BslTokenTypes.RBRACKET, false),
        BracePair(BslTokenTypes.LPAREN,   BslTokenTypes.RPAREN,   false),
    )

    override fun getPairs(): Array<BracePair> = pairs

    override fun isPairedBracesAllowedBeforeType(
        lbraceType: IElementType,
        contextType: IElementType?,
    ): Boolean = true

    override fun getCodeConstructStart(
        file: PsiFile?,
        openingBraceOffset: Int,
    ): Int = openingBraceOffset
}
