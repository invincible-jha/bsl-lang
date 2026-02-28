package com.aumos.bsl

import com.intellij.openapi.fileTypes.LanguageFileType
import javax.swing.Icon

/**
 * Associates the `.bsl` file extension with the BSL language and provides
 * the metadata the IDE needs to display BSL files correctly in the file tree,
 * editor tabs, and "Open With" menus.
 */
class BslFileType private constructor() : LanguageFileType(BslLanguage) {

    companion object {
        /** Singleton instance registered in plugin.xml via [fieldName]. */
        @JvmField
        val INSTANCE = BslFileType()
    }

    override fun getName(): String = "BSL File"

    override fun getDescription(): String = "Behavioral Specification Language file"

    override fun getDefaultExtension(): String = "bsl"

    override fun getIcon(): Icon = BslIcons.FILE
}
