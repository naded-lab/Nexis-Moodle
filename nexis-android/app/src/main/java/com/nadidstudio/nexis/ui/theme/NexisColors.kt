package com.nadidstudio.nexis.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Shared Nexis brand palette.
 *
 * Splash and Login previously each declared their own private copies of
 * these same values — pulled out here so every new screen (Home, Projects,
 * Conversations, ...) uses one source of truth instead of re-typing hex
 * codes. Splash/Login were updated to reference this object too.
 */
object NexisColors {
    val Teal = Color(0xFF0F6E56)
    val TealLight = Color(0xFF3FA98A)
    val White = Color(0xFFFFFFFF)
    val ButtonBorderGray = Color(0xFFD9DCE1)
    val TextDark = Color(0xFF23262B)

    /** Neutral card background used on Home/Projects/Conversations lists. */
    val CardBackground = Color(0xFFF4F6F5)
}
