package com.nadidstudio.nexis.data

import androidx.compose.runtime.mutableStateListOf
import com.nadidstudio.nexis.assistants.AssistantRole
import com.nadidstudio.nexis.assistants.Conversation
import com.nadidstudio.nexis.assistants.Project
import java.util.UUID

/**
 * Placeholder data store for Projects/Conversations.
 *
 * This stands in for the real local-storage layer (local-first persistence,
 * later backed up to GitHub) which hasn't been built yet — nothing here
 * survives a process death. The UI screens only call the functions below,
 * so swapping this object's internals for real persistence later won't
 * require touching Home/Projects/Conversations screens.
 */
object InMemoryAppStore {
    val codingProjects = mutableStateListOf<Project>()
    val chatProjects = mutableStateListOf<Project>()

    private fun listFor(role: AssistantRole) =
        if (role == AssistantRole.CODING) codingProjects else chatProjects

    fun projectsFor(role: AssistantRole): List<Project> = listFor(role)

    fun createProject(role: AssistantRole, name: String): Project {
        val project = Project(id = UUID.randomUUID().toString(), name = name, assistantRole = role)
        listFor(role).add(project)
        return project
    }

    fun findProject(projectId: String): Project? =
        (codingProjects + chatProjects).find { it.id == projectId }

    fun createConversation(project: Project): Conversation {
        val conversation = Conversation(id = UUID.randomUUID().toString(), projectId = project.id)
        project.conversations.add(conversation)
        return conversation
    }
}
