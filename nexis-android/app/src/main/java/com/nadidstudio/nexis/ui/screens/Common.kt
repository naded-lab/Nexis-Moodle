package com.nadidstudio.nexis.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.orchestration.ModelRegistry
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.theme.NexisPalette

/** Display strings for the real [AssistantRole] enum (kept out of the enum itself on purpose). */
fun AssistantRole.title(): String = when (this) {
    AssistantRole.CODING -> "مساعد البرمجة"
    AssistantRole.CHAT -> "المساعد العام"
}

fun AssistantRole.subtitle(): String = when (this) {
    AssistantRole.CODING -> "تخطيط، بناء، تصحيح وشحن المشاريع"
    AssistantRole.CHAT -> "محادثة وأفكار ومساعدة يومية"
}

/** Display name for a provider id (falls back to the id itself for a custom-added model). */
fun providerDisplayName(providerId: String): String = when (providerId) {
    "claude" -> "Claude"
    "chatgpt" -> "ChatGPT"
    "gemini" -> "Gemini"
    else -> providerId.replaceFirstChar { it.uppercase() }
}

@Composable
fun Brand(modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier.size(28.dp).background(NexisPalette.Accent, RoundedCornerShape(9.dp)),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Outlined.AutoAwesome, null, tint = Color.White, modifier = Modifier.size(15.dp))
        }
        Spacer(Modifier.width(8.dp))
        Text("NEXIS", fontSize = 15.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp)
    }
}

@Composable
fun SectionLabel(text: String) {
    Text(
        text, color = MaterialTheme.colorScheme.onSurface.copy(alpha = .58f), fontSize = 11.sp,
        modifier = Modifier.padding(horizontal = 8.dp, vertical = 7.dp)
    )
}

/** Picks the assistant ROLE (Coding / Chat) — not the AI model. */
@Composable
fun AssistantSheet(selected: AssistantRole, onSelect: (AssistantRole) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 6.dp)) {
        Text("اختيار المساعد", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = 12.dp))
        AssistantSheetRow(AssistantRole.CODING, selected, onSelect)
        AssistantSheetRow(AssistantRole.CHAT, selected, onSelect)
        Spacer(Modifier.height(22.dp))
    }
}

@Composable
private fun AssistantSheetRow(role: AssistantRole, selected: AssistantRole, onSelect: (AssistantRole) -> Unit) {
    val active = role == selected
    Surface(onClick = { onSelect(role) }, color = if (active) NexisPalette.Accent.copy(alpha = .09f) else Color.Transparent, shape = RoundedCornerShape(15.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).background(if (active) NexisPalette.Accent else MaterialTheme.colorScheme.surfaceContainerHigh, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                Icon(if (role == AssistantRole.CODING) Icons.Outlined.Code else Icons.Outlined.ChatBubbleOutline, null, tint = if (active) Color.White else NexisPalette.Accent, modifier = Modifier.size(19.dp))
            }
            Spacer(Modifier.width(11.dp))
            Column(Modifier.weight(1f)) {
                Text(role.title(), fontSize = 13.sp, fontWeight = if (active) FontWeight.SemiBold else FontWeight.Normal)
                Text(role.subtitle(), fontSize = 10.sp, color = NexisPalette.LightSecondary)
            }
            if (active) Icon(Icons.Outlined.Check, null, tint = NexisPalette.Accent, modifier = Modifier.size(19.dp))
        }
    }
}

/**
 * Picks which AI MODEL(S) are enabled for the current assistant role's
 * fallback chain — separate from [AssistantSheet]. Same visual language.
 *
 * This is the single entry point for AI models: it now also owns key
 * management directly (tap the key icon on a row), so nothing here requires
 * leaving the drawer to open general Settings.
 */
@Composable
fun ModelSheet(role: AssistantRole) {
    var keysDialogProvider by remember { mutableStateOf<String?>(null) }

    Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 6.dp)) {
        Text("نماذج الذكاء الاصطناعي", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = 3.dp))
        Text("فعّل أو عطّل نموذجًا ضمن سلسلة ${role.title()}، وأدر مفاتيح API مباشرة", fontSize = 11.sp, color = NexisPalette.LightSecondary, modifier = Modifier.padding(bottom = 12.dp))
        ModelRegistry.allProviderIds().forEach { providerId ->
            val keyCount = NexisSessionStore.keyStoreForSettings.getKeys(providerId).size
            ModelSheetRow(
                providerId = providerId,
                keyCount = keyCount,
                enabled = NexisSessionStore.isProviderEnabled(role, providerId),
                onToggle = { enabled -> NexisSessionStore.toggleProvider(role, providerId, enabled) },
                onManageKeys = { keysDialogProvider = providerId }
            )
        }
        Spacer(Modifier.height(8.dp))
        Surface(onClick = { }, color = MaterialTheme.colorScheme.surfaceContainer, shape = RoundedCornerShape(15.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Add, null, Modifier.size(19.dp), tint = NexisPalette.Accent)
                Spacer(Modifier.width(10.dp))
                Text("إضافة نموذج مخصص", fontSize = 13.sp)
            }
        }
        Spacer(Modifier.height(22.dp))
    }

    val provider = keysDialogProvider
    if (provider != null) {
        ApiKeyDialog(providerId = provider, onDismiss = { keysDialogProvider = null })
    }
}

@Composable
private fun ModelSheetRow(
    providerId: String,
    keyCount: Int,
    enabled: Boolean,
    onToggle: (Boolean) -> Unit,
    onManageKeys: () -> Unit
) {
    Surface(onClick = { onToggle(!enabled) }, color = if (enabled) NexisPalette.Accent.copy(alpha = .09f) else Color.Transparent, shape = RoundedCornerShape(15.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).background(if (enabled) NexisPalette.Accent else MaterialTheme.colorScheme.surfaceContainerHigh, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                Icon(Icons.Outlined.AutoAwesome, null, tint = if (enabled) Color.White else NexisPalette.Accent, modifier = Modifier.size(19.dp))
            }
            Spacer(Modifier.width(11.dp))
            Column(Modifier.weight(1f)) {
                Text(providerDisplayName(providerId), fontSize = 13.sp, fontWeight = if (enabled) FontWeight.SemiBold else FontWeight.Normal)
                Text(if (keyCount > 0) "$keyCount مفتاح مضاف" else "لا يوجد مفتاح", fontSize = 10.sp, color = NexisPalette.Muted)
            }
            if (enabled) Icon(Icons.Outlined.Check, null, tint = NexisPalette.Accent, modifier = Modifier.size(19.dp).padding(end = 4.dp))
            IconButton(onClick = onManageKeys, modifier = Modifier.size(30.dp)) {
                Icon(Icons.Outlined.VpnKey, "إدارة مفاتيح ${providerDisplayName(providerId)}", tint = NexisPalette.Muted, modifier = Modifier.size(16.dp))
            }
        }
    }
}

/** Shared key-management dialog — reachable both from the AI-models picker
 *  in the drawer (see [ModelSheet]) and from the GitHub row in Settings. */
@Composable
fun ApiKeyDialog(providerId: String, onDismiss: () -> Unit) {
    var newKey by remember { mutableStateOf("") }
    var keys by remember { mutableStateOf(NexisSessionStore.keyStoreForSettings.getKeys(providerId)) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (providerId == "github") "توكن GitHub" else "مفاتيح ${providerDisplayName(providerId)}") },
        text = {
            Column {
                keys.forEach { entry ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("•••• ${entry.keyValue.takeLast(4)}", fontSize = 13.sp, modifier = Modifier.weight(1f))
                        IconButton(onClick = {
                            NexisSessionStore.keyStoreForSettings.removeKey(providerId, entry.id)
                            keys = NexisSessionStore.keyStoreForSettings.getKeys(providerId)
                        }) { Icon(Icons.Outlined.Delete, "حذف") }
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = newKey, onValueChange = { newKey = it }, label = { Text("مفتاح جديد") }, singleLine = true)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                if (newKey.isNotBlank()) {
                    NexisSessionStore.keyStoreForSettings.addKey(providerId, newKey.trim())
                    keys = NexisSessionStore.keyStoreForSettings.getKeys(providerId)
                    newKey = ""
                }
            }) { Text("إضافة") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("تم") } }
    )
}
