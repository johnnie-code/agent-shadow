package com.shadow.os.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.shadow.os.bridge.ShadowRuntimeBridge
import com.shadow.os.ui.theme.AccentColor
import com.shadow.os.ui.theme.CardBackground
import com.shadow.os.ui.theme.DarkGray
import kotlinx.coroutines.launch

data class Message(val content: String, val isUser: Boolean)

@Composable
fun ChatScreen() {
    val coroutineScope = rememberCoroutineScope()
    var input by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<Message>() }
    var isThinking by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        messages.add(Message("Ghost is online and listening. Ask me about your goals, tasks, or request a research crawling job.", false))
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkGray)
            .padding(16.dp)
    ) {
        Text(
            text = "GHOST AGENT CHAT CONSOLE",
            style = MaterialTheme.typography.titleLarge,
            color = AccentColor,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(messages) { msg ->
                val sender = if (msg.isUser) "You" else "Ghost"
                val color = if (msg.isUser) AccentColor else Color.White
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBackground)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = sender, style = MaterialTheme.typography.labelSmall, color = AccentColor)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = msg.content, style = MaterialTheme.typography.bodyLarge, color = color)
                    }
                }
            }
            if (isThinking) {
                item {
                    Text(
                        text = "Ghost is reasoning...",
                        style = MaterialTheme.typography.bodyLarge,
                        color = AccentColor
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            TextField(
                value = input,
                onValueChange = { input = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("How can I help advance your mission goals today?") },
                colors = TextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedContainerColor = CardBackground,
                    unfocusedContainerColor = CardBackground
                )
            )
            Button(
                onClick = {
                    if (input.isNotBlank()) {
                        val query = input
                        messages.add(Message(query, true))
                        input = ""
                        isThinking = true
                        coroutineScope.launch {
                            val reply = ShadowRuntimeBridge.sendChatMessage(query)
                            messages.add(Message(reply, false))
                            isThinking = false
                        }
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
            ) {
                Text("SEND", color = Color.Black)
            }
        }
    }
}
