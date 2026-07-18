package com.shadow.os.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.shadow.os.bridge.ShadowRuntimeBridge
import com.shadow.os.ui.theme.AccentColor
import com.shadow.os.ui.theme.CardBackground
import com.shadow.os.ui.theme.DarkGray
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun ProviderManagerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var liveProvidersList by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var testLogs by remember { mutableStateOf("Connection latency checker initialized.") }

    fun loadLiveProviders() {
        coroutineScope.launch {
            val jsonStr = ShadowRuntimeBridge.getLiveProviders()
            if (jsonStr.startsWith("[")) {
                val arr = JSONArray(jsonStr)
                val list = mutableListOf<JSONObject>()
                for (i in 0 until arr.length()) {
                    list.add(arr.getJSONObject(i))
                }
                liveProvidersList = list
            }
        }
    }

    LaunchedEffect(Unit) {
        loadLiveProviders()
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
                text = "AI PROVIDERS CONFIGURATION",
                style = MaterialTheme.typography.titleLarge,
                color = AccentColor
            )
        }

        item {
            Text(
                text = "ACTIVE LLM RUNTIMES",
                style = MaterialTheme.typography.bodyLarge,
                color = AccentColor
            )
        }

        if (liveProvidersList.isEmpty()) {
            item {
                Text(text = "No providers dynamically loaded from ProviderManager.", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            items(liveProvidersList.size) { index ->
                val p = liveProvidersList[index]
                val name = p.optString("name").uppercase()
                val isDefault = p.optBoolean("is_default")

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = name, style = MaterialTheme.typography.titleLarge, color = AccentColor)
                            if (isDefault) {
                                Text(text = "DEFAULT BRAIN", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "Class: ${p.optString("class")}")
                        Text(text = "Supports Tools: ${p.optBoolean("supports_tools")}")
                        Text(text = "Supports Streaming: ${p.optBoolean("supports_streaming")}")
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = {
                                coroutineScope.launch {
                                    ShadowRuntimeBridge.executeCommand("config", listOf("default_provider", p.optString("name")))
                                    testLogs = "Set default provider to $name"
                                    loadLiveProviders()
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("SET DEFAULT", color = androidx.compose.ui.graphics.Color.Black)
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
                    Text(text = "AI PROVIDERS LOGS", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = testLogs)
                }
            }
        }
    }
}
