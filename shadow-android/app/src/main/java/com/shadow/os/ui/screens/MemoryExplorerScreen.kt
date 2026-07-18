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
fun MemoryExplorerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var searchInput by remember { mutableStateOf("") }
    var memoriesList by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var activeChronologyLog by remember { mutableStateOf("Ready to search persistent memory graph blocks.") }

    fun performSearch(query: String) {
        coroutineScope.launch {
            val sql = if (query.isBlank()) {
                "SELECT id, category, key, content, tags, importance_level, importance_score, workspace FROM memory"
            } else {
                "SELECT id, category, key, content, tags, importance_level, importance_score, workspace FROM memory WHERE content LIKE '%$query%' OR key LIKE '%$query%'"
            }
            val res = ShadowRuntimeBridge.queryDatabase(sql)
            if (res.startsWith("[")) {
                val arr = JSONArray(res)
                val list = mutableListOf<JSONObject>()
                for (i in 0 until arr.length()) {
                    list.add(arr.getJSONObject(i))
                }
                memoriesList = list
            }
            activeChronologyLog = "Queried sqlite database for: '$query'. Found ${memoriesList.size} blocks."
        }
    }

    LaunchedEffect(Unit) {
        performSearch("")
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
                text = "PERSISTENT MEMORY EXPLORER",
                style = MaterialTheme.typography.titleLarge,
                color = AccentColor
            )
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TextField(
                    value = searchInput,
                    onValueChange = { searchInput = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("Search long-term semantic memory blocks...") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CardBackground,
                        unfocusedContainerColor = CardBackground
                    )
                )
                Button(
                    onClick = { performSearch(searchInput) },
                    colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                ) {
                    Text("SEARCH", color = androidx.compose.ui.graphics.Color.Black)
                }
            }
        }

        item {
            Text(
                text = "DISCOVERED SEMANTIC GRAPH MEMORIES",
                style = MaterialTheme.typography.bodyLarge,
                color = AccentColor
            )
        }

        if (memoriesList.isEmpty()) {
            item {
                Text(text = "No memories indexed or matched.", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            items(memoriesList.size) { index ->
                val mem = memoriesList[index]
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = "ID: ${mem.optString("id")} | Category: ${mem.optString("category")}", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                            Text(text = "Score: ${mem.optString("importance_score")}", style = MaterialTheme.typography.labelSmall)
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "Key: ${mem.optString("key")}", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = mem.optString("content"), style = MaterialTheme.typography.bodyLarge)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "Tags: ${mem.optString("tags")} | Scope: ${mem.optString("workspace")}", style = MaterialTheme.typography.labelSmall)
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
                    Text(text = "SYSTEM METRICS & AUDITING", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = activeChronologyLog)
                }
            }
        }
    }
}
