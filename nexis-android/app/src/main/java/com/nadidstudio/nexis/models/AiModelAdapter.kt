package com.nadidstudio.nexis.models

import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull

/**
 * One unified error type every provider adapter must translate its own
 * errors into. This is what the fallback logic (key-switch / model-switch)
 * decides on — see the model-fallback-orchestration design.
 */
sealed class AiCallResult {
    data class Success(val text: String) : AiCallResult()

    /** Quota/rate limit hit on this key — try the next key for the same model. */
    data class QuotaExceeded(val raw: String? = null) : AiCallResult()

    /** Network blip / server hiccup — safe to retry the same key shortly. */
    data class TransientError(val raw: String? = null) : AiCallResult()

    /** Bad key, malformed request, etc — do not retry this key again. */
    data class PermanentError(val raw: String? = null) : AiCallResult()
}

/**
 * One API key belonging to a provider (a provider/model can have several,
 * per the multi-key failover design).
 */
data class ApiKeyEntry(
    val id: String,
    val keyValue: String // read from EncryptedSharedPreferences, never hardcoded
)

/**
 * Every AI provider (Claude, GPT, Gemini, KiMi, NotebookLM, a manually
 * added custom one, ...) implements this same interface so the
 * orchestration layer never needs to know provider-specific details.
 */
interface AiModelAdapter {
    val providerId: String
    val displayName: String

    /**
     * Send a single request using the given key. Implementations translate
     * their own SDK/HTTP error into one of the AiCallResult cases above —
     * this is the one place provider-specific error handling is allowed to live.
     */
    suspend fun send(prompt: String, key: ApiKeyEntry): AiCallResult
}

/**
 * Claude adapter — calls the real Anthropic Messages API.
 */
class ClaudeAdapter(
    private val client: okhttp3.OkHttpClient = okhttp3.OkHttpClient()
) : AiModelAdapter {
    override val providerId = "claude"
    override val displayName = "Claude"

    override suspend fun send(prompt: String, key: ApiKeyEntry): AiCallResult =
        withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val body = org.json.JSONObject().apply {
                    put("model", "claude-sonnet-4-5")
                    put("max_tokens", 1024)
                    put(
                        "messages",
                        org.json.JSONArray().put(
                            org.json.JSONObject().apply {
                                put("role", "user")
                                put("content", prompt)
                            }
                        )
                    )
                }

                val request = okhttp3.Request.Builder()
                    .url("https://api.anthropic.com/v1/messages")
                    .addHeader("x-api-key", key.keyValue)
                    .addHeader("anthropic-version", "2023-06-01")
                    .addHeader("content-type", "application/json")
                    .post(
                        okhttp3.RequestBody.create(
                            "application/json; charset=utf-8".toMediaTypeOrNull(),
                            body.toString()
                        )
                    )
                    .build()

                client.newCall(request).execute().use { response ->
                    val raw = response.body?.string()
                    parseHttpOutcome(response.code, raw) { json ->
                        json.getJSONArray("content").getJSONObject(0).getString("text")
                    }
                }
            } catch (e: java.io.IOException) {
                AiCallResult.TransientError(e.message)
            } catch (e: Exception) {
                AiCallResult.PermanentError(e.message)
            }
        }
}

/**
 * ChatGPT adapter — calls the OpenAI chat completions API. Same
 * key/fallback contract as every other adapter.
 */
class ChatGptAdapter(
    private val client: okhttp3.OkHttpClient = okhttp3.OkHttpClient()
) : AiModelAdapter {
    override val providerId = "chatgpt"
    override val displayName = "ChatGPT"

    override suspend fun send(prompt: String, key: ApiKeyEntry): AiCallResult =
        withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val body = org.json.JSONObject().apply {
                    put("model", "gpt-4o-mini")
                    put(
                        "messages",
                        org.json.JSONArray().put(
                            org.json.JSONObject().apply {
                                put("role", "user")
                                put("content", prompt)
                            }
                        )
                    )
                }

                val request = okhttp3.Request.Builder()
                    .url("https://api.openai.com/v1/chat/completions")
                    .addHeader("Authorization", "Bearer ${key.keyValue}")
                    .addHeader("content-type", "application/json")
                    .post(
                        okhttp3.RequestBody.create(
                            "application/json; charset=utf-8".toMediaTypeOrNull(),
                            body.toString()
                        )
                    )
                    .build()

                client.newCall(request).execute().use { response ->
                    val raw = response.body?.string()
                    parseHttpOutcome(response.code, raw) { json ->
                        json.getJSONArray("choices")
                            .getJSONObject(0)
                            .getJSONObject("message")
                            .getString("content")
                    }
                }
            } catch (e: java.io.IOException) {
                AiCallResult.TransientError(e.message)
            } catch (e: Exception) {
                AiCallResult.PermanentError(e.message)
            }
        }
}

/**
 * Gemini adapter — calls the Google AI Studio generateContent endpoint
 * (the free-tier API the user is starting with, per current plan).
 */
class GeminiAdapter(
    private val client: okhttp3.OkHttpClient = okhttp3.OkHttpClient()
) : AiModelAdapter {
    override val providerId = "gemini"
    override val displayName = "Gemini"

    override suspend fun send(prompt: String, key: ApiKeyEntry): AiCallResult =
        withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val body = org.json.JSONObject().apply {
                    put(
                        "contents",
                        org.json.JSONArray().put(
                            org.json.JSONObject().apply {
                                put(
                                    "parts",
                                    org.json.JSONArray().put(
                                        org.json.JSONObject().apply { put("text", prompt) }
                                    )
                                )
                            }
                        )
                    )
                }

                val url = "https://generativelanguage.googleapis.com/v1beta/models/" +
                    "gemini-1.5-flash:generateContent?key=${key.keyValue}"

                val request = okhttp3.Request.Builder()
                    .url(url)
                    .addHeader("content-type", "application/json")
                    .post(
                        okhttp3.RequestBody.create(
                            "application/json; charset=utf-8".toMediaTypeOrNull(),
                            body.toString()
                        )
                    )
                    .build()

                client.newCall(request).execute().use { response ->
                    val raw = response.body?.string()
                    parseHttpOutcome(response.code, raw) { json ->
                        json.getJSONArray("candidates")
                            .getJSONObject(0)
                            .getJSONObject("content")
                            .getJSONArray("parts")
                            .getJSONObject(0)
                            .getString("text")
                    }
                }
            } catch (e: java.io.IOException) {
                AiCallResult.TransientError(e.message)
            } catch (e: Exception) {
                AiCallResult.PermanentError(e.message)
            }
        }
}

/**
 * Shared HTTP-status -> AiCallResult mapping so every adapter treats
 * quota/auth/server errors the same way for the fallback logic upstream.
 * [extractText] pulls the actual reply text out of that provider's own
 * response shape once we know the call succeeded.
 */
private inline fun parseHttpOutcome(
    code: Int,
    raw: String?,
    extractText: (org.json.JSONObject) -> String
): AiCallResult {
    return when {
        code == 200 && raw != null -> {
            try {
                AiCallResult.Success(extractText(org.json.JSONObject(raw)))
            } catch (e: Exception) {
                AiCallResult.PermanentError("Unexpected response shape: ${e.message}")
            }
        }
        code == 401 || code == 403 -> AiCallResult.PermanentError("Invalid/unauthorized key (HTTP $code)")
        code == 429 -> AiCallResult.QuotaExceeded(raw)
        code in 500..599 -> AiCallResult.TransientError(raw)
        else -> AiCallResult.PermanentError(raw ?: "HTTP $code")
    }
}
