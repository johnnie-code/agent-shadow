package com.shadow.os.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = AccentColor,
    background = DarkGray,
    surface = SurfaceColor,
    onBackground = TextColorPrimary,
    onSurface = TextColorPrimary,
    error = ErrorColor
)

@Composable
fun ShadowTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography,
        content = content
    )
}
