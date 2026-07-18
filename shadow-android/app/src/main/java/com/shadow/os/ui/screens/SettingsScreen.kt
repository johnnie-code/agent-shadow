package com.shadow.os.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.shadow.os.ui.theme.AccentColor
import com.shadow.os.ui.theme.CardBackground
import com.shadow.os.ui.theme.DarkGray

@Composable
fun SettingsScreen() {
    var themePreference by remember { mutableStateOf("Neon Green Standard") }
    var notificationMode by remember { mutableStateOf("Android System") }
    var batterySaverMode by remember { mutableStateOf(true) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkGray)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "GLOBAL PREFERENCES",
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
                    Text(text = "INTERFACE THEME SELECTION", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = "Current: $themePreference")
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { themePreference = "Neon Green Standard" },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("NEON GREEN", color = androidx.compose.ui.graphics.Color.Black)
                        }
                        Button(
                            onClick = { themePreference = "Cyberpunk Dark" },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("CYBERPUNK", color = androidx.compose.ui.graphics.Color.Black)
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
                    Text(text = "NOTIFICATIONS MODE", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = "Current: $notificationMode")
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { notificationMode = "Android System" },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("ANDROID", color = androidx.compose.ui.graphics.Color.Black)
                        }
                        Button(
                            onClick = { notificationMode = "Terminal Console" },
                            colors = ButtonDefaults.buttonColors(containerColor = AccentColor)
                        ) {
                            Text("TERMINAL", color = androidx.compose.ui.graphics.Color.Black)
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
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(text = "BATTERY OPTIMIZED SAVER", style = MaterialTheme.typography.bodyLarge, color = AccentColor)
                        Text(text = "Throttles loop speed under 20% battery")
                    }
                    Switch(
                        checked = batterySaverMode,
                        onCheckedChange = { batterySaverMode = it },
                        colors = SwitchDefaults.colors(checkedThumbColor = AccentColor)
                    )
                }
            }
        }
    }
}
