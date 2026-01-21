# EdgeRouter Configuration Backup Tool - Plan

## Overview

### Purpose
Create a Python-based backup tool for a single EdgeOS 2.0+ device running on macOS, with automatic GitHub versioning and Web UI-compatible restore format.

### Problem Statement
EdgeRouter configurations can be lost due to:
- Hardware failure
- Misconfiguration requiring rollback
- Firmware upgrade issues
- Accidental configuration changes

Manual backups are often forgotten or inconsistent. This tool provides a simple, reliable daily backup solution with Git versioning and off-site storage.

### Confirmed Requirements (from User Interview)
- **Platform:** macOS
- **Implementation:** Python with simple script architecture
- **Scale:** Single EdgeRouter device on local network
- **EdgeOS Version:** 2.0+
- **Storage:** GitHub repository with auto-commit/push
- **Authentication:** SSH keys for both EdgeRouter and Git
- **Scheduling:** Manual execution (daily runs by user)
- **Notifications:** macOS native notifications for all events
- **Restore Format:** Web UI compatible (.tar.gz) + text (.cfg)

## Objectives

- Backup single EdgeRouter configuration to GitHub with version history
- Generate both Web UI-compatible (.tar.gz) and human-readable (.cfg) formats
- Automatically commit and push to GitHub after each backup
- Use macOS native notifications for all backup events
- Provide test/dry-run mode for connectivity verification
- Keep implementation simple with minimal dependencies
- Create daily backups on manual execution

## Use Cases

### Primary Use Case: Daily Manual Backup
1. User runs tool manually (e.g., `edgerouter-backup run`)
2. Tool connects to EdgeRouter via SSH key
3. Retrieves configuration in both .tar.gz and .cfg formats
4. Validates backup files (basic checks)
5. Commits files to local Git repository
6. Pushes to GitHub automatically
7. Sends macOS notification with status
8. Logs operation details locally

### Additional Use Cases
- **Pre-change backup:** Run before making configuration changes
- **Test connectivity:** Dry-run mode to verify SSH access and config retrieval
- **View diffs:** Use `git diff` to compare configurations over time
- **Manual restore:** Download .tar.gz from GitHub and upload via EdgeRouter Web UI
- **Audit trail:** Review Git commit history for configuration change timeline

## Technical Architecture

### Implementation Approach: Python Script

**Selected:** Simple Python script optimized for single-device use on macOS

**Why Python:**
- Excellent SSH library support (Paramiko)
- Native macOS notification support (pync or osascript)
- Rich Git integration libraries (GitPython or subprocess)
- Simple deployment (single script or minimal modules)
- Easy to maintain and extend

**Architecture Style:**
- Simple script structure (not heavily modular)
- Direct command execution flow
- Minimal abstraction layers
- Focus on readability and maintainability

## Core Features

### 1. Configuration Retrieval

**SSH Connection:**
- Connect to local EdgeRouter via SSH (port 22)
- Authenticate using SSH key (~/.ssh/id_rsa or ~/.ssh/id_ed25519)
- No password storage required

**EdgeOS Backup Commands:**
```bash
# Create system backup (Web UI compatible .tar.gz)
/opt/vyatta/bin/ubnt-save-config.sh

# Then download the backup file
/config/config.boot.tar.gz

# Also export text configuration for human readability
show configuration commands > /tmp/config.cfg
```

**Output Formats:**
1. **config.boot.tar.gz** - Binary archive compatible with EdgeRouter Web UI restore
2. **config.cfg** - Plain text with all `set` and `delete` commands for diff viewing

### 2. File Storage

**Primary Storage: GitHub Repository**

**Repository Structure (Date-Organized):**
```
edgerouter-backup/
├── 2026/
│   ├── 01/
│   │   ├── backup-2026-01-20.tar.gz
│   │   ├── backup-2026-01-20.cfg
│   │   ├── backup-2026-01-19.tar.gz
│   │   ├── backup-2026-01-19.cfg
│   │   └── ...
│   └── 02/
│       └── ...
├── 2025/
│   └── ...
├── logs/
│   └── backup.log (local only, not committed)
└── README.md
```

**Naming Convention:**
- **Archive:** `backup-YYYY-MM-DD.tar.gz` (Web UI restore compatible)
- **Text:** `backup-YYYY-MM-DD.cfg` (human-readable, Git diff friendly)

**Retention Policy:**
- Keep 30 days of backups in Git (files older than 30 days deleted from repo)
- Git history preserves all previous commits
- Local cleanup of old month folders after Git operations

### 3. Change Detection

**Git-Based Detection:**
- Compare new backup with previous commit using `git diff`
- Determine if configuration has changed
- Include change status in Git commit message
- No custom diff implementation needed (leverage Git)

**Commit Message Format:**
- **Changed:** `Backup 2026-01-20 - Configuration changed`
- **Unchanged:** `Backup 2026-01-20 - No changes`

**Benefits:**
- Use standard Git tools for viewing diffs
- Full change history in GitHub
- No duplicate diff logic required

### 4. Backup Verification

**Basic Validation:**
- Verify SSH connection succeeded
- Confirm files retrieved (non-empty, >0 bytes)
- Check .tar.gz archive is valid (not corrupted)
- Verify .cfg text file contains configuration commands
- Confirm files written to disk successfully

**No Advanced Validation:**
- File size comparison skipped (configuration can legitimately shrink)
- No syntax parsing (trust EdgeRouter to generate valid config)
- Focus on basic integrity checks only

### 5. Restoration Capability

**Manual Restore Only:**

The tool does NOT include automated restore functionality. Restoration is a manual process:

**Restore via Web UI (Recommended):**
1. Go to GitHub repository
2. Download desired `backup-YYYY-MM-DD.tar.gz` file
3. Open EdgeRouter Web UI (System > Configuration > Restore Backup)
4. Upload the .tar.gz file
5. Click Restore
6. EdgeRouter reboots with restored configuration

**Restore via CLI (Alternative):**
```bash
# Download .cfg file from GitHub
# SCP to EdgeRouter
scp backup-2026-01-20.cfg admin@192.168.1.1:/tmp/

# SSH to EdgeRouter
ssh admin@192.168.1.1
configure
load /tmp/backup-2026-01-20.cfg
compare  # Review changes before applying
commit
save
exit
```

**Why Manual:**
- Restore is infrequent (emergency only)
- Requires careful review before applying
- Reduces risk of automated mistakes

## Configuration File

**Format:** YAML (simple and readable)

**Example Configuration:**
```yaml
# EdgeRouter Backup Configuration

edgerouter:
  host: "192.168.1.1"
  port: 22
  username: "admin"
  ssh_key_path: "~/.ssh/id_rsa"  # or ~/.ssh/id_ed25519

github:
  repo_path: "~/edgerouter-backup"  # Local Git repo path
  remote: "git@github.com:username/edgerouter-backup.git"
  auto_push: true

backup:
  retention_days: 30
  formats:
    - tar.gz  # Web UI compatible
    - cfg     # Text format

notifications:
  macos_native: true
  on_success: true
  on_failure: true
  on_changes: true  # Include change status in notification

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "~/edgerouter-backup/logs/backup.log"
  max_size_mb: 10
  backup_count: 5
```

## Implementation Details

### Python Implementation Outline

**Required Libraries:**
- `paramiko` - SSH client for EdgeRouter connection
- `pyyaml` - Configuration file parsing
- `GitPython` - Git operations (or use subprocess)
- Standard library: `logging`, `pathlib`, `datetime`, `subprocess`

**For macOS Notifications:**
- Option 1: `subprocess` + `osascript` (no dependencies, native)
- Option 2: `pync` library (cleaner API, requires installation)

**Architecture: Simple Script**

Single main script with minimal helper functions. No complex class hierarchies.

**Main Flow:**
```python
1. Load configuration (config.yaml)
2. Setup logging
3. Parse command-line arguments (run, test, etc.)
4. Connect to EdgeRouter via SSH
5. Execute backup commands
6. Download backup files
7. Validate files (basic checks)
8. Save to Git repo with date-based paths
9. Check for changes (git diff)
10. Commit with appropriate message
11. Push to GitHub
12. Apply retention policy (delete old files)
13. Send macOS notification
14. Log completion
```

### Directory Structure
```
edgerouter-backup/           # This is also the Git repo
├── edgerouter-backup.py     # Main script (simple, ~300-400 lines)
├── config.yaml              # User configuration
├── config.example.yaml      # Example configuration
├── requirements.txt         # Python dependencies
├── logs/                    # Local logs (not committed to Git)
│   └── backup.log
├── 2026/                    # Backups organized by date
│   ├── 01/
│   │   ├── backup-2026-01-20.tar.gz
│   │   ├── backup-2026-01-20.cfg
│   │   └── ...
│   └── 02/
│       └── ...
├── README.md
└── .gitignore               # Ignore logs/, config.yaml
```

## Security Considerations

### Credential Management
- **SSH keys only** - No password storage required
- Use standard SSH keys (~/.ssh/id_rsa or ~/.ssh/id_ed25519)
- Never log SSH key paths or credentials
- Restrict config file permissions (chmod 600)

### Backup File Security
- Configurations contain sensitive data (VPN keys, passwords, firewall rules)
- **No encryption at rest** - Rely on file permissions and GitHub private repo
- Set appropriate file permissions on local files (600/700)
- Secure transmission via SSH to EdgeRouter and Git
- Use private GitHub repository (never public!)

### GitHub Repository Security
- Use SSH authentication for Git (git@github.com:user/repo.git)
- Never use HTTPS with tokens in config file
- Keep repository private
- Limit access to repository to authorized users only
- Enable two-factor authentication on GitHub account

### macOS Security
- Tool runs with user permissions (not root)
- Logs stored in user directory
- SSH keys protected by macOS keychain/file permissions

## Error Handling

### Common Scenarios

1. **SSH Connection Failure**
   - **No retry logic** - Alert immediately via macOS notification
   - Log detailed error message
   - Exit with error code

2. **Authentication Failure**
   - Clear error message indicating SSH key issue
   - Suggest checking SSH key permissions and EdgeRouter config
   - Alert via macOS notification
   - Exit immediately

3. **Network Timeout**
   - Timeout: 30 seconds for SSH operations
   - No retry - notify and exit
   - User can re-run manually if needed

4. **Disk Space Issues**
   - Check available disk space before backup
   - Alert if space low (<100MB free)
   - Suggest running retention cleanup
   - Exit without corrupting existing backups

5. **Configuration Retrieval Failure**
   - Empty or incomplete configuration
   - Validate output before saving
   - **Never overwrite good backup with bad one**
   - Alert and exit with error

6. **Git Push Failure**
   - If push fails, backup still saved locally
   - Alert user to check Git/GitHub connectivity
   - User can manually push later
   - Log git error output

### Error Philosophy
- **Fail fast** - Don't retry automatically
- **Alert immediately** - User needs to know right away
- **Preserve data** - Never delete or overwrite good backups on error
- **Clear messages** - Help user understand what went wrong

## Scheduling Options

### Manual Execution (Selected Approach)

**Daily Manual Run:**
User runs the tool manually each day (or as needed):
```bash
cd ~/edgerouter-backup
python3 edgerouter-backup.py run
```

**Why Manual:**
- Simple and predictable
- User aware when backup runs
- No daemon/service to manage
- Easy to skip if needed (travel, maintenance, etc.)
- Can add to daily routine or checklist

### Optional: Future Automation

If automatic scheduling desired later, options include:

**launchd (macOS Native):**
```xml
<!-- ~/Library/LaunchAgents/com.user.edgerouter-backup.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.edgerouter-backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>/Users/username/edgerouter-backup/edgerouter-backup.py</string>
    <string>run</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
</dict>
</plist>
```

**cron (Alternative):**
```cron
# Run daily at 2 AM
0 2 * * * cd ~/edgerouter-backup && /usr/local/bin/python3 edgerouter-backup.py run
```

## Command Line Interface

```bash
# Run backup (main command)
python3 edgerouter-backup.py run
# - Connects to EdgeRouter
# - Downloads configuration
# - Commits to Git
# - Pushes to GitHub
# - Sends macOS notification

# Test mode (dry-run, no files saved)
python3 edgerouter-backup.py test
# - Tests SSH connectivity
# - Retrieves configuration
# - Validates files
# - Shows what would be done
# - No Git operations

# Show status
python3 edgerouter-backup.py status
# - Shows last backup date/time
# - Shows GitHub sync status
# - Shows disk space usage
# - Shows retention policy status

# Cleanup old backups manually
python3 edgerouter-backup.py cleanup
# - Removes backups older than retention_days
# - Commits deletion to Git
# - Pushes to GitHub

# View help
python3 edgerouter-backup.py --help
python3 edgerouter-backup.py run --help
```

**Not Included:**
- No `restore` command (manual restore only)
- No `diff` command (use `git diff` or `git log -p`)
- No `daemon` mode (manual execution)
- No device selection (single device only)

## Monitoring & Logging

### Log Levels (INFO Selected)
- **INFO:** Backup started, completed, file saved, Git operations
- **WARNING:** Low disk space, Git push issues (still saved locally)
- **ERROR:** Backup failures, connection issues, validation failures

**Not Used:**
- DEBUG: Available but not default (too verbose for daily use)
- CRITICAL: Reserved for system errors

### Log Format (Standard INFO Level)
```
2026-01-20 09:15:01 [INFO] Starting backup for 192.168.1.1
2026-01-20 09:15:02 [INFO] SSH connection established
2026-01-20 09:15:03 [INFO] Configuration retrieved: .tar.gz (45,234 bytes), .cfg (32,123 bytes)
2026-01-20 09:15:03 [INFO] Files validated successfully
2026-01-20 09:15:03 [INFO] Saved to 2026/01/backup-2026-01-20.tar.gz
2026-01-20 09:15:03 [INFO] Configuration changed since last backup
2026-01-20 09:15:04 [INFO] Git commit: "Backup 2026-01-20 - Configuration changed"
2026-01-20 09:15:06 [INFO] Pushed to GitHub successfully
2026-01-20 09:15:06 [INFO] macOS notification sent
2026-01-20 09:15:06 [INFO] Backup completed in 5.2 seconds
```

### Log Storage
- **Location:** `~/edgerouter-backup/logs/backup.log`
- **Rotation:** 10 MB max, keep 5 backup files
- **Local only:** Logs NOT committed to Git repository
- **Excluded:** Logs directory in .gitignore

### macOS Notifications
All backup events generate macOS notification:
- **Success:** "EdgeRouter backup completed - Configuration changed"
- **Success (no change):** "EdgeRouter backup completed - No changes"
- **Failure:** "EdgeRouter backup failed - SSH connection error"

## Testing Plan

### Manual Testing Approach

Given the simple script architecture and single device, manual testing is appropriate:

**Initial Setup Testing:**
1. Test SSH connectivity to EdgeRouter
2. Verify SSH key authentication works
3. Test Git repository setup and GitHub access
4. Verify macOS notifications work

**Functional Testing:**
1. Run `test` command to verify dry-run mode
2. Run first `run` command and verify files created
3. Check Git commit created with correct message
4. Verify push to GitHub succeeded
5. Check macOS notification appeared
6. Review log file output

**Edge Case Testing:**
1. Disconnect network and verify error handling
2. Run backup twice same day (should update files)
3. Test with unchanged configuration
4. Fill disk to test low space warning
5. Test with invalid SSH key
6. Test Git push failure (disconnect from internet)

**Retention Testing:**
1. Create multiple backups over time
2. Run `cleanup` command
3. Verify old files deleted from repo
4. Check Git history still contains old commits

### Optional: Automated Tests

For future enhancement, basic tests could be added:
- Mock SSH connection tests
- File validation logic tests
- Git operation tests (using temporary repo)
- Date-based path generation tests

## Documentation Requirements

1. **README.md**
   - Overview and purpose
   - Prerequisites (Python 3.8+, SSH key, GitHub account)
   - Installation instructions (pip install, Git setup)
   - Quick start guide (5 minutes to first backup)
   - Configuration examples
   - Command reference (run, test, status, cleanup)
   - Troubleshooting common issues

2. **config.example.yaml**
   - Fully commented example configuration
   - Explanation of each setting
   - Security notes (private repo, SSH keys)

3. **Inline Code Comments**
   - Clear comments for complex operations
   - Explanation of EdgeOS-specific commands
   - Git workflow documentation

4. **Recovery Guide (in README)**
   - Web UI restore procedure
   - CLI restore procedure
   - When to restore from backups

## Success Criteria

- Successfully backup EdgeRouter 2.0+ configuration via SSH
- Generate both .tar.gz (Web UI compatible) and .cfg (text) formats
- Automatically commit and push to GitHub after each backup
- Send macOS notification for all backup events (success/failure)
- Maintain 30-day retention policy
- Test mode works without modifying any files
- Logs provide clear troubleshooting information
- Runs reliably on macOS with Python 3.8+
- Simple enough for daily manual execution
- Web UI restore works with generated .tar.gz files

## Future Enhancements (Out of Scope for v1)

### Potential Future Features
- **Automatic scheduling:** launchd integration for automatic daily backups
- **Multi-device support:** Backup multiple EdgeRouters from one tool
- **Restore automation:** Tool-assisted restore with safety checks
- **Built-in diff viewer:** Terminal-based diff display (though `git diff` works fine)
- **Web dashboard:** Simple web UI for viewing backup history and status
- **Other Ubiquiti devices:** Support UniFi, AirOS devices
- **Cloud storage options:** Additional backends (S3, Backblaze B2)
- **Email notifications:** Alternative to macOS notifications
- **Configuration validation:** Syntax check before restore
- **Backup verification:** Periodic restore tests to verify backups are valid

## Dependencies

### Runtime Requirements
- **Python:** 3.8+ (pre-installed on macOS 10.15+, but use `python3` command)
- **pip packages:**
  - `paramiko` - SSH client
  - `pyyaml` - Configuration parsing
  - `GitPython` - Git operations (or use subprocess)
  - Optional: `pync` for macOS notifications (or use `osascript`)
- **System requirements:**
  - macOS 10.15+ (Catalina or later)
  - ~100 MB disk space (depends on config size and retention)
  - Network access to EdgeRouter and GitHub

### EdgeRouter Requirements
- **EdgeOS:** 2.0.x (tested version)
- **SSH:** Enabled on port 22 (standard)
- **User account:** Admin access (for configuration backup)
- **Network:** Accessible from macOS machine on local network
- **SSH key:** Added to EdgeRouter authorized_keys

### GitHub Requirements
- GitHub account (free tier sufficient)
- Private repository (for security)
- SSH key added to GitHub account
- Network access to github.com

## Questions Answered from Interview

1. ✅ **Backups encrypted at rest?** No - rely on file permissions and private GitHub repo
2. ✅ **Preferred notification method?** macOS native notifications
3. ✅ **Remote storage in v1?** Yes - GitHub (Git-based)
4. ✅ **Windows support?** No - macOS only for v1
5. ✅ **Restoration automated?** No - manual restore only
6. ✅ **Git integration desired?** Yes - primary storage mechanism
7. ✅ **Scheduling approach?** Manual execution, no automatic scheduling
8. ✅ **Number of devices?** Single device
9. ✅ **Authentication method?** SSH key only (no password)
10. ✅ **Implementation style?** Simple Python script (not modular)

## Getting Started (Implementation Steps)

### Phase 1: Core Functionality
1. Create GitHub repository (private)
2. Set up Python script structure and CLI argument parsing
3. Implement configuration file loading (YAML)
4. Implement SSH connection to EdgeRouter
5. Implement configuration download (both .tar.gz and .cfg)
6. Implement basic file validation

### Phase 2: Git Integration
7. Implement date-based file organization
8. Implement Git commit with change detection
9. Implement Git push to GitHub
10. Implement retention policy (30-day cleanup)

### Phase 3: User Experience
11. Implement macOS notifications
12. Implement logging system
13. Implement test/dry-run mode
14. Implement status command
15. Create README and documentation

### Phase 4: Polish
16. Error handling and edge cases
17. Manual testing against real EdgeRouter
18. Create config.example.yaml
19. Final documentation review
20. Initial release (v1.0)

## Example Output

**Successful Backup:**
```
$ python3 edgerouter-backup.py run

EdgeRouter Backup Tool v1.0

[09:15:01] Starting backup for 192.168.1.1
[09:15:02] ✓ SSH connection established
[09:15:03] ✓ Configuration retrieved
           - backup-2026-01-20.tar.gz (45.2 KB)
           - backup-2026-01-20.cfg (32.1 KB)
[09:15:03] ✓ Files validated
[09:15:03] ✓ Saved to 2026/01/
[09:15:03] ⚠ Configuration changed since last backup
[09:15:04] ✓ Git commit created
[09:15:06] ✓ Pushed to GitHub
[09:15:06] ✓ macOS notification sent

Backup completed successfully in 5.2 seconds
```

**Test Mode:**
```
$ python3 edgerouter-backup.py test

EdgeRouter Backup Tool v1.0 - TEST MODE

[09:20:01] Testing SSH connection to 192.168.1.1...
[09:20:02] ✓ SSH connection successful
[09:20:02] ✓ Authentication successful (SSH key)
[09:20:03] ✓ Configuration retrieval successful
           - tar.gz: 45,234 bytes
           - cfg: 32,123 bytes
[09:20:03] ✓ Files would be valid
[09:20:03] ✓ GitHub remote accessible

Test completed successfully - ready for backup
(No files were saved or committed)
```

**Error Example:**
```
$ python3 edgerouter-backup.py run

EdgeRouter Backup Tool v1.0

[09:25:01] Starting backup for 192.168.1.1
[09:25:01] ✗ SSH connection failed: Connection timed out

ERROR: Unable to connect to EdgeRouter
  - Check network connectivity
  - Verify EdgeRouter is powered on
  - Confirm IP address: 192.168.1.1

macOS notification: "EdgeRouter backup failed - Connection timeout"
```

## References

- [EdgeOS User Guide](https://dl.ui.com/guides/edgemax/EdgeOS_UG.pdf)
- [EdgeOS CLI Command Reference](https://help.ui.com/hc/en-us/articles/204960094)
- [EdgeRouter Backup and Restore Guide](https://help.ui.com/hc/en-us/articles/360008355073)
- [Paramiko Documentation](https://www.paramiko.org/)
- [GitPython Documentation](https://gitpython.readthedocs.io/)
- [macOS Launch Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)

---

## Summary

This plan defines a **simple, focused Python tool** for backing up a single EdgeRouter to GitHub:

**Key Decisions:**
- ✅ Python script (simple, not modular)
- ✅ macOS only
- ✅ Single EdgeRouter device
- ✅ SSH key authentication
- ✅ GitHub storage with auto-push
- ✅ Both .tar.gz (Web UI) and .cfg (text) formats
- ✅ Manual daily execution
- ✅ macOS native notifications
- ✅ No encryption at rest
- ✅ 30-day retention
- ✅ No automatic restore
- ✅ Fail-fast error handling

**Estimated Scope:**
- ~300-400 lines of Python
- 4 commands: run, test, status, cleanup
- Minimal dependencies (paramiko, pyyaml, GitPython)
- Simple manual testing
- Ready for daily use

**Next Steps:**
1. Review and approve this plan
2. Set up GitHub repository
3. Begin Phase 1 implementation
4. Iterate based on testing with real EdgeRouter
