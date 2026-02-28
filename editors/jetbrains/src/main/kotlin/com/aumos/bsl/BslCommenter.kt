package com.aumos.bsl

import com.intellij.lang.CodeDocumentationAwareCommenter
import com.intellij.psi.PsiComment
import com.intellij.psi.tree.IElementType
import com.aumos.bsl.lexer.BslTokenTypes

/**
 * Teaches the IDE how to toggle line and block comments in BSL files.
 *
 * With this registered:
 * - Ctrl+/ (or Cmd+/) toggles `//` line comments.
 * - Ctrl+Shift+/ wraps the selection in `/* ... */`.
 */
class BslCommenter : CodeDocumentationAwareCommenter {

    override fun getLineCommentPrefix(): String = "//"

    override fun getBlockCommentPrefix(): String = "/*"

    override fun getBlockCommentSuffix(): String = "*/"

    override fun getCommentedBlockCommentPrefix(): String? = null

    override fun getCommentedBlockCommentSuffix(): String? = null

    override fun getLineCommentTokenType(): IElementType = BslTokenTypes.LINE_COMMENT

    override fun getBlockCommentTokenType(): IElementType = BslTokenTypes.BLOCK_COMMENT

    // Documentation comment support — not applicable for BSL
    override fun getDocumentationCommentTokenType(): IElementType? = null

    override fun getDocumentationCommentPrefix(): String? = null

    override fun getDocumentationCommentLinePrefix(): String? = null

    override fun getDocumentationCommentSuffix(): String? = null

    override fun isDocumentationComment(element: PsiComment?): Boolean = false
}
