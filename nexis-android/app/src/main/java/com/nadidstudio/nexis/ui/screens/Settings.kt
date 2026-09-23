package com.nadidstudio.nexis.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.theme.AppearanceMode
import com.nadidstudio.nexis.ui.theme.NexisAppearance
import com.nadidstudio.nexis.ui.theme.NexisPalette

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun SettingsScreen(onBack: () -> Unit, onOpenLocalModel: () -> Unit) {
    var keysDialogProvider by remember { mutableStateOf<String?>(null) }
    var showAccountSheet by remember { mutableStateOf(false) }
    var showAppearanceDialog by remember { mutableStateOf(false) }

    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 14.dp), contentPadding = PaddingValues(top = 10.dp, bottom = 28.dp)) {
        item { Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { IconButton(onClick = onBack) { Icon(Icons.Outlined.Close, "إغلاق") }; Text("الإعدادات", fontSize = 20.sp, fontWeight = FontWeight.SemiBold) }; Spacer(Modifier.height(10.dp)) }

        // "تعديل الملف الشخصي" now lives inside "الحساب الشخصي" (see the sheet
        // below) instead of sitting as its own row here.
        item { SectionTitle("الحساب") }
        item { SettingGroup { SettingRow("الحساب الشخصي", "الاسم والصورة والبيانات", Icons.Outlined.Person, onClick = { showAccountSheet = true }); SettingRow("التخزين", "إدارة البيانات والمحادثات", Icons.Outlined.Storage) } }

        // "نماذج الذكاء الاصطناعي ومفاتيح API" لم تعد بطاقة هنا إطلاقًا — انتقلت
        // إلى زر رئيسي أعلى القائمة الجانبية (NexisDrawer -> ModelSheet)، وأصبحت
        // إدارة المفاتيح تتم من هناك مباشرة دون الحاجة للدخول إلى الإعدادات.

        item { SectionTitle("التطبيق") }
        item { SettingGroup { SettingRow("المظهر", NexisAppearance.mode.label, Icons.Outlined.Brightness6, onClick = { showAppearanceDialog = true }); SettingRow("اللغة", "العربية", Icons.Outlined.Language); SettingRow("الإشعارات", "تنبيهات التطبيق", Icons.Outlined.Notifications) } }

        item { SectionTitle("التطوير") }
        item { SettingGroup { SettingRow("النموذج المحلي", "Qwen 0.5B · إضافة أو تغيير ملف GGUF", Icons.Outlined.Memory, onClick = onOpenLocalModel); SettingRow("Termux", "ربط بيئة التطوير لاحقًا", Icons.Outlined.Terminal); SettingRow("GitHub", if (NexisSessionStore.keyStoreForSettings.hasAnyKey("github")) "متصل" else "غير متصل", Icons.Outlined.Code, onClick = { keysDialogProvider = "github" }) } }

        item { Spacer(Modifier.height(18.dp)); Text("Nexis Model 0.1.0", color = NexisPalette.Muted, fontSize = 11.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center) }
    }

    if (showAccountSheet) {
        ModalBottomSheet(
            onDismissRequest = { showAccountSheet = false },
            containerColor = MaterialTheme.colorScheme.surface,
            dragHandle = { BottomSheetDefaults.DragHandle(color = NexisPalette.LightMuted) }
        ) {
            Column(Modifier.padding(horizontal = 18.dp).padding(bottom = 18.dp)) {
                Text("الحساب الشخصي", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = 12.dp))
                SettingGroup {
                    // TODO: real profile-edit screen — not built yet.
                    SettingRow("تعديل الملف الشخصي", "الاسم، الصورة، البيانات الأساسية", Icons.Outlined.Edit, onClick = { showAccountSheet = false })
                }
            }
        }
    }

    if (showAppearanceDialog) {
        AlertDialog(
            onDismissRequest = { showAppearanceDialog = false },
            title = { Text("المظهر") },
            text = {
                Column {
                    AppearanceMode.entries.forEach { mode ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .selectable(selected = NexisAppearance.mode == mode, onClick = { NexisAppearance.mode = mode; showAppearanceDialog = false })
                                .padding(vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(selected = NexisAppearance.mode == mode, onClick = { NexisAppearance.mode = mode; showAppearanceDialog = false })
                            Spacer(Modifier.width(8.dp))
                            Text(mode.label, fontSize = 14.sp)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showAppearanceDialog = false }) { Text("تم") } }
        )
    }

    val provider = keysDialogProvider
    if (provider != null) {
        ApiKeyDialog(providerId = provider, onDismiss = { keysDialogProvider = null })
    }
}

@Composable private fun SectionTitle(text: String) { Text(text, fontSize = 11.sp, color = NexisPalette.Muted, modifier = Modifier.padding(start = 8.dp, top = 12.dp, bottom = 7.dp)) }
@Composable private fun SettingGroup(content: @Composable ColumnScope.() -> Unit) { Surface(color = MaterialTheme.colorScheme.surfaceContainer, shape = RoundedCornerShape(16.dp)) { Column(Modifier.fillMaxWidth(), content = content) } }
@Composable private fun SettingRow(title: String, sub: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onClick: (() -> Unit)? = null) {
    var modifier = Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 12.dp) as Modifier
    if (onClick != null) modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 13.dp, vertical = 12.dp)
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, Modifier.size(18.dp), tint = NexisPalette.Muted)
        Spacer(Modifier.width(13.dp))
        Column(Modifier.weight(1f)) { Text(title, fontSize = 13.sp); Text(sub, fontSize = 10.sp, color = NexisPalette.Muted, maxLines = 1) }
    }
}
