package com.aumos.bsl

import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile

/**
 * Factory registered in plugin.xml under [lang.syntaxHighlighterFactory].
 *
 * The IntelliJ Platform calls [getSyntaxHighlighter] each time it opens a
 * BSL file, so a fresh [BslSyntaxHighlighter] instance is created per file.
 */
class BslSyntaxHighlighterFactory : SyntaxHighlighterFactory() {

    override fun getSyntaxHighlighter(
        project: Project?,
        virtualFile: VirtualFile?,
    ): SyntaxHighlighter = BslSyntaxHighlighter()
}
