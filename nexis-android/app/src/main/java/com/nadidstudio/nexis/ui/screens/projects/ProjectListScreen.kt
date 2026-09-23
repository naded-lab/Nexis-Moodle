package com.nadidstudio.nexis.ui.screens.projects

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.assistants.Project
import com.nadidstudio.nexis.data.InMemoryAppStore
import com.nadidstudio.nexis.ui.theme.NexisColors

/**
 * Lists the Projects for one assistant role (Coding or Chat) and lets the
 * user create a new one. Tapping a project drills into its conversations.
 *
 * Styled to match the Home/Splash/Login identity (Teal top bar + FAB).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NexisProjectListScreen(
    role: AssistantRole,
    onBack: () -> Unit,
    onOpenProject: (Project) -> Unit
) {
    val projects = InMemoryAppStore.projectsFor(role)
    var showCreateDialog by remember { mutableStateOf(false) }

    Scaffold(
        containerColor = NexisColors.White,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        if (role == AssistantRole.CODING) "Coding Projects" else "Chat Projects",
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = NexisColors.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NexisColors.Teal,
                    titleContentColor = NexisColors.White,
                    navigationIconContentColor = NexisColors.White
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showCreateDialog = true },
                containerColor = NexisColors.Teal,
                contentColor = NexisColors.White,
                elevation = FloatingActionButtonDefaults.elevation()
            ) {
                Icon(Icons.Filled.Add, contentDescription = "New project")
            }
        }
    ) { padding ->
        if (projects.isEmpty()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "No projects yet. Tap + to start one.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = NexisColors.TextDark
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(12.dp)
            ) {
                items(projects) { project ->
                    Card(
                        onClick = { onOpenProject(project) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp),
                        colors = CardDefaults.cardColors(containerColor = NexisColors.CardBackground)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(project.name, style = MaterialTheme.typography.titleSmall, color = NexisColors.TextDark)
                            Text(
                                "${project.conversations.size} conversation(s) · " +
                                    "${project.uploadedFilePaths.size} file(s)",
                                style = MaterialTheme.typography.bodySmall,
                                color = NexisColors.TextDark
                            )
                        }
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        var name by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showCreateDialog = false },
            title = { Text("New project") },
            text = {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Project name") },
                    singleLine = true
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        if (name.isNotBlank()) {
                            InMemoryAppStore.createProject(role, name.trim())
                        }
                        showCreateDialog = false
                    }
                ) { Text("Create") }
            },
            dismissButton = {
                TextButton(onClick = { showCreateDialog = false }) { Text("Cancel") }
            }
        )
    }
}
