package com.nadidstudio.nexis.models

import android.content.Context
import android.net.Uri

/** Keeps the user-selected GGUF model outside the APK so it can be replaced independently. */
object LocalModelManager {
    private const val PREFS = "nexis_model"
    private const val KEY_URI = "model_uri"
    const val MODEL_NAME = "Qwen2.5-0.5B-Instruct Q4_K_M"
    const val DIRECT_DOWNLOAD_URL =
        "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"

    fun save(context: Context, uri: Uri) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_URI, uri.toString()).apply()
    }

    fun uri(context: Context): Uri? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_URI, null)?.let(Uri::parse)

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(KEY_URI).apply()
    }
}
