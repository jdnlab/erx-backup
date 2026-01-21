#!/usr/bin/env python3
"""
EdgeRouter Configuration Backup Tool
Backs up EdgeRouter configuration to GitHub with version control
"""

import argparse
import logging
import os
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler

import paramiko
import yaml
from git import Repo, GitCommandError


VERSION = "1.0.0"


def setup_logging(config, test_mode=False):
    """Setup logging with rotation"""
    log_level = getattr(logging, config['logging']['level'].upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    repo_path = Path(config['github']['repo_path']).expanduser()
    log_file = repo_path / config['logging']['file']
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with rotation (only if not test mode)
    if not test_mode:
        max_bytes = config['logging']['max_size_mb'] * 1024 * 1024
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=config['logging']['backup_count']
        )
        file_handler.setLevel(log_level)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def load_config(config_path='config.yaml'):
    """Load configuration from YAML file"""
    config_file = Path(config_path).expanduser()

    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}")
        print(f"Please copy config.example.yaml to config.yaml and customize it")
        sys.exit(1)

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def send_macos_notification(title, message, config):
    """Send macOS native notification"""
    if not config['notifications']['macos_native']:
        return

    try:
        # Use osascript for native macOS notifications
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        logging.info("macOS notification sent")
    except Exception as e:
        logging.warning(f"Failed to send notification: {e}")


def check_disk_space(path, min_mb=100):
    """Check available disk space"""
    stat = os.statvfs(path)
    available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

    if available_mb < min_mb:
        logging.warning(f"Low disk space: {available_mb:.1f} MB available")
        return False

    return True


def connect_ssh(config):
    """Establish SSH connection to EdgeRouter"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_key_path = Path(config['edgerouter']['ssh_key_path']).expanduser()

        logging.info(f"Connecting to {config['edgerouter']['host']}...")
        ssh.connect(
            hostname=config['edgerouter']['host'],
            port=config['edgerouter']['port'],
            username=config['edgerouter']['username'],
            key_filename=str(ssh_key_path),
            timeout=30
        )

        logging.info("✓ SSH connection established")
        return ssh

    except paramiko.AuthenticationException:
        logging.error("SSH authentication failed")
        logging.error(f"  - Check SSH key: {ssh_key_path}")
        logging.error(f"  - Verify key is added to EdgeRouter authorized_keys")
        raise
    except paramiko.SSHException as e:
        logging.error(f"SSH error: {e}")
        raise
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        logging.error(f"  - Check network connectivity")
        logging.error(f"  - Verify EdgeRouter is powered on")
        logging.error(f"  - Confirm IP address: {config['edgerouter']['host']}")
        raise


def download_config(ssh, config, test_mode=False):
    """Download configuration from EdgeRouter in both formats"""

    backup_files = {}

    try:
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp()

        # Get .tar.gz backup (Web UI compatible)
        if 'tar.gz' in config['backup']['formats']:
            logging.info("Retrieving configuration archive...")

            # Generate backup on EdgeRouter
            stdin, stdout, stderr = ssh.exec_command(f"gzip -zcf config.boot.tar.gz /config")
            stdout.channel.recv_exit_status()  # Wait for completion

            # Download the backup file
            sftp = ssh.open_sftp()
            local_tar = os.path.join(temp_dir, 'config.boot.tar.gz')
            sftp.get('/config/config.boot.tar.gz', local_tar)
            sftp.close()

            tar_size = os.path.getsize(local_tar)
            logging.info(f"  - tar.gz: {tar_size:,} bytes")
            backup_files['tar.gz'] = local_tar

        # Get plain text configuration (.cfg)
        # if 'cfg' in config['backup']['formats']:
        #     logging.info("Retrieving text configuration...")

        #     stdin, stdout, stderr = ssh.exec_command('show configuration commands')
        #     cfg_content = stdout.read().decode('utf-8')

        #     print(cfg_content)

        #     local_cfg = os.path.join(temp_dir, 'config.cfg')
        #     with open(local_cfg, 'w') as f:
        #         f.write(cfg_content)

        #     cfg_size = os.path.getsize(local_cfg)
        #     logging.info(f"  - cfg: {cfg_size:,} bytes")
        #     backup_files['cfg'] = local_cfg

        # logging.info("✓ Configuration retrieved")
        return backup_files, temp_dir

    except Exception as e:
        logging.error(f"Failed to download configuration: {e}")
        raise


def validate_backup_files(backup_files):
    """Perform basic validation on backup files"""
    try:
        for fmt, filepath in backup_files.items():
            if not os.path.exists(filepath):
                raise ValueError(f"{fmt} file not found")

            size = os.path.getsize(filepath)
            if size == 0:
                raise ValueError(f"{fmt} file is empty")

            # Validate tar.gz can be opened
            if fmt == 'tar.gz':
                with tarfile.open(filepath, 'r:gz') as tar:
                    pass  # Just verify it's a valid tar.gz

            # Validate cfg contains configuration commands
            if fmt == 'cfg':
                with open(filepath, 'r') as f:
                    content = f.read()
                    if 'set ' not in content and 'delete ' not in content:
                        raise ValueError("cfg file doesn't appear to contain valid EdgeOS configuration")

        logging.info("✓ Files validated")
        return True

    except Exception as e:
        logging.error(f"Validation failed: {e}")
        return False


def save_to_repo(backup_files, config, test_mode=False):
    """Save backup files to Git repository with date-based organization"""

    repo_path = Path(config['github']['repo_path']).expanduser()

    # Create date-based path (YYYY/MM/)
    now = datetime.now()
    date_path = repo_path / str(now.year) / f"{now.month:02d}"
    date_path.mkdir(parents=True, exist_ok=True)

    # Date string for filenames
    date_str = now.strftime('%Y-%m-%d')

    saved_files = []

    for fmt, temp_file in backup_files.items():
        dest_file = date_path / f"backup-{date_str}.{fmt}"

        # Copy file to destination
        import shutil
        shutil.copy2(temp_file, dest_file)

        saved_files.append(str(dest_file.relative_to(repo_path)))
        logging.info(f"Saved: {dest_file.relative_to(repo_path)}")

    logging.info(f"✓ Saved to {now.year}/{now.month:02d}/")

    return saved_files


def check_for_changes(repo):
    """Check if configuration has changed using git diff"""
    try:
        # Check if there are any changes staged or unstaged
        if repo.is_dirty(untracked_files=True):
            return True
        return False
    except Exception as e:
        logging.warning(f"Could not determine if files changed: {e}")
        return True  # Assume changed to be safe


def git_commit_and_push(config, changed, test_mode=False):
    """Commit changes to Git and push to GitHub"""

    repo_path = Path(config['github']['repo_path']).expanduser()

    try:
        # Initialize or open repository
        if not (repo_path / '.git').exists():
            logging.info("Initializing Git repository...")
            repo = Repo.init(repo_path)

            # Add remote
            remote_url = config['github']['remote']
            try:
                repo.create_remote('origin', remote_url)
            except:
                pass  # Remote might already exist

            logging.info("✓ Git repository initialized")
        else:
            repo = Repo(repo_path)

        if test_mode:
            return

        # Add backup files
        repo.git.add('.')

        # Check if there are actually changes to commit
        if not check_for_changes(repo):
            logging.info("No changes detected in files")
            changed = False

        # Create commit message
        date_str = datetime.now().strftime('%Y-%m-%d')
        if changed:
            commit_msg = f"Backup {date_str} - Configuration changed"
            logging.info("⚠ Configuration changed since last backup")
        else:
            commit_msg = f"Backup {date_str} - No changes"
            logging.info("Configuration unchanged")

        # Commit
        repo.index.commit(commit_msg)
        logging.info("✓ Git commit created")

        # Push to GitHub
        if config['github']['auto_push']:
            logging.info("Pushing to GitHub...")
            origin = repo.remote('origin')
            origin.push()
            logging.info("✓ Pushed to GitHub successfully")

        return changed

    except GitCommandError as e:
        logging.warning(f"Git push failed: {e}")
        logging.warning("  - Backup saved locally")
        logging.warning("  - Check GitHub connectivity")
        logging.warning("  - You can manually push later: git push")
        return changed
    except Exception as e:
        logging.error(f"Git operation failed: {e}")
        raise


def cleanup_old_backups(config, test_mode=False):
    """Remove backups older than retention period"""

    repo_path = Path(config['github']['repo_path']).expanduser()
    retention_days = config['backup']['retention_days']
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    removed_count = 0

    try:
        # Walk through year/month directories
        for year_dir in repo_path.glob('[0-9][0-9][0-9][0-9]'):
            if not year_dir.is_dir():
                continue

            for month_dir in year_dir.glob('[0-9][0-9]'):
                if not month_dir.is_dir():
                    continue

                # Check each backup file
                for backup_file in month_dir.glob('backup-*.{tar.gz,cfg}'):
                    try:
                        # Extract date from filename: backup-2026-01-20.tar.gz
                        date_str = backup_file.stem.split('backup-')[1].rsplit('.', 1)[0]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')

                        if file_date < cutoff_date:
                            if not test_mode:
                                backup_file.unlink()
                                logging.info(f"Removed old backup: {backup_file.relative_to(repo_path)}")
                            else:
                                logging.info(f"Would remove: {backup_file.relative_to(repo_path)}")
                            removed_count += 1
                    except Exception as e:
                        logging.warning(f"Could not process {backup_file}: {e}")

        if removed_count > 0:
            logging.info(f"✓ Retention policy applied (removed {removed_count} old files)")

        return removed_count

    except Exception as e:
        logging.warning(f"Cleanup failed: {e}")
        return 0


def run_backup(config, test_mode=False):
    """Main backup function"""

    start_time = datetime.now()
    ssh = None
    temp_dir = None
    changed = True

    try:
        # Check disk space
        repo_path = Path(config['github']['repo_path']).expanduser()
        repo_path.mkdir(parents=True, exist_ok=True)

        if not check_disk_space(repo_path):
            raise Exception("Insufficient disk space (<100MB available)")

        # Connect to EdgeRouter
        logging.info(f"Starting backup for {config['edgerouter']['host']}")
        ssh = connect_ssh(config)

        # Download configuration
        backup_files, temp_dir = download_config(ssh, config, test_mode)

        # Validate files
        if not validate_backup_files(backup_files):
            raise Exception("Backup validation failed")

        if test_mode:
            logging.info("✓ Test completed successfully - ready for backup")
            logging.info("(No files were saved or committed)")
            return True

        # Save to repository
        saved_files = save_to_repo(backup_files, config, test_mode)

        # Git commit and push
        changed = git_commit_and_push(config, changed, test_mode)

        # Cleanup old backups
        cleanup_old_backups(config, test_mode)

        # Success notification
        duration = (datetime.now() - start_time).total_seconds()
        logging.info(f"Backup completed successfully in {duration:.1f} seconds")

        if config['notifications']['on_success']:
            if config['notifications']['on_changes'] and changed:
                msg = "EdgeRouter backup completed - Configuration changed"
            else:
                msg = "EdgeRouter backup completed - No changes"
            send_macos_notification("Backup Successful", msg, config)

        return True

    except Exception as e:
        logging.error(f"Backup failed: {e}")

        if config['notifications']['on_failure']:
            send_macos_notification("Backup Failed", str(e), config)

        return False

    finally:
        # Cleanup
        if ssh:
            ssh.close()
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def show_status(config):
    """Show backup status"""

    repo_path = Path(config['github']['repo_path']).expanduser()

    print("\nEdgeRouter Backup Status")
    print("=" * 50)

    # Repository info
    print(f"Repository: {repo_path}")
    if (repo_path / '.git').exists():
        repo = Repo(repo_path)
        print(f"Git remote: {config['github']['remote']}")

        # Last commit info
        try:
            last_commit = repo.head.commit
            print(f"Last backup: {last_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Commit message: {last_commit.message.strip()}")
        except:
            print("Last backup: No commits yet")
    else:
        print("Git status: Not initialized")

    # Disk space
    stat = os.statvfs(repo_path)
    available_gb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024 * 1024)
    print(f"Disk space available: {available_gb:.2f} GB")

    # Backup count
    backup_count = len(list(repo_path.glob('[0-9]*/[0-9]*/backup-*.tar.gz')))
    print(f"Total backups: {backup_count}")

    # Retention policy
    print(f"Retention policy: {config['backup']['retention_days']} days")

    print()


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description='EdgeRouter Configuration Backup Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run backup')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test mode (dry-run)')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show backup status')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old backups')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    config = load_config()

    # Setup logging
    test_mode = (args.command == 'test')
    logger = setup_logging(config, test_mode)

    # Print header
    print(f"\nEdgeRouter Backup Tool v{VERSION}")
    if test_mode:
        print("TEST MODE - No files will be saved\n")
    else:
        print()

    # Execute command
    if args.command == 'run':
        success = run_backup(config, test_mode=False)
        sys.exit(0 if success else 1)

    elif args.command == 'test':
        success = run_backup(config, test_mode=True)
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        show_status(config)
        sys.exit(0)

    elif args.command == 'cleanup':
        logger = setup_logging(config)
        repo_path = Path(config['github']['repo_path']).expanduser()

        if not repo_path.exists():
            print("Error: Repository not found. Run 'backup run' first.")
            sys.exit(1)

        logging.info(f"Cleaning up backups older than {config['backup']['retention_days']} days...")
        removed = cleanup_old_backups(config, test_mode=False)

        if removed > 0:
            # Commit and push the deletions
            try:
                repo = Repo(repo_path)
                repo.git.add(A=True)
                repo.index.commit(f"Cleanup: Removed {removed} old backup files")

                if config['github']['auto_push']:
                    origin = repo.remote('origin')
                    origin.push()
                    logging.info("✓ Changes pushed to GitHub")
            except Exception as e:
                logging.warning(f"Could not commit cleanup: {e}")

        sys.exit(0)


if __name__ == '__main__':
    main()
