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
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun McpManagerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var serversList by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var operationsLog by remember { mutableStateOf("Ready to configure Model Context Protocol (MCP) servers.") }

    fun refreshServers() {
        coroutineScope.launch {
            val res = ShadowRuntimeBridge.queryDatabase("SELECT name, description, transport, status, tools FROM mcp_servers")
            if (res.startsWith("[")) {
                val arr = JSONArray(res)
                val list = mutableListOf<JSONObject>()
                for (i in 0 until arr.length()) {
                    list.add(arr.getJSONObject(i))
                }
                serversList = list
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshServers()
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
                text = "MODEL CONTEXT PROTOCOL (MCP) MANAGER",
                style = MaterialTheme.typography.titleLarge,
                color = AccentColor
            )
        }

        item {
            Text(
                text = "CONFIGURED MCP SERVERS",
                style = MaterialTheme.typography.bodyLarge,
                color = AccentColor
            )
        }

        if (serversList.isEmpty()) {
            item {
                Text(text = "No MCP servers registered in database.", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            items(serversList.size) { index ->
                val s = serversList[index]
                val name = s.optString("name")
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = name, style = MaterialTheme.typography.titleLarge, color = AccentColor)
                            Text(text = s.optString("status").uppercase(), style = MaterialTheme.typography.labelSmall)
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = s.optString("description"))
                        Text(text = "Transport: ${s.optString("transport")}")
                        Text(text = "Discovered Tools: ${s.optString("tools")}", color = AccentColor)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                onClick = {
                                    coroutineScope.launch {
                                        ShadowRuntimeBridge.executeCommand("mcp", listOf("start", name))
                                        operationsLog = "Started MCP Server: $name"
                                        refreshServers()
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                            ) {
                                Text("START", color = androidx.compose.ui.graphics.Color.Black)
                            }

                            Button(
                                onClick = {
                                    coroutineScope.launch {
                                        ShadowRuntimeBridge.executeCommand("mcp", listOf("stop", name))
                                        operationsLog = "Stopped MCP Server: $name"
                                        refreshServers()
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                            ) {
                                Text("STOP", color = androidx.compose.ui.graphics.Color.Black)
                            }
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
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(text = "MCP OPERATIONS LOG", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = operationsLog)
                }
            }
        }
    }
}
