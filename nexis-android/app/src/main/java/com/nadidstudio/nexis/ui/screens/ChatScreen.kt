package com.nadidstudio.nexis.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.session.UiMessage
import com.nadidstudio.nexis.ui.theme.NexisPalette

@Composable
fun ChatScreen(onOpenDrawer: () -> Unit, onAssistant: () -> Unit) {
    var input by remember { mutableStateOf("") }
    var showTools by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val messages = NexisSessionStore.messages
    val thinking = NexisSessionStore.sending
    val error = NexisSessionStore.lastError

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            TopBar(onOpenDrawer = onOpenDrawer, onAssistant = onAssistant)
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = .6f))

            if (messages.isEmpty()) EmptyChat() else LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 22.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp)
            ) {
                items(messages) { MessageBubble(it) }
                if (thinking) item { ThinkingBubble() }
            }

            if (error != null) {
                Text(error, color = MaterialTheme.colorScheme.error, fontSize = 12.sp, modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp))
            }

            if (showTools) ToolRow(onClose = { showTools = false })
            Composer(
                value = input,
                onValueChange = { input = it },
                onTools = { showTools = !showTools },
                onSend = {
                    val text = input.trim()
                    if (text.isNotEmpty() && !thinking) {
                        NexisSessionStore.addUserMessageOptimistically(text)
                        input = ""
                        scope.launch { NexisSessionStore.send(text) }
                    }
                }
            )
        }
    }
}

// Header is a Box, not a Row, so the assistant chip can sit dead-center
// regardless of how wide the two icon buttons on either side are — that
// centering is what a Row-with-weighted-spacer can't guarantee once both
// sides are occupied. Menu stays on its established side (screen-right,
// i.e. RTL "Start"); new-chat now lives opposite it at screen-top-left
// (RTL "End"), replacing the old bottom-corner FAB.
@Composable private fun TopBar(onOpenDrawer: () -> Unit, onAssistant: () -> Unit) {
    Box(
        Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center
    ) {
        AssistChip(
            onClick = onAssistant,
            label = { Text(NexisSessionStore.selectedRole.title(), fontSize = 11.sp) },
            leadingIcon = { Icon(Icons.Outlined.AutoAwesome, null, Modifier.size(14.dp)) },
            modifier = Modifier.align(Alignment.Center)
        )
        IconButton(onClick = onOpenDrawer, modifier = Modifier.align(Alignment.CenterStart)) {
            MenuGlyph(tint = MaterialTheme.colorScheme.onSurface)
        }
        IconButton(onClick = { NexisSessionStore.newChat() }, modifier = Modifier.align(Alignment.CenterEnd)) {
            Icon(Icons.Outlined.AddComment, "محادثة جديدة", tint = MaterialTheme.colorScheme.onSurface)
        }
    }
}

// Three equal-width bars, evenly spaced — a single consistent glyph rather
// than the previous tapered/hamburger look.
@Composable private fun MenuGlyph(tint: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.size(21.dp)) {
        val strokeH = 2.2.dp.toPx()
        val corner = CornerRadius(strokeH / 2f)
        val gap = (size.height - strokeH * 3f) / 2f
        repeat(3) { i ->
            val y = i * (strokeH + gap)
            drawRoundRect(color = tint, topLeft = Offset(0f, y), size = Size(size.width, strokeH), cornerRadius = corner)
        }
    }
}

@Composable private fun EmptyChat() {
    Column(Modifier.fillMaxSize().padding(horizontal = 28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Box(Modifier.size(54.dp).background(NexisPalette.Accent.copy(alpha = .10f), RoundedCornerShape(18.dp)), contentAlignment = Alignment.Center) {
            Icon(Icons.Outlined.AutoAwesome, null, tint = NexisPalette.Accent, modifier = Modifier.size(24.dp))
        }
        Spacer(Modifier.height(16.dp))
        Text("مرحباً، كيف أقدر أساعدك؟", fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(8.dp))
        Text("اكتب سؤالًا أو فكرة، وسنرتبها ونحوّلها إلى خطوات واضحة.", color = NexisPalette.LightSecondary, fontSize = 13.sp, lineHeight = 21.sp, textAlign = TextAlign.Center)
    }
}

@Composable private fun MessageBubble(message: UiMessage) {
    val user = message.fromUser
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (user) Arrangement.Start else Arrangement.End) {
        Surface(color = if (user) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainer, contentColor = if (user) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface, shape = if (user) RoundedCornerShape(18.dp, 18.dp, 6.dp, 18.dp) else RoundedCornerShape(18.dp, 18.dp, 18.dp, 6.dp), modifier = Modifier.widthIn(max = 330.dp)) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
                Text(message.text, fontSize = 14.sp, lineHeight = 22.sp)
                if (message.time.isNotEmpty()) {
                    Spacer(Modifier.height(5.dp))
                    Text(message.time, fontSize = 10.sp, color = LocalContentColor.current.copy(alpha = .52f))
                }
            }
        }
    }
}

@Composable private fun ThinkingBubble() { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) { Surface(color = MaterialTheme.colorScheme.surfaceContainer, shape = RoundedCornerShape(18.dp, 18.dp, 18.dp, 6.dp)) { Row(Modifier.padding(horizontal = 15.dp, vertical = 13.dp), horizontalArrangement = Arrangement.spacedBy(5.dp)) { repeat(3) { Box(Modifier.size(5.dp).background(NexisPalette.Muted, RoundedCornerShape(50))) } } } } }

@Composable private fun Composer(value: String, onValueChange: (String) -> Unit, onTools: () -> Unit, onSend: () -> Unit) {
    Surface(modifier = Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 12.dp), shape = RoundedCornerShape(27.dp), color = MaterialTheme.colorScheme.surfaceContainer, border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Row(Modifier.fillMaxWidth().padding(start = 5.dp, end = 7.dp, top = 5.dp, bottom = 5.dp), verticalAlignment = Alignment.Bottom) {
            IconButton(onClick = onTools, modifier = Modifier.size(39.dp)) { Icon(Icons.Outlined.Add, "إضافة") }
            TextField(value = value, onValueChange = onValueChange, modifier = Modifier.weight(1f), placeholder = { Text("اكتب رسالتك…", color = NexisPalette.Muted) }, maxLines = 5, colors = TextFieldDefaults.colors(focusedContainerColor = Color.Transparent, unfocusedContainerColor = Color.Transparent, focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent), textStyle = LocalTextStyle.current.copy(fontSize = 14.sp))
            FilledIconButton(onClick = onSend, enabled = value.isNotBlank(), modifier = Modifier.size(39.dp)) { Icon(Icons.Outlined.ArrowUpward, "إرسال", Modifier.size(18.dp)) }
        }
    }
}

@Composable private fun ToolRow(onClose: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 6.dp)) {
        Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("إرفاق", fontSize = 12.sp, color = NexisPalette.Muted, modifier = Modifier.weight(1f))
            IconButton(onClick = onClose, modifier = Modifier.size(26.dp)) { Icon(Icons.Outlined.Close, "إغلاق", Modifier.size(15.dp)) }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            AttachTile("ملف", Icons.Outlined.AttachFile, Modifier.weight(1f))
            AttachTile("صورة", Icons.Outlined.Image, Modifier.weight(1f))
            AttachTile("كاميرا", Icons.Outlined.PhotoCamera, Modifier.weight(1f))
        }
    }
}

@Composable private fun AttachTile(label: String, icon: ImageVector, modifier: Modifier = Modifier) {
    Surface(onClick = {}, modifier = modifier, shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surfaceContainer) {
        Column(Modifier.padding(vertical = 14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.size(38.dp).background(NexisPalette.Accent.copy(alpha = .12f), RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                Icon(icon, null, tint = NexisPalette.Accent, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.height(7.dp))
            Text(label, fontSize = 11.sp)
        }
    }
}
