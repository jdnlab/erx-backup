# EdgeRouter Configuration Backup Tool

Automated backup tool for Ubiquiti EdgeRouter configurations with GitHub version control and Web UI-compatible restore format.

## Features

- 🔄 Backs up EdgeRouter configuration to GitHub automatically
- 📦 Generates both Web UI-compatible (.tar.gz) and human-readable (.cfg) formats
- 🔍 Git-based version control with full change history
- 🍎 Native macOS notifications
- 🔐 SSH key authentication (no password storage)
- 📅 Date-organized backups with configurable retention
- ✅ Test mode to verify connectivity
- 🚀 Simple manual execution - no daemon required

## Prerequisites

- **macOS** 10.15+ (Catalina or later)
- **Python 3.8+** (pre-installed on modern macOS)
- **EdgeRouter** with EdgeOS 2.0+
- **GitHub account** (free tier sufficient)
- **SSH access** to your EdgeRouter
- **~100 MB** disk space (depends on config size and retention)

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Install Python dependencies
pip3 install -r requirements.txt
```

### 2. Set Up SSH Key for EdgeRouter

If you don't already have an SSH key on your EdgeRouter:

```bash
# On your Mac, display your public key
cat ~/.ssh/id_rsa.pub
# or
cat ~/.ssh/id_ed25519.pub

# SSH to your EdgeRouter
ssh admin@192.168.1.1

# On EdgeRouter, add your public key
configure
set system login user admin authentication public-keys mykey type ssh-rsa
set system login user admin authentication public-keys mykey key "AAAAB3Nza..."
commit
save
exit
```

Test SSH key authentication:
```bash
ssh -i ~/.ssh/id_rsa admin@192.168.1.1
```

### 3. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `edgerouter-backup`
3. **Important: Make it PRIVATE** (configurations contain sensitive data)
4. Create repository
5. Copy the SSH URL: `git@github.com:yourusername/edgerouter-backup.git`

### 4. Configure the Tool

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

Update these settings:
- `edgerouter.host`: Your EdgeRouter IP address
- `edgerouter.username`: Your EdgeRouter username (typically `admin`)
- `edgerouter.ssh_key_path`: Path to your SSH key
- `github.remote`: Your GitHub repository SSH URL
- `github.repo_path`: Where to store backups locally (e.g., `~/edgerouter-backup`)

### 5. Test the Connection

```bash
python3 edgerouter-backup.py test
```

This will verify:
- SSH connection to EdgeRouter
- Configuration retrieval
- File validation
- GitHub connectivity

### 6. Run Your First Backup

```bash
python3 edgerouter-backup.py run
```

You should see:
- ✓ Connection established
- ✓ Configuration retrieved
- ✓ Files validated
- ✓ Git commit created
- ✓ Pushed to GitHub
- macOS notification

Check your GitHub repository - you should see the backup files!

## Usage

### Run Backup

```bash
python3 edgerouter-backup.py run
```

Backs up your EdgeRouter configuration:
1. Connects via SSH
2. Downloads `.tar.gz` (Web UI compatible) and `.cfg` (text)
3. Validates files
4. Commits to local Git repository
5. Pushes to GitHub
6. Sends macOS notification
7. Logs all operations

### Test Mode (Dry-Run)

```bash
python3 edgerouter-backup.py test
```

Tests everything without saving files:
- Verifies SSH connectivity
- Tests configuration download
- Validates files
- Shows what would be done
- No Git operations performed

### Check Status

```bash
python3 edgerouter-backup.py status
```

Shows:
- Last backup date/time
- Git commit message
- Disk space available
- Total number of backups
- Retention policy

### Cleanup Old Backups

```bash
python3 edgerouter-backup.py cleanup
```

Manually removes backups older than retention period (30 days by default).

## Daily Backup Routine

Run the backup daily:

```bash
cd ~/edgerouter-backup
python3 edgerouter-backup.py run
```

**Optional:** Add to your daily routine with a reminder, or set up automatic scheduling (see below).

## Repository Structure

Backups are organized by date in your GitHub repository:

```
edgerouter-backup/
├── 2026/
│   ├── 01/
│   │   ├── backup-2026-01-20.tar.gz  # Web UI restore
│   │   ├── backup-2026-01-20.cfg     # Human-readable
│   │   ├── backup-2026-01-19.tar.gz
│   │   ├── backup-2026-01-19.cfg
│   │   └── ...
│   └── 02/
│       └── ...
├── logs/
│   └── backup.log (local only, not in Git)
├── README.md
└── .gitignore
```

## Viewing Configuration History

Use standard Git commands to view history:

```bash
cd ~/edgerouter-backup

# View commit history
git log --oneline

# See what changed in last backup
git show HEAD

# Compare two backups
git diff HEAD~1 HEAD -- 2026/01/backup-2026-01-20.cfg

# View configuration from specific date
git show HEAD~5:2026/01/backup-2026-01-15.cfg
```

## Restoring from Backup

### Method 1: Web UI (Recommended)

1. Go to your GitHub repository
2. Download the desired `backup-YYYY-MM-DD.tar.gz` file
3. Open EdgeRouter Web UI
4. Go to **System** → **Configuration Management**
5. Click **Restore Backup**
6. Upload the `.tar.gz` file
7. Click **Restore**
8. EdgeRouter will reboot with restored configuration

### Method 2: CLI

```bash
# Download .cfg from GitHub
cd ~/edgerouter-backup
scp 2026/01/backup-2026-01-20.cfg admin@192.168.1.1:/tmp/

# SSH to EdgeRouter
ssh admin@192.168.1.1

# On EdgeRouter
configure
load /tmp/backup-2026-01-20.cfg
compare  # Review changes before committing
commit
save
exit
```

## Optional: Automatic Scheduling

### Using launchd (macOS Native)

Create `~/Library/LaunchAgents/com.user.edgerouter-backup.plist`:

```xml
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
    <string>/Users/yourusername/edgerouter-backup/edgerouter-backup.py</string>
    <string>run</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/yourusername/edgerouter-backup/logs/launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/yourusername/edgerouter-backup/logs/launchd-error.log</string>
</dict>
</plist>
```

Load the agent:
```bash
launchctl load ~/Library/LaunchAgents/com.user.edgerouter-backup.plist
```

### Using cron

```bash
crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * cd ~/edgerouter-backup && /usr/local/bin/python3 edgerouter-backup.py run
```

## Configuration Reference

### EdgeRouter Settings

```yaml
edgerouter:
  host: "192.168.1.1"        # EdgeRouter IP or hostname
  port: 22                    # SSH port
  username: "admin"           # SSH username
  ssh_key_path: "~/.ssh/id_rsa"  # Path to SSH private key
```

### GitHub Settings

```yaml
github:
  repo_path: "~/edgerouter-backup"  # Local repository path
  remote: "git@github.com:user/edgerouter-backup.git"  # GitHub SSH URL
  auto_push: true  # Automatically push after commit
```

### Backup Settings

```yaml
backup:
  retention_days: 30  # Keep backups for 30 days (Git history preserved)
  formats:
    - tar.gz  # Web UI compatible archive
    - cfg     # Plain text for diff viewing
```

### Notification Settings

```yaml
notifications:
  macos_native: true  # Use macOS notifications
  on_success: true    # Notify on successful backup
  on_failure: true    # Notify on backup failure
  on_changes: true    # Include change status in notification
```

### Logging Settings

```yaml
logging:
  level: "INFO"                      # DEBUG, INFO, WARNING, ERROR
  file: "logs/backup.log"            # Log file path
  max_size_mb: 10                    # Max log size before rotation
  backup_count: 5                    # Number of rotated logs to keep
```

## Troubleshooting

### SSH Connection Failed

**Error:** `SSH connection failed: Connection timed out`

**Solutions:**
- Verify EdgeRouter is powered on and accessible
- Check IP address in `config.yaml`
- Test connection: `ping 192.168.1.1`
- Verify firewall isn't blocking SSH

### SSH Authentication Failed

**Error:** `SSH authentication failed`

**Solutions:**
- Verify SSH key is correct: `ls -l ~/.ssh/id_rsa`
- Check key permissions: `chmod 600 ~/.ssh/id_rsa`
- Test SSH manually: `ssh -i ~/.ssh/id_rsa admin@192.168.1.1`
- Verify public key is added to EdgeRouter authorized_keys

### Git Push Failed

**Error:** `Git push failed`

**Solutions:**
- Backup is still saved locally
- Check internet connection
- Verify GitHub SSH key: `ssh -T git@github.com`
- Manually push later: `cd ~/edgerouter-backup && git push`
- Check GitHub repository exists and is accessible

### File Validation Failed

**Error:** `Validation failed: cfg file doesn't appear to contain valid EdgeOS configuration`

**Solutions:**
- EdgeRouter may be in a bad state
- Try rebooting EdgeRouter
- SSH manually and run: `show configuration commands`
- Check EdgeOS firmware version (2.0+ required)

### Low Disk Space

**Warning:** `Low disk space: X MB available`

**Solutions:**
- Run cleanup: `python3 edgerouter-backup.py cleanup`
- Reduce retention period in `config.yaml`
- Free up disk space on your Mac
- Move repository to external drive

### macOS Notifications Not Showing

**Solutions:**
- Check System Preferences → Notifications
- Enable notifications for Terminal/Script Editor
- Test notification: `osascript -e 'display notification "test"'`
- Check config: `macos_native: true`

## Security Notes

- **Keep repository PRIVATE** - configurations contain sensitive data
- **Use SSH keys** - never store passwords in config
- **Protect config.yaml** - contains network topology information
- **Limit GitHub access** - only authorized users should access backups
- **Enable 2FA** - on your GitHub account
- **Review permissions** - `chmod 600 config.yaml`

## File Permissions

```bash
chmod 600 config.yaml           # Configuration file
chmod 700 ~/edgerouter-backup   # Repository directory
chmod 600 ~/.ssh/id_rsa         # SSH private key
```

## What's Backed Up?

The backup includes your complete EdgeRouter configuration:
- All interface settings
- Firewall rules
- NAT rules
- DHCP settings
- DNS settings
- VPN configuration
- Port forwarding
- User accounts
- System settings

## What's NOT Backed Up?

- EdgeOS firmware/system files
- Traffic statistics
- Log files
- Dynamic state (routing tables, connections)

## Version History

### v1.0.0 (2026-01-20)
- Initial release
- EdgeOS 2.0+ support
- macOS native notifications
- GitHub version control
- Web UI-compatible restore format
- Test mode
- 30-day retention policy

## License

MIT License - See LICENSE file

## Support

For issues or questions:
- Check troubleshooting section above
- Review logs: `cat ~/edgerouter-backup/logs/backup.log`
- Test connectivity: `python3 edgerouter-backup.py test`
- Check GitHub repository for updates

## Credits

Built with:
- [Paramiko](https://www.paramiko.org/) - SSH client
- [GitPython](https://gitpython.readthedocs.io/) - Git integration
- [PyYAML](https://pyyaml.org/) - Configuration parsing
