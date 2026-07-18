package com.shadow.os.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.shadow.os.services.ShadowForegroundService

/**
 * Triggers the continuous reasoning foreground service on system boot-up to ensure
 * autonomous background tasks run seamlessly without user intervention.
 */
class ShadowBootReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "ShadowBootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i(TAG, "Device booted. Initializing Shadow OS background service...")
            val serviceIntent = Intent(context, ShadowForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent)
            } else {
                context.startService(serviceIntent)
            }
        }
    }
}
