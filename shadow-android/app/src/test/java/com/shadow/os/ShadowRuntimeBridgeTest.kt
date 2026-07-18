package com.shadow.os

import org.junit.Test
import org.junit.Assert.*
import com.shadow.os.bridge.ShadowRuntimeBridge
import kotlinx.coroutines.runBlocking

class ShadowRuntimeBridgeTest {
    @Test
    fun testExecuteCommandSimulation() = runBlocking {
        val result = ShadowRuntimeBridge.executeCommand("status")
        assertTrue(result.contains("System: Shadow"))
        assertTrue(result.contains("Daemon Status"))
    }

    @Test
    fun testQueryDatabaseSimulation() = runBlocking {
        val result = ShadowRuntimeBridge.queryDatabase("SELECT * FROM goals")
        assertTrue(result.startsWith("["))
        assertTrue(result.contains("Establish Security Protocols"))
    }
}
