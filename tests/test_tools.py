import pytest
from shadow.tools.registry import tool_registry
from shadow.tools.filesystem import ReadFileTool, WriteFileTool
from shadow.tools.android import (
    AndroidBatteryTool, AndroidWifiTool, AndroidBluetoothTool,
    AndroidGPSTool, AndroidApplicationLauncherTool, AndroidCameraTool
)
import os

def test_tool_discovery():
    tool_registry.discover_tools()
    tools = tool_registry.list_tools()
    assert len(tools) > 0

    # Assert presence of core tools
    read_tool = tool_registry.get_tool("read_file")
    assert read_tool is not None
    assert isinstance(read_tool, ReadFileTool)

    battery_tool = tool_registry.get_tool("android_battery")
    assert battery_tool is not None
    assert isinstance(battery_tool, AndroidBatteryTool)

@pytest.mark.asyncio
async def test_filesystem_tools():
    test_file = "tests/temp_test.txt"
    write_tool = WriteFileTool()
    read_tool = ReadFileTool()

    # Write
    write_res = await write_tool.execute(filepath=test_file, content="Shadow test text")
    assert write_res["success"] is True
    assert os.path.exists(test_file)

    # Read
    read_res = await read_tool.execute(filepath=test_file)
    assert read_res["success"] is True
    assert read_res["result"] == "Shadow test text"

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

@pytest.mark.asyncio
async def test_expanded_android_tools():
    # Test Wi-Fi Connection Tool
    wifi_tool = AndroidWifiTool()
    wifi_res = await wifi_tool.execute(scan=False)
    assert wifi_res["success"] is True
    assert "ssid" in wifi_res["result"]

    # Test Bluetooth Tool
    bt_tool = AndroidBluetoothTool()
    bt_res = await bt_tool.execute()
    assert bt_res["success"] is True
    assert len(bt_res["result"]) > 0

    # Test GPS Tool
    gps_tool = AndroidGPSTool()
    gps_res = await gps_tool.execute()
    assert gps_res["success"] is True
    assert "latitude" in gps_res["result"]

    # Test Application Launcher Tool
    launcher_tool = AndroidApplicationLauncherTool()
    launcher_res = await launcher_tool.execute(package_name="com.android.settings")
    assert launcher_res["success"] is True

    # Test Camera Tool
    camera_tool = AndroidCameraTool()
    photo_file = "tests/mock_capture.jpg"
    camera_res = await camera_tool.execute(output_path=photo_file, camera_id=0)
    assert camera_res["success"] is True
    assert os.path.exists(photo_file)

    # Cleanup capture
    if os.path.exists(photo_file):
        os.remove(photo_file)
