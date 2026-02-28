package com.aumos.bsl

import com.intellij.lang.Language

/**
 * Singleton that registers BSL as an IntelliJ Platform language.
 *
 * All BSL-related extension points (file type, parser, highlighter …) reference
 * this object so the platform can wire them together by language ID.
 */
object BslLanguage : Language("BSL") {

    /** Human-readable display name shown in the IDE language selector. */
    override fun getDisplayName(): String = "Behavioral Specification Language (BSL)"
}
