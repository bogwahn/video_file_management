#!/bin/bash
# Sync command - mirrors source to destination with move-like behavior
# Usage: sync <source> <destination> <folders...>
#
# Example:
#   sync macbook backup "Documents Photos Videos"
#   sync nas-server external "/Volumes/Media /Users/bogwahn/Downloads"

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validate arguments
if [ $# -lt 3 ]; then
    echo "Error: Insufficient arguments"
    echo ""
    echo "Usage: sync <source-device> <destination-device> <folders>"
    echo ""
    echo "Arguments:"
    echo "  source-device       : Source machine/device name or path"
    echo "  destination-device  : Destination machine/device name or path"
    echo "  folders             : Space-separated list of folders to sync"
    echo ""
    echo "Examples:"
    echo "  sync macbook backup \"Documents Photos Videos\""
    echo "  sync nas external \"/Volumes/Media /Users/bogwahn/Downloads\""
    echo "  sync user@host1:/data user@host2:/backup \"folder1 folder2\""
    exit 1
fi

SOURCE_DEVICE="$1"
DEST_DEVICE="$2"
shift 2
FOLDERS=("$@")

# Function to retrieve password from keychain for a host
get_keychain_password() {
    local hostname="$1"

    # Try to find internet password in keychain
    security find-internet-password -s "$hostname" -w 2>/dev/null || return 1
}

# Function to resolve device path
resolve_path() {
    local device="$1"

    # If it's a path starting with /, ~, or contains :, use as-is (local path or remote)
    if [[ "$device" =~ ^[/~] ]] || [[ "$device" == *:* ]]; then
        echo "$device"
    else
        # Otherwise, treat as a device name and try to find it
        # Check /Volumes first (mounted external drives)
        if [ -d "/Volumes/$device" ]; then
            echo "/Volumes/$device"
        # Then check home directory shortcuts
        elif [ -d "$HOME/$device" ]; then
            echo "$HOME/$device"
        else
            # Assume it's a hostname for SSH
            echo "$device"
        fi
    fi
}

# Function to extract hostname from a path (for remote paths like user@host:/path)
extract_hostname() {
    local path="$1"
    if [[ "$path" == *@* ]]; then
        # Extract hostname from user@host:path format
        echo "$path" | sed -E 's/.*@([^:]+).*/\1/'
    elif [[ "$path" == *:* ]]; then
        # Extract hostname from host:path format
        echo "$path" | sed -E 's/([^:]+).*/\1/'
    fi
}

SOURCE_PATH=$(resolve_path "$SOURCE_DEVICE")
DEST_PATH=$(resolve_path "$DEST_DEVICE")

echo -e "${BLUE}=== Sync Configuration ===${NC}"
echo "Source:      $SOURCE_PATH"
echo "Destination: $DEST_PATH"
echo "Folders:     ${FOLDERS[*]}"
echo ""

# Verify source path exists (skip for remote paths)
if [[ ! "$SOURCE_PATH" == *:* ]]; then
    if [ ! -d "$SOURCE_PATH" ]; then
        echo -e "${RED}Error: Source path does not exist: $SOURCE_PATH${NC}"
        exit 1
    fi
fi

# Build rsync commands for each folder
run_sync() {
    local dry_run="$1"
    local dry_run_flag=""

    if [ "$dry_run" = true ]; then
        dry_run_flag="--dry-run"
    fi

    # Check if we need credentials for remote paths
    local src_host
    src_host=$(extract_hostname "$SOURCE_PATH")
    local dst_host
    dst_host=$(extract_hostname "$DEST_PATH")
    local src_password=""
    local dst_password=""

    if [ -n "$src_host" ]; then
        src_password=$(get_keychain_password "$src_host") || true
    fi

    if [ -n "$dst_host" ]; then
        dst_password=$(get_keychain_password "$dst_host") || true
    fi

    # Check if sshpass is available (needed for password-based SSH)
    local use_sshpass=false
    if command -v sshpass >/dev/null 2>&1; then
        use_sshpass=true
    fi

    for folder in "${FOLDERS[@]}"; do
        # Remove leading/trailing whitespace
        folder=$(echo "$folder" | xargs)

        if [ -z "$folder" ]; then
            continue
        fi

        # Handle paths with spaces - build source and dest
        local src="${SOURCE_PATH}/${folder}"
        local dst="${DEST_PATH}/${folder}"

        echo -e "${YELLOW}Syncing: $folder${NC}"

        # Build rsync command
        # rsync options:
        # -a: archive (recursive, preserve permissions, times, etc)
        # -v: verbose
        # --delete: delete extraneous files from destination
        # --remove-source-files: delete source files after successful transfer
        # --progress: show progress
        # --stats: show statistics
        # --dry-run: preview changes without making them
        local rsync_opts="-av --delete --remove-source-files --progress --stats"
        if [ -n "$dry_run_flag" ]; then
            rsync_opts="$rsync_opts $dry_run_flag"
        fi

        # Use sshpass if passwords are available and sshpass is installed
        if [ "$use_sshpass" = true ] && { [ -n "$src_password" ] || [ -n "$dst_password" ]; }; then
            # If source is remote, use password for source
            if [ -n "$src_password" ]; then
                # shellcheck disable=SC2086
                SSHPASS="$src_password" sshpass -e rsync -e ssh $rsync_opts "$src/" "$dst/"
            # If destination is remote, use password for destination
            elif [ -n "$dst_password" ]; then
                # shellcheck disable=SC2086
                SSHPASS="$dst_password" sshpass -e rsync -e ssh $rsync_opts "$src/" "$dst/"
            else
                # shellcheck disable=SC2086
                rsync $rsync_opts "$src/" "$dst/"
            fi
        else
            # Standard rsync (will use SSH keys if configured)
            # shellcheck disable=SC2086
            rsync $rsync_opts "$src/" "$dst/"
        fi

        echo ""
    done
}

# Perform dry run
echo -e "${BLUE}=== DRY RUN (Preview Only) ===${NC}"
echo ""
run_sync true

# Ask for confirmation
echo ""
echo -e "${YELLOW}Review the changes above.${NC}"
echo ""
echo "This will:"
echo "  1. Update files on destination if source is newer"
echo "  2. Add any files/folders that don't exist on destination"
echo "  3. Delete extraneous files from destination"
echo "  4. Delete synced files from source"
echo ""
read -p "Proceed with sync? (yes/no): " -r CONFIRM

if [[ "$CONFIRM" =~ ^[Yy][Ee][Ss]$ ]]; then
    echo ""
    echo -e "${GREEN}=== EXECUTING SYNC ===${NC}"
    echo ""
    run_sync false
    echo ""
    echo -e "${GREEN}Sync complete!${NC}"
else
    echo -e "${RED}Sync cancelled.${NC}"
    exit 0
fi
