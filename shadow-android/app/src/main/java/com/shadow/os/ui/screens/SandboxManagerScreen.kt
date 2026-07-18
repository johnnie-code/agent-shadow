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
fun SandboxManagerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var sandboxes by remember { mutableStateOf("Querying active sandboxes...") }
    var actionLogs by remember { mutableStateOf("Ready to execute sandbox computer checkpoints.") }

    fun refreshSandbox() {
        coroutineScope.launch {
            sandboxes = ShadowRuntimeBridge.executeCommand("sandbox", listOf("list"))
        }
    }

    LaunchedEffect(Unit) {
        refreshSandbox()
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkGray)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "SANDBOX COMPUTER MANAGER",
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
                    Text(text = "ACTIVE ISOLATED COMPUTERS LIST", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = sandboxes)
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = {
                                coroutineScope.launch {
                                    val res = ShadowRuntimeBridge.executeCommand("sandbox", listOf("create", "sandbox_android"))
                                    actionLogs = res
                                    refreshSandbox()
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("CREATE SANDBOX", color = androidx.compose.ui.graphics.Color.Black)
                        }
                    }
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardBackground)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "SANDBOX OPERATIONS LOGS", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = actionLogs)
                }
            }
        }
    }
}
