package com.shadow.os.receivers

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import com.shadow.os.MainActivity
import com.shadow.os.R
import com.shadow.os.bridge.ShadowRuntimeBridge
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Android home screen widget provider displaying system heartbeats, remaining active goals,
 * and quick action hooks.
 */
class ShadowWidgetProvider : AppWidgetProvider() {
    private val scope = CoroutineScope(Dispatchers.Main)

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (appWidgetId in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId)
        }
    }

    private fun updateAppWidget(context: Context, appWidgetManager: AppWidgetManager, appWidgetId: Int) {
        val views = RemoteViews(context.packageName, R.layout.widget_layout)

        scope.launch {
            try {
                // Read active goals from SQLite database via bridge
                val res = ShadowRuntimeBridge.queryDatabase("SELECT COUNT(*) as cnt FROM goals WHERE status != 'completed'")
                if (res.startsWith("[")) {
                    val cnt = org.json.JSONArray(res).optJSONObject(0)?.optString("cnt") ?: "0"
                    views.setTextViewText(R.id.widget_goals, "Remaining goals: $cnt")
                }
            } catch (e: Exception) {
                views.setTextViewText(R.id.widget_goals, "Remaining goals: --")
            }

            // Quick Chat Button pending intent mapping
            val chatIntent = Intent(context, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                putExtra("shortcut_action", "chat")
            }
            val chatPendingIntent = PendingIntent.getActivity(
                context, 0, chatIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.btn_quick_chat, chatPendingIntent)

            // Update on device screen
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }
}
