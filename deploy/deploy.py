#!/usr/bin/env python3
"""One-click backend deployment script for Video File Management.

This script is natively executed by the double-clickable 'Deploy Video Tools.app'.
It installs the python package, copies shell wrappers, and directly populates
macOS Automator Workflows into ~/Library/Services/.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def execute(command: list[str], cwd: Path) -> None:
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR executing {' '.join(command)}")
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


def create_automator_workflow(name: str, shell_command: str, output_dir: Path) -> None:
    """Generates a raw Automotive Workflow bundle from an XML template."""
    safe_command = shell_command.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    wflow_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AMApplicationBuild</key>
	<string>523</string>
	<key>AMApplicationVersion</key>
	<string>2.10</string>
	<key>AMDocumentVersion</key>
	<string>2</string>
	<key>actions</key>
	<array>
		<dict>
			<key>action</key>
			<dict>
				<key>AMAccepts</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Optional</key>
					<true/>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>AMProvides</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>ActionBundlePath</key>
				<string>/System/Library/Automator/Run Shell Script.action</string>
				<key>ActionName</key>
				<string>Run Shell Script</string>
				<key>ActionParameters</key>
				<dict>
					<key>COMMAND_STRING</key>
					<string>{safe_command}</string>
					<key>CheckedForUserDefaultShell</key>
					<true/>
					<key>inputMethod</key>
					<integer>1</integer>
					<key>shell</key>
					<string>/bin/zsh</string>
					<key>source</key>
					<string></string>
				</dict>
				<key>BundleIdentifier</key>
				<string>com.apple.RunShellScript</string>
				<key>CFBundleVersion</key>
				<string>2.0.3</string>
				<key>CanShowSelectedItemsWhenRun</key>
				<false/>
				<key>CanShowWhenRun</key>
				<true/>
				<key>Category</key>
				<array>
					<string>AMCategoryUtilities</string>
				</array>
				<key>Class Name</key>
				<string>RunShellScriptAction</string>
				<key>InputUUID</key>
				<string>00000000-0000-0000-0000-000000000000</string>
				<key>Keywords</key>
				<array><string>Shell</string><string>Script</string><string>Command</string><string>Run</string><string>Unix</string></array>
				<key>OutputUUID</key>
				<string>11111111-1111-1111-1111-111111111111</string>
				<key>UUID</key>
				<string>22222222-2222-2222-2222-222222222222</string>
				<key>UnlocalizedApplications</key>
				<array><string>Automator</string></array>
				<key>arguments</key>
				<dict>
					<key>0</key><dict><key>default value</key><integer>0</integer><key>name</key><string>inputMethod</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>0</string></dict>
					<key>1</key><dict><key>default value</key><false/><key>name</key><string>CheckedForUserDefaultShell</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>1</string></dict>
					<key>2</key><dict><key>default value</key><string></string><key>name</key><string>source</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>2</string></dict>
					<key>3</key><dict><key>default value</key><string></string><key>name</key><string>COMMAND_STRING</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>3</string></dict>
					<key>4</key><dict><key>default value</key><string>/bin/sh</string><key>name</key><string>shell</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>4</string></dict>
				</dict>
			</dict>
		</dict>
	</array>
	<key>workflowMetaData</key>
	<dict>
		<key>applicationBundleIDsByPath</key>
		<dict/>
		<key>applicationPaths</key>
		<array/>
		<key>inputTypeIdentifier</key>
		<string>com.apple.Automator.fileSystemObject</string>
		<key>outputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>presentationMode</key>
		<integer>15</integer>
		<key>processesInput</key>
		<false/>
		<key>serviceInputTypeIdentifier</key>
		<string>com.apple.Automator.fileSystemObject</string>
		<key>serviceOutputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>serviceProcessesInput</key>
		<false/>
		<key>systemImageName</key>
		<string>NSActionTemplate</string>
		<key>useAutomaticInputType</key>
		<false/>
		<key>workflowTypeIdentifier</key>
		<string>com.apple.Automator.servicesMenu</string>
	</dict>
</dict>
</plist>
"""
    workflow_path = output_dir / f"{name}.workflow"
    # Ensure a clean state
    if workflow_path.exists():
        shutil.rmtree(workflow_path)

    contents_path = workflow_path / "Contents"
    contents_path.mkdir(parents=True)

    wflow_file = contents_path / "document.wflow"
    wflow_file.write_text(wflow_content)
    print(f"Created Quick Action: {workflow_path}")


def main() -> None:
    project_root = Path(__file__).parent.parent.absolute()
    home_dir = Path.home()

    print("=== Deploying Video Tools ===")

    print("\n1. Installing Python Backend locally...")
    # Ensures python dependencies, including `pytest` and basic cli commands
    execute([sys.executable, "-m", "pip", "install", "-e", "."], cwd=project_root)

    print("\n2. Configuring wrapper scripts in ~/bin...")
    bin_dir = home_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    for script_name in ["remux-to-mp4.sh", "chapterize-video.sh"]:
        source = project_root / "quickactions" / script_name
        dest = bin_dir / script_name.replace(".sh", "")
        shutil.copy2(source, dest)
        dest.chmod(0o755)
        print(f"Installed {dest}")

    print("\n3. Generating and Installing macOS Automator Workflows...")
    services_dir = home_dir / "Library" / "Services"
    services_dir.mkdir(parents=True, exist_ok=True)

    # 3a. Remux Video
    remux_command = 'source ~/.zprofile 2>/dev/null; source ~/.zshrc 2>/dev/null;\n"$HOME/bin/remux-to-mp4" "$@"'
    create_automator_workflow("Remux to MP4 (Copy)", remux_command, services_dir)

    # 3b. Chapterize Video
    chap_command = 'source ~/.zprofile 2>/dev/null; source ~/.zshrc 2>/dev/null;\n"$HOME/bin/chapterize-video" "$@"'
    create_automator_workflow("Chapterize Video", chap_command, services_dir)

    print("\n=== Deployment Complete ===")


if __name__ == "__main__":
    main()
