package com.nadidstudio.nexis.ui.screens

import android.content.Intent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nadidstudio.nexis.models.LocalModelManager
import com.nadidstudio.nexis.ui.theme.NexisPalette

@Composable
fun LocalModelScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    var selectedUri by remember { mutableStateOf(LocalModelManager.uri(context)) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) { }
            LocalModelManager.save(context, uri)
            selectedUri = uri
            Toast.makeText(context, "تمت إضافة النموذج", Toast.LENGTH_SHORT).show()
        }
    }

    Column(Modifier.fillMaxSize().padding(18.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Outlined.ArrowBack, "رجوع") }
            Text("النموذج المحلي", fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
        }
        Spacer(Modifier.height(18.dp))

        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            color = MaterialTheme.colorScheme.surfaceContainer
        ) {
            Column(Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.Memory, null, tint = NexisPalette.Accent, modifier = Modifier.size(26.dp))
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text("Qwen 0.5B Instruct", fontWeight = FontWeight.SemiBold)
                        Text("Q4_K_M · ملف GGUF", fontSize = 12.sp, color = NexisPalette.Muted)
                    }
                }
                Spacer(Modifier.height(16.dp))
                Text(
                    "النموذج لا يدخل داخل التطبيق. اختر الملف الذي حملته على هاتفك، وسيحتفظ Nexis Model بمكانه ويستخدمه لاحقًا.",
                    fontSize = 13.sp, lineHeight = 20.sp, color = NexisPalette.LightSecondary
                )
                Spacer(Modifier.height(16.dp))
                Button(
                    onClick = { picker.launch(arrayOf("application/octet-stream", "application/*", "*/*")) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Icon(Icons.Outlined.UploadFile, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(if (selectedUri == null) "إضافة ملف النموذج" else "تغيير ملف النموذج")
                }
                if (selectedUri != null) {
                    Spacer(Modifier.height(10.dp))
                    Text("النموذج مضاف: ${selectedUri}", fontSize = 10.sp, color = NexisPalette.Muted, maxLines = 2)
                    TextButton(onClick = { LocalModelManager.clear(context); selectedUri = null }) {
                        Text("إزالة النموذج")
                    }
                }
            }
        }

        Spacer(Modifier.height(14.dp))
        OutlinedButton(
            onClick = {
                context.startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(LocalModelManager.DIRECT_DOWNLOAD_URL)))
            },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(14.dp)
        ) {
            Icon(Icons.Outlined.Download, null, Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("تحميل Qwen Q4_K_M")
        }

        TextButton(
            onClick = {
                val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Qwen Q4_K_M", LocalModelManager.DIRECT_DOWNLOAD_URL))
                Toast.makeText(context, "تم نسخ رابط التحميل", Toast.LENGTH_SHORT).show()
            },
            modifier = Modifier.align(Alignment.CenterHorizontally)
        ) {
            Text("نسخ رابط التحميل")
        }
    }
}
