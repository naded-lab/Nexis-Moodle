package com.nadidstudio.nexis.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color

/**
 * Palette for the new chat/drawer/settings/projects design
 * (design source: nexis-all-screens-light-dark.html — kept exactly as
 * delivered; do not restyle). Splash/Login keep using [NexisColors]
 * (their own earlier, already-approved identity) untouched.
 */
object NexisPalette {
    val LightBackground = Color(0xFFFFFFFF)
    val LightSurface = Color(0xFFF6F7F6)
    val LightSurfaceAlt = Color(0xFFEDEFEE)
    val LightText = Color(0xFF12201B)
    val LightSecondary = Color(0xFF5B655F)
    val LightMuted = Color(0xFF8B958F)
    val LightBorder = Color(0xFFE7EAE8)
    val Accent = Color(0xFF0F6E56)
    val Accent2 = Color(0xFF17B893)

    val DarkBackground = Color(0xFF0B0F0D)
    val DarkSurface = Color(0xFF151B19)
    val DarkSurfaceAlt = Color(0xFF1E2624)
    val DarkText = Color(0xFFECEFED)
    val DarkSecondary = Color(0xFF9CA6A1)
    val DarkMuted = Color(0xFF66716C)
    val DarkBorder = Color(0xFF232B29)

    /** Alias so screens can use one name regardless of theme (matches uploaded UI's usage). */
    val Muted: Color get() = LightMuted
}

private val LightColors = lightColorScheme(
    primary = NexisPalette.Accent,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD9F1E9),
    onPrimaryContainer = NexisPalette.LightText,
    secondary = NexisPalette.Accent2,
    onSecondary = NexisPalette.LightText,
    background = NexisPalette.LightBackground,
    onBackground = NexisPalette.LightText,
    surface = NexisPalette.LightBackground,
    onSurface = NexisPalette.LightText,
    surfaceContainer = NexisPalette.LightSurface,
    surfaceContainerHigh = NexisPalette.LightSurfaceAlt,
    outline = NexisPalette.LightBorder,
    outlineVariant = NexisPalette.LightBorder
)

private val DarkColors = darkColorScheme(
    primary = NexisPalette.Accent2,
    onPrimary = NexisPalette.DarkBackground,
    primaryContainer = Color(0xFF103D31),
    onPrimaryContainer = NexisPalette.DarkText,
    secondary = NexisPalette.Accent2,
    onSecondary = NexisPalette.DarkBackground,
    background = NexisPalette.DarkBackground,
    onBackground = NexisPalette.DarkText,
    surface = NexisPalette.DarkBackground,
    onSurface = NexisPalette.DarkText,
    surfaceContainer = NexisPalette.DarkSurface,
    surfaceContainerHigh = NexisPalette.DarkSurfaceAlt,
    outline = NexisPalette.DarkBorder,
    outlineVariant = NexisPalette.DarkBorder
)

/** User's appearance choice — set from the Settings screen, read here so the
 * whole app (not just Settings) reacts immediately when it changes. */
enum class AppearanceMode(val label: String) {
    SYSTEM("افتراضي (حسب النظام)"),
    DARK("داكن"),
    LIGHT("فاتح")
}

object NexisAppearance {
    var mode: AppearanceMode by mutableStateOf(AppearanceMode.SYSTEM)
}

@Composable
fun NexisTheme(content: @Composable () -> Unit) {
    val systemDark = isSystemInDarkTheme()
    val darkTheme = when (NexisAppearance.mode) {
        AppearanceMode.SYSTEM -> systemDark
        AppearanceMode.DARK -> true
        AppearanceMode.LIGHT -> false
    }
    MaterialTheme(colorScheme = if (darkTheme) DarkColors else LightColors, content = content)
}
