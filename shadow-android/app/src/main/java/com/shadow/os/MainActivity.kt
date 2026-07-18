package com.shadow.os

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.fragment.app.FragmentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.shadow.os.bridge.ShadowRuntimeBridge
import com.shadow.os.security.BiometricAuthenticator
import com.shadow.os.ui.navigation.Screen
import com.shadow.os.ui.navigation.Sidebar
import com.shadow.os.ui.screens.*
import com.shadow.os.ui.theme.DarkGray
import com.shadow.os.ui.theme.ShadowTheme

/**
 * Android Main Activity entrypoint for the native Shadow AI Operating System.
 * Handles side-drawer navigation, launches the local Chaquopy Python VM, deep-linked short-cuts routing,
 * and enforces biometric authentication gatekeepers for Safety Level 2 actions.
 */
class MainActivity : FragmentActivity() {
    private var currentScreenState = mutableStateOf<Screen>(Screen.Dashboard)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Bootstrapping our direct Python bridge
        ShadowRuntimeBridge.initialize(applicationContext)

        // Process potential shortcut intents or custom deep links
        handleIntent(intent)

        setContent {
            ShadowTheme {
                var currentScreen by remember { currentScreenState }

                Row(modifier = Modifier.fillMaxSize()) {
                    Sidebar(
                        currentScreen = currentScreen,
                        onScreenSelected = { selectedScreen ->
                            // Enforce secure biometric prompts on critical developer consoles or admin tools
                            if (selectedScreen == Screen.Developer || selectedScreen == Screen.Settings) {
                                triggerSecureCheck(selectedScreen)
                            } else {
                                currentScreen = selectedScreen
                            }
                        }
                    )

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .background(DarkGray)
                    ) {
                        when (currentScreen) {
                            Screen.Dashboard -> DashboardScreen()
                            Screen.Chat -> ChatScreen()
                            Screen.Tasks -> TaskManagerScreen()
                            Screen.Memory -> MemoryExplorerScreen()
                            Screen.Web -> WebIntelligenceScreen()
                            Screen.Mcp -> McpManagerScreen()
                            Screen.Providers -> ProviderManagerScreen()
                            Screen.Capabilities -> CapabilityExplorerScreen()
                            Screen.Sandbox -> SandboxManagerScreen()
                            Screen.Plugins -> PluginManagerScreen()
                            Screen.File -> FileManagerScreen()
                            Screen.Logs -> LiveLogViewerScreen()
                            Screen.Settings -> SettingsScreen()
                            Screen.Developer -> DeveloperConsoleScreen()
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val action = intent?.action
        val data = intent?.data

        if (action == Intent.ACTION_VIEW && data != null) {
            val path = data.path
            if (path != null) {
                if (path.contains("chat")) {
                    currentScreenState.value = Screen.Chat
                } else if (path.contains("tasks")) {
                    currentScreenState.value = Screen.Tasks
                }
            }
        } else {
            val shortcutAction = intent?.getStringExtra("shortcut_action")
            if (shortcutAction == "chat") {
                currentScreenState.value = Screen.Chat
            }
        }
    }

    private fun triggerSecureCheck(targetScreen: Screen) {
        if (BiometricAuthenticator.isBiometricAvailable(this)) {
            BiometricAuthenticator.authenticate(
                activity = this,
                title = "Security Verification",
                subtitle = "Authorization required for: ${targetScreen.title}",
                onSuccess = {
                    currentScreenState.value = targetScreen
                },
                onError = { errMsg ->
                    Toast.makeText(this, "Authentication failed: $errMsg", Toast.LENGTH_SHORT).show()
                }
            )
        } else {
            // Bypass gracefully if hardware not available
            currentScreenState.value = targetScreen
        }
    }
}
