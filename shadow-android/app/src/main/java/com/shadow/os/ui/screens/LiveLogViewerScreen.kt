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
fun LiveLogViewerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var logsText by remember { mutableStateOf("Querying active decision logs...") }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            logsText = ShadowRuntimeBridge.executeCommand("logs")
        }
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
                text = "LIVE DAEMON DECISION LOGS",
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
                    Text(text = "LIVE STDOUT DAEMON STREAMS", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = logsText)
                }
            }
        }
    }
}
