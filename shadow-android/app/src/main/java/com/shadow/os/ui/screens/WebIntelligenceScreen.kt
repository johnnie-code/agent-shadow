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
fun WebIntelligenceScreen() {
    val coroutineScope = rememberCoroutineScope()
    var targetUrl by remember { mutableStateOf("https://example.com") }
    var scrapeOutput by remember { mutableStateOf("Ready to capture clean content from target webpage.") }
    var crawlStatus by remember { mutableStateOf("Crawl scheduler is currently IDLE.") }
    var isOperating by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkGray)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "WEB INTELLIGENCE ENGINE",
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
                    Text(text = "LIVE SCRAPER & CRAWLER INTERFACE", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(12.dp))
                    TextField(
                        value = targetUrl,
                        onValueChange = { targetUrl = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("Enter target URL to parse or scrape...") },
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = DarkGray,
                            unfocusedContainerColor = DarkGray
                        )
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = {
                                isOperating = true
                                coroutineScope.launch {
                                    val res = ShadowRuntimeBridge.executeCommand("scrape", listOf(targetUrl))
                                    scrapeOutput = res
                                    isOperating = false
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor),
                            enabled = !isOperating
                        ) {
                            Text("SCRAPE PAGE", color = androidx.compose.ui.graphics.Color.Black)
                        }

                        Button(
                            onClick = {
                                isOperating = true
                                coroutineScope.launch {
                                    val res = ShadowRuntimeBridge.executeCommand("crawl", listOf(targetUrl))
                                    crawlStatus = res
                                    isOperating = false
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor),
                            enabled = !isOperating
                        ) {
                            Text("CRAWL SITE", color = androidx.compose.ui.graphics.Color.Black)
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
                    Text(text = "LIVE CRAWL PROGRESS & HISTORY", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = crawlStatus)
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardBackground)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "SCRAPED MARKDOWN PREVIEW", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = scrapeOutput, maxLines = 10)
                }
            }
        }
    }
}
