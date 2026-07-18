package com.shadow.os.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.shadow.os.bridge.ShadowRuntimeBridge
import com.shadow.os.ui.theme.AccentColor
import com.shadow.os.ui.theme.CardBackground
import com.shadow.os.ui.theme.DarkGray
import kotlinx.coroutines.launch

@Composable
fun DeveloperConsoleScreen() {
    val coroutineScope = rememberCoroutineScope()
    var inputCommand by remember { mutableStateOf("") }
    var terminalOutput by remember { mutableStateOf("Shadow OS developers terminal console ready.\nType python or system shell commands directly.") }
    var isRunning by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkGray)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "DEVELOPER COMMAND TERMINAL CONSOLE",
                style = MaterialTheme.typography.titleLarge,
                color = AccentColor
            )
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardBackground)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "TERMINAL STDOUT/STDERR DISPLAY", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = terminalOutput)
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TextField(
                    value = inputCommand,
                    onValueChange = { inputCommand = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("shadow version / status / doctor...") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CardBackground,
                        unfocusedContainerColor = CardBackground
                    ),
                    enabled = !isRunning
                )
                Button(
                    onClick = {
                        if (inputCommand.isNotBlank()) {
                            isRunning = true
                            val fullCmd = inputCommand.trim().split(" ")
                            val cmd = fullCmd[0]
                            val args = if (fullCmd.size > 1) fullCmd.subList(1, fullCmd.size) else emptyList()

                            coroutineScope.launch {
                                val out = ShadowRuntimeBridge.executeCommand(cmd, args)
                                terminalOutput = out
                                inputCommand = ""
                                isRunning = false
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = AccentColor),
                    enabled = !isRunning
                ) {
                    Text("RUN", color = androidx.compose.ui.graphics.Color.Black)
                }
            }
        }
    }
}
