import os
import shutil
import pytest
from typer.testing import CliRunner
from shadow.cli.main import app
from shadow.core.config import SHADOW_HOME

runner = CliRunner()

def test_backup_and_restore_commands():
    # Setup directories
    env_dir = os.path.join(SHADOW_HOME, "config")
    os.makedirs(env_dir, exist_ok=True)
    env_file = os.path.join(env_dir, ".env")
    with open(env_file, "w") as f:
        f.write("SHADOW_USER_NAME=\"Backup Tester\"\n")

    mission_file = os.path.join(SHADOW_HOME, "mission.md")
    with open(mission_file, "w") as f:
        f.write("# MISSION\n\n- Goal 1")

    # 1. Run backup
    result = runner.invoke(app, ["backup"])
    assert result.exit_code == 0
    assert "✓ Created backup" in result.stdout

    # 2. Verify backup folder is created
    backup_root = os.path.join(SHADOW_HOME, "backups")
    assert os.path.exists(backup_root)
    backups = sorted([d for d in os.listdir(backup_root) if d.startswith("backup_")])
    assert len(backups) > 0

    backup_name = backups[-1]

    # Delete original files to test restoration
    if os.path.exists(env_file):
        os.remove(env_file)
    if os.path.exists(mission_file):
        os.remove(mission_file)

    # 3. Run restore command (interactively confirm y)
    result = runner.invoke(app, ["restore", backup_name], input="y\n")
    print("RESTORE RESULT:", result.stdout)
    assert result.exit_code == 0
    assert "✓ Restoration completed successfully" in result.stdout

    # 4. Verify files are restored
    print("ENV FILE EXISTS:", os.path.exists(env_file))
    print("BACKUP DIR CONTENT:", os.listdir(os.path.join(backup_root, backup_name)))
    assert os.path.exists(env_file)
    assert os.path.exists(mission_file)
    with open(env_file, "r") as f:
        content = f.read()
        assert "Backup Tester" in content
