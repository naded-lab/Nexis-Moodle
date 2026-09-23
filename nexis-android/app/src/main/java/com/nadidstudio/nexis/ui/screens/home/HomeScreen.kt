package com.nadidstudio.nexis.ui.screens.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.ui.theme.NexisColors

/**
 * Post-login dashboard: pick which assistant to open.
 * v1 scope is exactly these two (Coding, Chat) — Study/Educational
 * assistants are a later addition, not shown here.
 *
 * Styled to match the Splash/Login identity: solid Teal top bar with a
 * white NEXIS wordmark, instead of the unstyled default Material bar.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NexisHomeScreen(
    onOpenAssistant: (AssistantRole) -> Unit,
    onOpenSettings: () -> Unit
) {
    Scaffold(
        containerColor = NexisColors.White,
        topBar = {
            TopAppBar(
                title = { Text("NEXIS", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings", tint = NexisColors.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NexisColors.Teal,
                    titleContentColor = NexisColors.White,
                    actionIconContentColor = NexisColors.White
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(NexisColors.White)
                .padding(padding)
                .padding(20.dp)
        ) {
            Text(
                text = "Choose an assistant",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = NexisColors.TextDark
            )
            Spacer(modifier = Modifier.height(16.dp))

            AssistantCard(
                title = "Coding Assistant",
                subtitle = "Your personal dev office — plan, build, fix, and ship code.",
                icon = Icons.Filled.Build,
                onClick = { onOpenAssistant(AssistantRole.CODING) }
            )
            Spacer(modifier = Modifier.height(14.dp))
            AssistantCard(
                title = "Chat Assistant",
                subtitle = "Plain, casual conversation — no coding or study framing.",
                icon = Icons.Filled.Chat,
                onClick = { onOpenAssistant(AssistantRole.CHAT) }
            )
        }
    }
}

@Composable
private fun AssistantCard(
    title: String,
    subtitle: String,
    icon: ImageVector,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = NexisColors.CardBackground)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .background(NexisColors.Teal, RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = NexisColors.White)
            }
            Spacer(modifier = Modifier.width(14.dp))
            Column {
                Text(text = title, fontWeight = FontWeight.Bold, color = NexisColors.TextDark)
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = NexisColors.TextDark
                )
            }
        }
    }
}
