package com.nadidstudio.nexis.ui.session

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.assistants.BaseAssistant
import com.nadidstudio.nexis.assistants.ChatAssistant
import com.nadidstudio.nexis.assistants.ChatMessage
import com.nadidstudio.nexis.assistants.CodingAssistant
import com.nadidstudio.nexis.assistants.Conversation
import com.nadidstudio.nexis.assistants.Project
import com.nadidstudio.nexis.data.InMemoryAppStore
import com.nadidstudio.nexis.head.ModelHealthTracker
import com.nadidstudio.nexis.head.NetworkMonitor
import com.nadidstudio.nexis.orchestration.FallbackOrchestrator
import com.nadidstudio.nexis.orchestration.ModelRegistry
import com.nadidstudio.nexis.orchestration.OrchestratedResult
import com.nadidstudio.nexis.security.SecureKeyStore

/** UI-facing chat bubble — same shape the ChatScreen design already expects. */
data class UiMessage(val fromUser: Boolean, val text: String, val time: String)

/**
 * Real session store behind the uploaded UI design (Drawer/ChatScreen/
 * Projects/Settings). Replaces the design's original placeholder
 * `NexisStore` (fake in-memory list + fake delay). Visuals are untouched —
 * only the data layer underneath changed: every message now goes through
 * [BaseAssistant.sendMessage] -> [FallbackOrchestrator], real per-project
 * conversation isolation, and real per-provider API keys.
 */
object NexisSessionStore {

    private lateinit var keyStore: SecureKeyStore
    private lateinit var orchestrator: FallbackOrchestrator
    private lateinit var codingAssistant: CodingAssistant
    private lateinit var chatAssistant: ChatAssistant
    private var initialized = false

    /** Call once, e.g. from MainActivity.onCreate(applicationContext). Safe to call more than once. */
    fun init(context: Context) {
        if (initialized) return
        keyStore = SecureKeyStore(context.applicationContext)
        orchestrator = FallbackOrchestrator(
            keyStore = keyStore,
            networkMonitor = NetworkMonitor(context.applicationContext),
            healthTracker = ModelHealthTracker()
        )
        codingAssistant = CodingAssistant(orchestrator)
        chatAssistant = ChatAssistant(orchestrator)
        // Ensure there's always a project to land the "quick chat" in for each role.
        if (InMemoryAppStore.projectsFor(AssistantRole.CODING).isEmpty()) {
            InMemoryAppStore.createProject(AssistantRole.CODING, "محادثة سريعة")
        }
        if (InMemoryAppStore.projectsFor(AssistantRole.CHAT).isEmpty()) {
            InMemoryAppStore.createProject(AssistantRole.CHAT, "محادثة سريعة")
        }
        selectedRole = AssistantRole.CODING
        selectedProject = InMemoryAppStore.projectsFor(AssistantRole.CODING).first()
        initialized = true
    }

    /** Pre-warms the encrypted key store off the main thread right after
     *  launch, so the first screen that touches API keys (Settings, the
     *  model sheet) never blocks the UI thread on Keystore setup. Call once
     *  from a background coroutine, e.g. MainActivity.onCreate via lifecycleScope. */
    suspend fun warmUpSecureStorage() {
        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            keyStore.warmUp()
        }
    }

    var selectedRole by mutableStateOf(AssistantRole.CODING)
        private set

    var selectedProject by mutableStateOf<Project?>(null)
        private set

    private var currentConversation: Conversation? = null

    var messages by mutableStateOf<List<UiMessage>>(emptyList())
        private set

    var sending by mutableStateOf(false)
        private set

    var lastError by mutableStateOf<String?>(null)
        private set

    val keyStoreForSettings: SecureKeyStore get() = keyStore
    val providerIds: List<String> get() = ModelRegistry.allProviderIds()

    /** Per-assistant-role model chain, filtered by the toggle in Settings/model picker. */
    private val roleChains = mutableStateMapOf<AssistantRole, List<String>>()

    fun chainFor(role: AssistantRole): List<String> =
        roleChains[role] ?: ModelRegistry.defaultChainFor(role)

    fun isProviderEnabled(role: AssistantRole, providerId: String): Boolean =
        chainFor(role).contains(providerId)

    /** Toggles one provider in/out of this role's fallback chain (order preserved). */
    fun toggleProvider(role: AssistantRole, providerId: String, enabled: Boolean) {
        val current = chainFor(role)
        roleChains[role] = if (enabled) {
            if (current.contains(providerId)) current else (current + providerId).take(5)
        } else {
            current.filterNot { it == providerId }
        }
    }

    fun selectRole(role: AssistantRole) {
        selectedRole = role
        val project = InMemoryAppStore.projectsFor(role).firstOrNull()
            ?: InMemoryAppStore.createProject(role, "محادثة سريعة")
        openProject(project)
    }

    fun openProject(project: Project) {
        selectedProject = project
        selectedRole = project.assistantRole
        currentConversation = project.conversations.firstOrNull()
            ?: InMemoryAppStore.createConversation(project)
        syncMessagesFromConversation()
    }

    fun newChat() {
        val project = selectedProject ?: return
        currentConversation = InMemoryAppStore.createConversation(project)
        messages = emptyList()
    }

    private fun syncMessagesFromConversation() {
        val conversation = currentConversation ?: return
        messages = conversation.messages.map {
            UiMessage(fromUser = it.role == "user", text = it.text, time = "")
        }
    }

    fun addUserMessageOptimistically(text: String) {
        messages = messages + UiMessage(true, text, "الآن")
    }

    /** Sends through the real fallback orchestrator; call from a coroutine scope. */
    suspend fun send(text: String) {
        val conversation = currentConversation ?: return
        val assistant: BaseAssistant = if (selectedRole == AssistantRole.CODING) codingAssistant else chatAssistant
        sending = true
        lastError = null
        when (val result = assistant.sendMessage(conversation, text, chainFor(selectedRole))) {
            is OrchestratedResult.Success -> {
                syncMessagesFromConversation()
            }
            is OrchestratedResult.Offline -> {
                lastError = "لا يوجد اتصال بالإنترنت"
            }
            is OrchestratedResult.AllModelsFailed -> {
                lastError = "كل النماذج المتاحة فشلت — تحقق من مفاتيح API في الإعدادات"
            }
        }
        sending = false
    }
}
