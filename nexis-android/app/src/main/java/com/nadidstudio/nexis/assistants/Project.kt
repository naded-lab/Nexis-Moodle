package com.nadidstudio.nexis.assistants

/** MVP scope: only these two ship in the first version. */
enum class AssistantRole {
    CODING,
    CHAT
}

data class ChatMessage(
    val role: String, // "user" or "assistant"
    val text: String,
    val timestampMillis: Long = System.currentTimeMillis()
)

/**
 * A conversation is isolated from every other conversation, even within
 * the same project — same principle as Claude Projects.
 */
data class Conversation(
    val id: String,
    val projectId: String,
    val messages: MutableList<ChatMessage> = mutableListOf()
)

/**
 * A project groups conversations that share the same uploaded files.
 * Files uploaded here stay available to any new conversation opened
 * inside this project, without re-uploading.
 */
data class Project(
    val id: String,
    val name: String,
    val assistantRole: AssistantRole,
    val uploadedFilePaths: MutableList<String> = mutableListOf(),
    val conversations: MutableList<Conversation> = mutableListOf()
)
