package com.shadow.os.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.shadow.os.MainActivity
import com.shadow.os.bridge.ShadowRuntimeBridge
import kotlinx.coroutines.*

/**
 * Maintains a persistent foreground service running Ghost's continuous background loop,
 * publishing active heartbeat stats, monitoring battery optimization constraints, and triggering
 * system-wide notifications for goal updates or Level 2 sensitive task approvals.
 */
class ShadowForegroundService : Service() {
    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var isLoopRunning = false

    companion object {
        private const val TAG = "ShadowForegroundService"
        private const val CHANNEL_ID = "shadow_os_channel"
        private const val NOTIFICATION_ID = 8888
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(
            NOTIFICATION_ID,
            buildNotification("Ghost System is Active", "Shadow AI Operating System is monitoring goals."),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            } else {
                0
            }
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(TAG, "Shadow OS background Service triggered onStartCommand.")
        startContinuousReasoningLoop()
        return START_STICKY
    }

    private fun startContinuousReasoningLoop() {
        if (isLoopRunning) return
        isLoopRunning = true
        serviceScope.launch {
            while (isActive) {
                try {
                    // Query the status of the Python daemon loop via our unified runtime bridge
                    val statusStr = ShadowRuntimeBridge.executeCommand("status")
                    Log.v(TAG, "Autonomous Heartbeat Status Query:\n$statusStr")

                    // Inspect database for pending Safety Level 2 hold actions requiring manual approval
                    val pendingApprovalsJson = ShadowRuntimeBridge.queryDatabase(
                        "SELECT id, action FROM approvals WHERE status = 'pending'"
                    )
                    if (pendingApprovalsJson != "[]" && pendingApprovalsJson.startsWith("[")) {
                        triggerApprovalNotification()
                    }

                    // Simulated 15 seconds heartbeat interval
                    delay(15000)
                } catch (e: Exception) {
                    Log.e(TAG, "Error inside continuous background reasoning loop: ${e.message}")
                    delay(5000)
                }
            }
        }
    }

    private fun triggerApprovalNotification() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Shadow OS Approval Required")
            .setContentText("A Safety Level 2 action is on hold. Tap to approve or reject.")
            .setSmallIcon(android.R.drawable.stat_sys_warning)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(9999, notification)
    }

    private fun buildNotification(title: String, text: String): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Shadow OS System Monitor"
            val descriptionText = "Monitors background goals, daemon heartbeats, and safety approvals."
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isLoopRunning = false
        serviceScope.cancel()
        Log.i(TAG, "Shadow OS background service destroyed.")
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
}
