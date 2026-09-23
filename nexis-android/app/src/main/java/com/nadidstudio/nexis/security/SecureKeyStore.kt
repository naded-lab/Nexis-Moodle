package com.nadidstudio.nexis.security

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.nadidstudio.nexis.models.ApiKeyEntry
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Stores every provider's API key(s) using EncryptedSharedPreferences
 * (backed by the Android Keystore) — never plain text, per the confirmed
 * storage decision. Supports several keys per provider for the multi-key
 * failover design (e.g. "claude" -> [key1, key2, key3]).
 *
 * GitHub personal access tokens use the same store under providerId "github".
 */
class SecureKeyStore(context: Context) {

    // First touch of this (MasterKey generation via the Android Keystore +
    // Tink) can block for a very noticeable amount of time on some devices —
    // that cost must never land on the main thread. `warmUp()` below lets
    // callers pay it on a background thread right after process start, so by
    // the time a screen actually needs a key the value is already cached.
    private val prefs: SharedPreferences by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "nexis_secure_keys",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    /** Forces the lazy Keystore/EncryptedSharedPreferences setup now. Call this
     *  from a background dispatcher only — never from the main thread. */
    fun warmUp() {
        prefs
    }

    /** All keys currently stored for a provider, in the order they'll be tried. */
    fun getKeys(providerId: String): List<ApiKeyEntry> {
        val raw = prefs.getString(keyListPrefKey(providerId), null) ?: return emptyList()
        val array = JSONArray(raw)
        return (0 until array.length()).map { i ->
            val obj = array.getJSONObject(i)
            ApiKeyEntry(id = obj.getString("id"), keyValue = obj.getString("value"))
        }
    }

    /** Adds a new key for the given provider, appended to the end of its list. */
    fun addKey(providerId: String, keyValue: String): ApiKeyEntry {
        val entry = ApiKeyEntry(id = UUID.randomUUID().toString(), keyValue = keyValue)
        val updated = getKeys(providerId) + entry
        saveKeys(providerId, updated)
        return entry
    }

    /** Removes one key (e.g. user deletes an expired key from settings). */
    fun removeKey(providerId: String, keyId: String) {
        val updated = getKeys(providerId).filterNot { it.id == keyId }
        saveKeys(providerId, updated)
    }

    /** Whether this provider has at least one key configured at all. */
    fun hasAnyKey(providerId: String): Boolean = getKeys(providerId).isNotEmpty()

    private fun saveKeys(providerId: String, keys: List<ApiKeyEntry>) {
        val array = JSONArray()
        keys.forEach { entry ->
            array.put(
                JSONObject().apply {
                    put("id", entry.id)
                    put("value", entry.keyValue)
                }
            )
        }
        prefs.edit().putString(keyListPrefKey(providerId), array.toString()).apply()
    }

    private fun keyListPrefKey(providerId: String) = "keys_$providerId"
}
