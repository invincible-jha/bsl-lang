package com.aumos.bsl.parser

import com.aumos.bsl.BslFileType
import com.aumos.bsl.BslLanguage
import com.intellij.extapi.psi.PsiFileBase
import com.intellij.openapi.fileTypes.FileType
import com.intellij.psi.FileViewProvider

/**
 * Root PSI element for a BSL source file.
 *
 * [PsiFileBase] provides the default implementation for most [com.intellij.psi.PsiFile]
 * methods.  BSL-specific file operations (e.g., extracting the top-level agent
 * declarations for the structure view) would be added here in a future release.
 */
class BslFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, BslLanguage) {

    override fun getFileType(): FileType = BslFileType.INSTANCE

    override fun toString(): String = "BSL File"
}
