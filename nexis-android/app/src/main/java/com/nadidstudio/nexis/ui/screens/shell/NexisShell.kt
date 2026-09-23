package com.nadidstudio.nexis.ui.screens.shell

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import com.nadidstudio.nexis.ui.screens.AssistantSheet
import com.nadidstudio.nexis.ui.screens.ChatScreen
import com.nadidstudio.nexis.ui.screens.ModelSheet
import com.nadidstudio.nexis.ui.screens.NexisDrawer
import com.nadidstudio.nexis.ui.screens.ProjectScreen
import com.nadidstudio.nexis.ui.screens.SettingsScreen
import com.nadidstudio.nexis.ui.screens.LocalModelScreen
import com.nadidstudio.nexis.ui.session.NexisSessionStore
import com.nadidstudio.nexis.ui.theme.NexisPalette
import kotlinx.coroutines.launch

/**
 * Main Nexis Model shell: Drawer + Chat/Projects/Settings as local pages.
 * The app opens directly here after the splash; there is no login flow.
 */
@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun NexisShell() {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        val drawerState = rememberDrawerState(DrawerValue.Closed)
        val scope = rememberCoroutineScope()
        var page by remember { mutableStateOf("chat") }
        var sheet by remember { mutableStateOf<String?>(null) }

        ModalNavigationDrawer(
            drawerState = drawerState,
            drawerContent = {
                NexisDrawer(
                    onClose = { scope.launch { drawerState.close() } },
                    onChat = { page = "chat"; scope.launch { drawerState.close() } },
                    onProjects = { page = "projects"; scope.launch { drawerState.close() } },
                    onSettings = { page = "settings"; scope.launch { drawerState.close() } },
                    onPlugins = {
                        // TODO: real "plugins/add-ons" install screen — not built yet.
                        scope.launch { drawerState.close() }
                    },
                    onPickAssistant = { sheet = "assistant" },
                    onPickModels = { sheet = "models" }
                )
            }
        ) {
            when (page) {
                "projects" -> ProjectScreen(
                    onBack = { page = "chat" },
                    onOpenProject = { NexisSessionStore.openProject(it); page = "chat" }
                )
                "settings" -> SettingsScreen(
                    onBack = { page = "chat" },
                    onOpenLocalModel = { page = "model" }
                )
                "model" -> LocalModelScreen(onBack = { page = "settings" })
                else -> ChatScreen(
                    onOpenDrawer = { scope.launch { drawerState.open() } },
                    onAssistant = { sheet = "assistant" }
                )
            }
        }

        if (sheet == "assistant") {
            ModalBottomSheet(
                onDismissRequest = { sheet = null },
                containerColor = MaterialTheme.colorScheme.surface,
                dragHandle = { BottomSheetDefaults.DragHandle(color = NexisPalette.LightMuted) }
            ) {
                AssistantSheet(
                    selected = NexisSessionStore.selectedRole,
                    onSelect = { NexisSessionStore.selectRole(it); sheet = null }
                )
            }
        }

        if (sheet == "models") {
            ModalBottomSheet(
                onDismissRequest = { sheet = null },
                containerColor = MaterialTheme.colorScheme.surface,
                dragHandle = { BottomSheetDefaults.DragHandle(color = NexisPalette.LightMuted) }
            ) {
                ModelSheet(role = NexisSessionStore.selectedRole)
            }
        }
    }
}
