package com.aumos.bsl

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import javax.swing.Icon

/**
 * Adds a "BSL - Behavioral Specification Language" section to
 * Settings | Editor | Color Scheme so users can customize token colors.
 *
 * Each [AttributesDescriptor] maps a human-readable label to a
 * [TextAttributesKey] defined in [BslSyntaxHighlighter].
 */
class BslColorSettingsPage : ColorSettingsPage {

    companion object {
        private val DESCRIPTORS = arrayOf(
            AttributesDescriptor("Declaration keywords//agent, behavior, invariant", BslSyntaxHighlighter.KEYWORD_DECLARATION),
            AttributesDescriptor("Modality keywords//must, must_not, should, may", BslSyntaxHighlighter.KEYWORD_MODALITY),
            AttributesDescriptor("Clause keywords//when, degrades_to, delegates_to, …", BslSyntaxHighlighter.KEYWORD_CLAUSE),
            AttributesDescriptor("Metadata field keywords//version, model, owner, …", BslSyntaxHighlighter.KEYWORD_METADATA),
            AttributesDescriptor("Operator keywords//and, or, not, before, after, contains", BslSyntaxHighlighter.KEYWORD_OPERATOR),
            AttributesDescriptor("Severity constants//critical, high, medium, low, …", BslSyntaxHighlighter.KEYWORD_SEVERITY),
            AttributesDescriptor("Identifiers", BslSyntaxHighlighter.IDENTIFIER),
            AttributesDescriptor("String literals", BslSyntaxHighlighter.STRING),
            AttributesDescriptor("Number literals", BslSyntaxHighlighter.NUMBER),
            AttributesDescriptor("Boolean literals//true, false", BslSyntaxHighlighter.BOOL),
            AttributesDescriptor("Comparison operators//==, !=, <, >, <=, >=", BslSyntaxHighlighter.OPERATOR),
            AttributesDescriptor("Braces//{ }", BslSyntaxHighlighter.BRACES),
            AttributesDescriptor("Brackets//[ ]", BslSyntaxHighlighter.BRACKETS),
            AttributesDescriptor("Parentheses//( )", BslSyntaxHighlighter.PARENTHESES),
            AttributesDescriptor("Dot//.  (member access)", BslSyntaxHighlighter.DOT),
            AttributesDescriptor("Comma", BslSyntaxHighlighter.COMMA),
            AttributesDescriptor("Colon//:  (field separator)", BslSyntaxHighlighter.COLON),
            AttributesDescriptor("Line comments", BslSyntaxHighlighter.LINE_COMMENT),
            AttributesDescriptor("Block comments", BslSyntaxHighlighter.BLOCK_COMMENT),
            AttributesDescriptor("Bad characters", BslSyntaxHighlighter.BAD_CHARACTER),
        )

        /** Demo snippet rendered in the preview panel of the Color Settings page. */
        private val DEMO_TEXT = """
            // Line comment — BSL color settings preview
            /* Block comment spanning multiple lines */

            agent PaymentAgent {
              version: "1.0"
              model: "gpt-4"
              owner: "finance-team"

              behavior ProcessPayment {
                when context.amount > 1000 {
                  must_not call external_service without audit
                  must log_action "high_value_payment"
                  should verify_identity
                }
                may retry 3
              }

              invariant SpendLimit {
                applies_to: all_behaviors
                must context.total_spend <= context.budget * 100%
                severity: critical
              }

              behavior FallbackFlow {
                degrades_to SafeMode
                delegates_to HumanReview when confidence < 0.5
              }
            }
        """.trimIndent()
    }

    override fun getDisplayName(): String = "BSL - Behavioral Specification Language"

    override fun getIcon(): Icon = BslIcons.FILE

    override fun getHighlighter(): SyntaxHighlighter = BslSyntaxHighlighter()

    override fun getDemoText(): String = DEMO_TEXT

    override fun getAdditionalHighlightingTagToDescriptorMap(): Map<String, TextAttributesKey>? = null

    override fun getAttributeDescriptors(): Array<AttributesDescriptor> = DESCRIPTORS

    override fun getColorDescriptors(): Array<ColorDescriptor> = ColorDescriptor.EMPTY_ARRAY
}
