package com.aumos.bsl.parser

import com.intellij.lang.ASTNode
import com.intellij.lang.LightPsiParser
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.psi.tree.IElementType

/**
 * Stub BSL parser.
 *
 * The IntelliJ Platform requires a [PsiParser] to build a PSI tree.  Full AST
 * construction (needed for inspections, refactoring, and structure view) is
 * planned for a future release.  This implementation wraps the entire file
 * in a single root marker so that the platform is satisfied and syntax
 * highlighting can proceed from the lexer token stream alone.
 */
class BslParser : PsiParser, LightPsiParser {

    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        parseLight(root, builder)
        return builder.treeBuilt
    }

    override fun parseLight(root: IElementType, builder: PsiBuilder) {
        val rootMarker = builder.mark()
        // Consume every token without building sub-tree structure.
        // The syntax highlighter operates on the lexer stream directly, so
        // this no-op pass is sufficient for highlighting to function.
        while (!builder.eof()) {
            builder.advanceLexer()
        }
        rootMarker.done(root)
    }
}
