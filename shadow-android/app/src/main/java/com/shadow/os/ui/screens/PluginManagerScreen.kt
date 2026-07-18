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
fun PluginManagerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var pluginsStatus by remember { mutableStateOf("Discovering system plugins...") }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            pluginsStatus = ShadowRuntimeBridge.executeCommand("plugins")
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
                text = "SYSTEM PLUGIN REGISTRY",
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
                    Text(text = "DISCOVERED PLUGINS & EXTENSIONS", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = pluginsStatus)
                }
            }
        }
    }
}
