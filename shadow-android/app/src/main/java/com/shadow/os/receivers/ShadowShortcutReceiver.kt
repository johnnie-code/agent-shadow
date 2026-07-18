package com.shadow.os.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import android.widget.Toast

/**
 * Handles incoming events from native Android shortcuts (Quick Chat, New Task, Capture Idea).
 */
class ShadowShortcutReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "ShadowShortcutReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.getStringExtra("action_type") ?: return
        Log.i(TAG, "Shortcuts quick action received: $action")
        Toast.makeText(context, "Executing Shortcut: $action", Toast.LENGTH_SHORT).show()
    }
}
