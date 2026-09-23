package com.nadidstudio.nexis.assistants

import com.nadidstudio.nexis.orchestration.FallbackOrchestrator
import com.nadidstudio.nexis.orchestration.OrchestratedResult

/**
 * Common behavior for every assistant: append the user's message to its
 * (isolated) conversation, run it through the fallback chain, append the
 * reply. Role-specific behavior (system prompt, tone) lives in the
 * subclasses below, not here.
 */
abstract class BaseAssistant(
    protected val role: AssistantRole,
    private val orchestrator: FallbackOrchestrator
) {
    abstract val systemPromptPrefix: String

    suspend fun sendMessage(
        conversation: Conversation,
        userText: String,
        chain: List<String>? = null
    ): OrchestratedResult {
        conversation.messages.add(ChatMessage(role = "user", text = userText))

        val fullPrompt = buildPrompt(conversation)
        val result = if (chain != null) {
            orchestrator.sendWithFallback(fullPrompt, role, chain)
        } else {
            orchestrator.sendWithFallback(fullPrompt, role)
        }

        if (result is OrchestratedResult.Success) {
            conversation.messages.add(ChatMessage(role = "assistant", text = result.text))
        }
        return result
    }

    /**
     * Very simple context join for now: system prefix + prior turns in
     * THIS conversation only (isolation is enforced by never reading from
     * any other Conversation object).
     */
    private fun buildPrompt(conversation: Conversation): String {
        val history = conversation.messages.joinToString("\n") { "${it.role}: ${it.text}" }
        return "$systemPromptPrefix\n\n$history"
    }
}

/**
 * Acts like a personal dev office: proposes, designs, writes code, and
 * (via tool-calling once that layer exists) pushes it to GitHub.
 */
class CodingAssistant(
    orchestrator: FallbackOrchestrator
) : BaseAssistant(AssistantRole.CODING, orchestrator) {
    override val systemPromptPrefix =
        "You are Nexis's coding assistant: a personal dev office. Propose, design, " +
            "write real code, and explain what you changed and why."
}

/** Plain casual conversation — no coding/study framing. */
class ChatAssistant(
    orchestrator: FallbackOrchestrator
) : BaseAssistant(AssistantRole.CHAT, orchestrator) {
    override val systemPromptPrefix =
        "You are Nexis's general chat assistant for plain, casual conversation."
}
