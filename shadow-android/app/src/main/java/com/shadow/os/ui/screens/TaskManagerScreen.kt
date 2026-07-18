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
fun TaskManagerScreen() {
    val coroutineScope = rememberCoroutineScope()
    var tasksList by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var approvalsList by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var operationLogs by remember { mutableStateOf("Ready to initiate tasks execution workflow.") }

    fun refreshData() {
        coroutineScope.launch {
            val tasksStr = ShadowRuntimeBridge.queryDatabase("SELECT id, title, priority_score, safety_level, status FROM tasks")
            if (tasksStr.startsWith("[")) {
                val arr = JSONArray(tasksStr)
                val list = mutableListOf<JSONObject>()
                for (i in 0 until arr.length()) {
                    list.add(arr.getJSONObject(i))
                }
                tasksList = list
            }

            val approvalsStr = ShadowRuntimeBridge.queryDatabase("SELECT id, task_id, action, parameters, status FROM approvals")
            if (approvalsStr.startsWith("[")) {
                val arr = JSONArray(approvalsStr)
                val list = mutableListOf<JSONObject>()
                for (i in 0 until arr.length()) {
                    list.add(arr.getJSONObject(i))
                }
                approvalsList = list
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshData()
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
                text = "TASK QUEUES & APPROVALS MANAGER",
                style = MaterialTheme.typography.titleLarge,
                color = AccentColor
            )
        }

        // Section: Pending Approvals (L2 Holds)
        item {
            Text(
                text = "PENDING ACTION APPROVALS (SAFETY LEVEL 2)",
                style = MaterialTheme.typography.bodyLarge,
                color = AccentColor
            )
        }

        if (approvalsList.isEmpty()) {
            item {
                Text(text = "No pending approvals in queue.", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            items(approvalsList.size) { index ->
                val app = approvalsList[index]
                val id = app.optString("id")
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = "Approval Request #$id", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "Action: ${app.optString("action")}")
                        Text(text = "Params: ${app.optString("parameters")}")
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                onClick = {
                                    coroutineScope.launch {
                                        ShadowRuntimeBridge.executeCommand("approvals") // manually handles standard app trigger
                                        operationLogs = "Manually processed approval request #$id."
                                        refreshData()
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                            ) {
                                Text("APPROVE", color = androidx.compose.ui.graphics.Color.Black)
                            }
                        }
                    }
                }
            }
        }

        // Section: Active Task Queue
        item {
            Text(
                text = "ACTIVE TASK QUEUE",
                style = MaterialTheme.typography.bodyLarge,
                color = AccentColor
            )
        }

        if (tasksList.isEmpty()) {
            item {
                Text(text = "No active tasks generated yet.", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            items(tasksList.size) { index ->
                val task = tasksList[index]
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = "Task #${task.optString("id")}", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                            Text(text = "Priority: ${task.optString("priority_score")}", style = MaterialTheme.typography.labelSmall)
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = task.optString("title"), style = MaterialTheme.typography.bodyLarge)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "Safety: L${task.optString("safety_level")} | Status: ${task.optString("status")}")
                    }
                }
            }
        }

        // Live Log Viewer Box
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardBackground)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(text = "OPERATIONAL REASONING LOGS", style = MaterialTheme.typography.labelSmall, color = AccentColor)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = operationLogs)
                }
            }
        }
    }
}
