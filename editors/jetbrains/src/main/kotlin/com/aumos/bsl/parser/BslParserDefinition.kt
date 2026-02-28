package com.aumos.bsl.parser

import com.aumos.bsl.BslLanguage
import com.aumos.bsl.lexer.BslLexer
import com.aumos.bsl.lexer.BslTokenTypes
import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiParser
import com.intellij.lexer.Lexer
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet

/**
 * Minimal parser definition for BSL.
 *
 * A full parse tree (for refactoring, intentions, structure view) is a future
 * milestone.  This stub provides the required platform integration points so
 * that syntax highlighting, bracket matching, and commenter support work
 * correctly today.
 *
 * The [createParser] method returns a no-op parser that wraps the entire file
 * content in a single FILE element; the syntax highlighter drives directly
 * from the lexer token stream, so this is sufficient for highlighting.
 */
class BslParserDefinition : ParserDefinition {

    companion object {
        /** Root element type wrapping the whole BSL file in the PSI tree. */
        @JvmField
        val FILE: IFileElementType = IFileElementType(BslLanguage)
    }

    override fun createLexer(project: Project?): Lexer = BslLexer()

    override fun createParser(project: Project?): PsiParser = BslParser()

    override fun getFileNodeType(): IFileElementType = FILE

    override fun getCommentTokens(): TokenSet = BslTokenTypes.COMMENT_SET

    override fun getStringLiteralElements(): TokenSet = BslTokenTypes.STRING_SET

    override fun getWhitespaceTokens(): TokenSet = TokenSet.create(
        BslTokenTypes.WHITE_SPACE,
        TokenType.WHITE_SPACE,
    )

    override fun createElement(node: ASTNode): PsiElement =
        throw UnsupportedOperationException(
            "BslParserDefinition.createElement: full PSI tree not yet implemented. " +
                "Node: ${node.elementType}"
        )

    override fun createFile(viewProvider: FileViewProvider): PsiFile =
        BslFile(viewProvider)
}
