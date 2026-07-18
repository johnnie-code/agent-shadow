package com.shadow.os.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.shadow.os.ui.theme.AccentColor
import com.shadow.os.ui.theme.DarkGray

sealed class Screen(val route: String, val title: String) {
    object Dashboard : Screen("dashboard", "Dashboard")
    object Chat : Screen("chat", "Chat")
    object Tasks : Screen("tasks", "Tasks")
    object Memory : Screen("memory", "Memory")
    object Web : Screen("web", "Web")
    object Mcp : Screen("mcp", "MCP")
    object Providers : Screen("providers", "Providers")
    object Capabilities : Screen("capabilities", "Capabilities")
    object Sandbox : Screen("sandbox", "Sandbox")
    object Plugins : Screen("plugins", "Plugins")
    object File : Screen("file", "File")
    object Logs : Screen("logs", "Logs")
    object Settings : Screen("settings", "Settings")
    object Developer : Screen("developer", "Developer")
}

@Composable
fun Sidebar(
    currentScreen: Screen,
    onScreenSelected: (Screen) -> Unit,
    modifier: Modifier = Modifier
) {
    val screens = listOf(
        Screen.Dashboard, Screen.Chat, Screen.Tasks, Screen.Memory,
        Screen.Web, Screen.Mcp, Screen.Providers, Screen.Capabilities,
        Screen.Sandbox, Screen.Plugins, Screen.File, Screen.Logs,
        Screen.Settings, Screen.Developer
    )

    Column(
        modifier = modifier
            .fillMaxHeight()
            .width(220.dp)
            .background(DarkGray)
            .padding(12.dp)
    ) {
        Text(
            text = "SHADOW OS",
            style = MaterialTheme.typography.titleLarge,
            color = AccentColor,
            modifier = Modifier.padding(bottom = 20.dp)
        )
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            items(screens.size) { index ->
                val screen = screens[index]
                val isSelected = screen == currentScreen
                Text(
                    text = screen.title,
                    style = MaterialTheme.typography.bodyLarge,
                    color = if (isSelected) AccentColor else Color.White,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onScreenSelected(screen) }
                        .padding(vertical = 10.dp, horizontal = 8.dp)
                )
            }
        }
    }
}
