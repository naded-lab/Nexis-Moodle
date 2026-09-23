package com.nadidstudio.nexis.orchestration

import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.head.ModelHealthTracker
import com.nadidstudio.nexis.head.NetworkMonitor
import com.nadidstudio.nexis.models.AiCallResult
import com.nadidstudio.nexis.security.SecureKeyStore

/** What the caller (an assistant) ultimately gets back. */
sealed class OrchestratedResult {
    data class Success(val text: String, val providerId: String) : OrchestratedResult()
    data class Offline(val message: String = "No internet connection") : OrchestratedResult()

    /** Every key on every model in the chain was exhausted. */
    data class AllModelsFailed(val attempts: List<String>) : OrchestratedResult()
}

/**
 * Implements the confirmed fallback design:
 * - try each key of the current model before moving to the next model
 * - only after ALL of a model's keys are exhausted does it move to the
 *   next model in that assistant's chain (max 5 models)
 * - the "head" layer decides usability (connectivity + known-bad keys),
 *   this class just drives the loop and records outcomes back into it
 */
class FallbackOrchestrator(
    private val keyStore: SecureKeyStore,
    private val networkMonitor: NetworkMonitor,
    private val healthTracker: ModelHealthTracker
) {

    suspend fun sendWithFallback(
        prompt: String,
        role: AssistantRole,
        chain: List<String> = ModelRegistry.defaultChainFor(role)
    ): OrchestratedResult {
        if (!networkMonitor.isOnline()) {
            return OrchestratedResult.Offline()
        }

        val attemptLog = mutableListOf<String>()

        for (providerId in chain.take(5)) {
            val adapter = ModelRegistry.adapterFor(providerId) ?: continue
            val keys = keyStore.getKeys(providerId).filter {
                healthTracker.isUsable(providerId, it.id)
            }

            for (key in keys) {
                attemptLog.add("$providerId:${key.id}")

                when (val result = adapter.send(prompt, key)) {
                    is AiCallResult.Success -> {
                        healthTracker.markWorking(providerId, key.id)
                        return OrchestratedResult.Success(result.text, providerId)
                    }
                    is AiCallResult.QuotaExceeded -> {
                        healthTracker.markQuotaExceeded(providerId, key.id)
                        // fall through to the next key for this same provider
                    }
                    is AiCallResult.TransientError -> {
                        healthTracker.markServerDown(providerId, key.id)
                        // provider-side hiccup — also move on for now; a later
                        // pass can add a short retry-before-skip here
                    }
                    is AiCallResult.PermanentError -> {
                        healthTracker.markInvalid(providerId, key.id)
                        // bad key — never retried automatically, per design
                    }
                }
            }
            // all keys for this provider are exhausted -> next provider in chain
        }

        return OrchestratedResult.AllModelsFailed(attemptLog)
    }
}
