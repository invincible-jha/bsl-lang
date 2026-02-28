package com.aumos.bsl

import com.intellij.openapi.util.IconLoader
import javax.swing.Icon

/**
 * Central registry of BSL icons.
 *
 * Icons are loaded from `/icons/` under the resources root.  The file
 * `bsl-file.svg` (16x16) is the only required asset; it is shown in the
 * project tree, editor tabs, and the file-type settings panel.
 *
 * If the icon resource is missing the IDE falls back to a generic text-file
 * icon rather than crashing, so the plugin functions correctly even without
 * the asset during development.
 */
object BslIcons {

    /** Icon used for .bsl files in the file tree and editor tabs. */
    @JvmField
    val FILE: Icon = IconLoader.getIcon("/icons/bsl-file.svg", BslIcons::class.java)
}
