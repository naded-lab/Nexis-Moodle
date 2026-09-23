package com.nadidstudio.nexis.orchestration

import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.models.AiModelAdapter
import com.nadidstudio.nexis.models.ChatGptAdapter
import com.nadidstudio.nexis.models.ClaudeAdapter
import com.nadidstudio.nexis.models.GeminiAdapter

/**
 * Every provider Nexis knows about. "Custom" providers the user adds via
 * the "+" option in settings get registered here too at runtime — see
 * [ModelRegistry.registerCustomAdapter].
 */
object ModelRegistry {

    private val adapters = mutableMapOf<String, AiModelAdapter>(
        "claude" to ClaudeAdapter(),
        "chatgpt" to ChatGptAdapter(),
        "gemini" to GeminiAdapter()
        // "kimi" / "notebooklm" / custom models plug in the same way once
        // their adapters are written — nothing else in this file changes.
    )

    fun adapterFor(providerId: String): AiModelAdapter? = adapters[providerId]

    fun allProviderIds(): List<String> = adapters.keys.toList()

    /** Lets the user's manually-added custom model join the same fallback system. */
    fun registerCustomAdapter(adapter: AiModelAdapter) {
        adapters[adapter.providerId] = adapter
    }

    /**
     * Default fallback chain per assistant role, capped at 5 providers as
     * decided. This is the starting point — the per-assistant model
     * enable/disable toggle in settings should filter/reorder this list,
     * not hardcode a different one per assistant.
     */
    fun defaultChainFor(role: AssistantRole): List<String> =
        when (role) {
            AssistantRole.CODING -> listOf("claude", "chatgpt", "gemini")
            AssistantRole.CHAT -> listOf("chatgpt", "claude", "gemini")
        }.take(5)
}
