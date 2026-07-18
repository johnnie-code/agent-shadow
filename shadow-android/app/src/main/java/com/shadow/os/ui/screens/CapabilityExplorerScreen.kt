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
import org.json.JSONObject

@Composable
fun CapabilityExplorerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var capabilityReport by remember { mutableStateOf("Scanning central Capability Registry...") }
    var healthScore by remember { mutableStateOf("100%") }
    var healthMessage by remember { mutableStateOf("Operating normally.") }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            val jsonStr = ShadowRuntimeBridge.getLiveCapabilities()
            if (jsonStr.startsWith("{")) {
                val obj = JSONObject(jsonStr)
                val health = obj.optJSONObject("health")
                healthScore = "${health?.optString("score") ?: "100"}%"
                healthMessage = health?.optString("message") ?: "Operating normally."

                // Formulate human-readable list of sectors
                val sectors = obj.optJSONObject("sectors")
                val sb = StringBuilder()
                sectors?.keys()?.forEach { sectorKey ->
                    sb.append("Sector: ${sectorKey.uppercase()}\n")
                    val arr = sectors.optJSONArray(sectorKey)
                    if (arr != null) {
                        for (i in 0 until arr.length()) {
                            val item = arr.optJSONObject(i)
                            if (item != null) {
                                sb.append("  • Name: ${item.optString("name")}\n")
                                sb.append("    Health: ${item.optString("health")}\n")
                                sb.append("    Enabled: ${item.optBoolean("enabled")}\n")
                                val caps = item.optJSONArray("capabilities")
                                if (caps != null && caps.length() > 0) {
                                    val capsList = mutableListOf<String>()
                                    for (j in 0 until caps.length()) {
                                        capsList.add(caps.getString(j))
                                    }
                                    sb.append("    Capabilities: ${capsList.joinToString(", ")}\n")
                                }
                            }
                        }
                    }
                    sb.append("\n")
                }
                capabilityReport = sb.toString()
            }
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
                text = "SYSTEM CAPABILITY EXPLORER",
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
                    Text(text = "DYNAMIC SECTORS HEALTH REPORT", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "Overall Score:")
                        Text(text = healthScore, color = AccentColor, style = MaterialTheme.typography.titleLarge)
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = "Diagnostic Message: $healthMessage")
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardBackground)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "REGISTERED SYSTEM CAPABILITIES MAP", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = capabilityReport)
                }
            }
        }
    }
}
