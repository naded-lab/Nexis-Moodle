package com.nadidstudio.nexis.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.theme.NexisPalette

@Composable
fun NexisDrawer(
    onClose: () -> Unit,
    onChat: () -> Unit,
    onProjects: () -> Unit,
    onSettings: () -> Unit,
    onPlugins: () -> Unit,
    onPickAssistant: () -> Unit,
    onPickModels: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxHeight().widthIn(max = 340.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topEnd = 0.dp, bottomEnd = 0.dp)
    ) {
        Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding().padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Brand(Modifier.weight(1f))
                IconButton(onClick = onClose) { Icon(Icons.Outlined.Close, "إغلاق") }
            }
            Spacer(Modifier.height(14.dp))
            SearchRow()
            Spacer(Modifier.height(14.dp))
            // Prominent entry point for picking the AI MODEL(S) — see ModelSheet.
            // Replaces the old "اختيار المساعد" block, which was dropped from
            // the drawer (still reachable from the chat top bar chip).
            AiModelsPillButton(onClick = onPickModels)
            Spacer(Modifier.height(10.dp))
            DrawerRow("المشاريع", Icons.Outlined.FolderOpen, onProjects)
            DrawerRow("المهام المجدولة", Icons.Outlined.Schedule, onChat)
            DrawerRow("المكونات الإضافية", Icons.Outlined.Extension, onPlugins)
            SectionLabel("المحادثات")
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text("لا توجد محادثات محفوظة", color = MaterialTheme.colorScheme.onSurface.copy(alpha = .48f), fontSize = 12.sp)
            }
            SettingsPill(onClick = onSettings)
        }
    }
}

@Composable private fun SearchRow() {
    Surface(color = MaterialTheme.colorScheme.surfaceContainer, shape = RoundedCornerShape(14.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Search, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurface.copy(alpha = .6f))
            Spacer(Modifier.width(9.dp))
            Text("بحث", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = .6f))
        }
    }
}

/** Full-width pill, green-gradient, sparkles + label — the new top-of-drawer
 * entry point into the AI model picker (see ModelSheet). Fully rounded
 * corners on purpose, distinct from every other (rectangular) drawer row. */
@Composable private fun AiModelsPillButton(onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(50),
        color = Color.Transparent
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .background(
                    Brush.horizontalGradient(listOf(NexisPalette.Accent, NexisPalette.Accent2)),
                    RoundedCornerShape(50)
                )
                .padding(horizontal = 18.dp, vertical = 13.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("نماذج الذكاء الاصطناعي", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.width(8.dp))
            Icon(Icons.Outlined.AutoAwesome, null, Modifier.size(17.dp), tint = Color.White)
        }
    }
}

@Composable private fun DrawerRow(text: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onClick: () -> Unit) {
    Surface(onClick = onClick, color = Color.Transparent, shape = RoundedCornerShape(13.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 9.dp, vertical = 11.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, Modifier.size(19.dp), tint = MaterialTheme.colorScheme.onSurface.copy(alpha = .72f))
            Spacer(Modifier.width(11.dp))
            Text(text, fontSize = 13.sp, modifier = Modifier.weight(1f))
        }
    }
}

@Composable private fun SettingsPill(onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        Surface(onClick = onClick, shape = RoundedCornerShape(15.dp), color = NexisPalette.Accent, contentColor = Color.White) {
            Row(Modifier.padding(horizontal = 13.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Settings, null, Modifier.size(16.dp))
                Spacer(Modifier.width(7.dp))
                Text("الإعدادات", fontSize = 13.sp)
            }
        }
    }
}
