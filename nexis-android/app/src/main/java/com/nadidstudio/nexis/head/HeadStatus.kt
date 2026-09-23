package com.nadidstudio.nexis.head

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

/**
 * The "head" is explicitly NOT an AI model — it's the status/health layer
 * that (1) confirms real internet connectivity and (2) tracks each key's
 * health so the fallback orchestrator knows what to skip.
 */
enum class KeyHealth {
    UNKNOWN,        // never tried yet
    WORKING,        // last call succeeded
    QUOTA_EXCEEDED, // try again later / move to next key
    INVALID,        // bad key — never retry automatically
    SERVER_DOWN     // provider-side issue — safe to retry later
}

/** Checks whether the device actually has a working internet path right now. */
class NetworkMonitor(private val context: Context) {

    fun isOnline(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false
        val network = cm.activeNetwork ?: return false
        val capabilities = cm.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
}

/**
 * In-memory health table: (providerId, keyId) -> KeyHealth.
 * Updated by the orchestrator after every real call outcome.
 *
 * Kept in memory only for now — a future pass can persist this (e.g. to
 * survive process death) without changing the public API below.
 */
class ModelHealthTracker {

    private val table = mutableMapOf<String, KeyHealth>()

    fun healthOf(providerId: String, keyId: String): KeyHealth =
        table[tableKey(providerId, keyId)] ?: KeyHealth.UNKNOWN

    fun markWorking(providerId: String, keyId: String) {
        table[tableKey(providerId, keyId)] = KeyHealth.WORKING
    }

    fun markQuotaExceeded(providerId: String, keyId: String) {
        table[tableKey(providerId, keyId)] = KeyHealth.QUOTA_EXCEEDED
    }

    fun markInvalid(providerId: String, keyId: String) {
        table[tableKey(providerId, keyId)] = KeyHealth.INVALID
    }

    fun markServerDown(providerId: String, keyId: String) {
        table[tableKey(providerId, keyId)] = KeyHealth.SERVER_DOWN
    }

    /** A key is worth trying unless we already know it's permanently bad. */
    fun isUsable(providerId: String, keyId: String): Boolean =
        healthOf(providerId, keyId) != KeyHealth.INVALID

    private fun tableKey(providerId: String, keyId: String) = "$providerId:$keyId"
}
