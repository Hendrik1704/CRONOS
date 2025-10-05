#!/usr/bin/env python3
"""
Real-time memory monitoring for CRONOS simulations.
Run this alongside your simulations to monitor memory usage.
"""

import psutil
import time
import argparse
from datetime import datetime


def monitor_memory(interval=5, threshold=80, log_file=None):
    """Monitor system and process memory usage in real-time.

    Continuously monitors system memory usage and identifies high-memory processes.
    Displays colored status indicators and warnings when thresholds are exceeded.
    Optionally logs data to a CSV file for analysis.

    Args:
        interval (int, optional): Monitoring interval in seconds. Defaults to 5.
        threshold (int, optional): Memory usage percentage threshold for warnings.
            Defaults to 80.
        log_file (str, optional): Path to CSV file for logging memory data.
            If None, no logging is performed. Defaults to None.

    Returns:
        None: Function runs until interrupted with Ctrl+C.

    Example:
        >>> monitor_memory(interval=2, threshold=90, log_file="memory.csv")
        🔍 Starting memory monitoring...
    """

    print(
        f"🔍 Starting memory monitoring (interval: {interval}s, threshold: {threshold}%)"
    )
    if log_file:
        print(f"📝 Logging to: {log_file}")
    print("Press Ctrl+C to stop\n")

    log_handle = None
    if log_file:
        log_handle = open(log_file, "w")
        log_handle.write(
            "timestamp,system_percent,system_available_gb,process_count,high_memory_processes\n"
        )

    try:
        while True:
            # Get system memory info
            memory = psutil.virtual_memory()

            # Find processes using significant memory
            high_mem_processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    if (
                        proc.info["memory_percent"] > 5
                    ):  # More than 5% of system memory
                        high_mem_processes.append(
                            f"{proc.info['name']}({proc.info['pid']}):{proc.info['memory_percent']:.1f}%"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Format timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Display current status
            status_color = (
                "🔴"
                if memory.percent > threshold
                else "🟢" if memory.percent < 50 else "🟡"
            )
            print(
                f"{status_color} {timestamp} | Memory: {memory.percent:5.1f}% | "
                f"Available: {memory.available/1024/1024/1024:5.1f}GB | "
                f"High-mem processes: {len(high_mem_processes)}"
            )

            # Show warning if threshold exceeded
            if memory.percent > threshold:
                print(f"  ⚠️  WARNING: Memory usage above {threshold}%!")
                if high_mem_processes:
                    print(
                        f"  📊 Top memory consumers: {', '.join(high_mem_processes[:3])}"
                    )

            # Log to file if specified
            if log_handle:
                log_handle.write(
                    f"{timestamp},{memory.percent},{memory.available/1024/1024/1024},"
                    f"{len(high_mem_processes)},\"{';'.join(high_mem_processes[:5])}\"\n"
                )
                log_handle.flush()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    finally:
        if log_handle:
            log_handle.close()
            print(f"📝 Log saved to {log_file}")


def check_cronos_processes():
    """Identify and analyze CRONOS-related processes and their memory consumption.

    Searches for both CRONOS Python processes (framework) and external physics
    code processes (MUSIC, SMASH, KoMPoST, iSS). Provides detailed memory usage
    statistics and identifies high-memory consumers.

    The function categorizes processes into two types:
    - Python processes: CRONOS framework components
    - External processes: Physics simulation executables

    Returns:
        None: Prints process information to stdout.

    Example:
        >>> check_cronos_processes()
        🔍 Checking for CRONOS processes...
        Found 2 Python processes and 1 external processes:
        Total memory usage: 2048.5 MB (2.0 GB)
    """
    print("🔍 Checking for CRONOS processes...\n")

    cronos_processes = []
    external_processes = []
    total_memory = 0

    for proc in psutil.process_iter(
        [
            "pid",
            "ppid",
            "name",
            "cmdline",
            "memory_info",
            "memory_percent",
            "create_time",
        ]
    ):
        try:
            cmdline = (
                " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
            )
            name = proc.info["name"].lower()

            memory_mb = proc.info["memory_info"].rss / 1024 / 1024

            # Look for CRONOS Python processes
            if any(
                keyword in cmdline.lower()
                for keyword in ["cronos", "run_simulations"]
            ):
                cronos_processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "memory_mb": memory_mb,
                        "memory_percent": proc.info["memory_percent"],
                        "cmdline": cmdline,
                        "type": "python",
                    }
                )
                total_memory += memory_mb

            # Look for external physics codes
            elif any(
                keyword in name
                for keyword in ["music", "smash", "kompost", "iss"]
            ) or any(
                keyword in cmdline.lower()
                for keyword in ["musichydro", "smash", "kompost.exe", "iss.exe"]
            ):
                external_processes.append(
                    {
                        "pid": proc.info["pid"],
                        "ppid": proc.info["ppid"],
                        "name": proc.info["name"],
                        "memory_mb": memory_mb,
                        "memory_percent": proc.info["memory_percent"],
                        "cmdline": cmdline,
                        "type": "external",
                    }
                )
                total_memory += memory_mb

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    all_processes = cronos_processes + external_processes

    if all_processes:
        print(
            f"Found {len(cronos_processes)} Python processes and {len(external_processes)} external processes:"
        )
        print(
            f"Total memory usage: {total_memory:.1f} MB ({total_memory/1024:.1f} GB)\n"
        )

        if cronos_processes:
            print("📋 CRONOS Python Processes:")
            for proc in sorted(
                cronos_processes, key=lambda x: x["memory_mb"], reverse=True
            ):
                print(
                    f"  PID {proc['pid']:6} | {proc['name']:15} | "
                    f"{proc['memory_mb']:8.1f} MB ({proc['memory_percent']:4.1f}%)"
                )
            print()

        if external_processes:
            print("⚡ External Physics Codes:")
            for proc in sorted(
                external_processes, key=lambda x: x["memory_mb"], reverse=True
            ):
                status_icon = "🔥" if proc["memory_mb"] > 8000 else "⚡"
                print(
                    f"  {status_icon} PID {proc['pid']:6} | {proc['name']:15} | "
                    f"{proc['memory_mb']:8.1f} MB ({proc['memory_percent']:4.1f}%)"
                )

                # Show command for external processes
                if proc["cmdline"] and len(proc["cmdline"]) > len(proc["name"]):
                    cmd_short = (
                        proc["cmdline"][:60] + "..."
                        if len(proc["cmdline"]) > 60
                        else proc["cmdline"]
                    )
                    print(f"    Command: {cmd_short}")
            print()

        # Warn about high memory usage
        high_memory_procs = [p for p in all_processes if p["memory_mb"] > 8000]
        if high_memory_procs:
            print("⚠️  High Memory Usage Detected:")
            for proc in high_memory_procs:
                print(
                    f"    {proc['name']} (PID {proc['pid']}): {proc['memory_mb']:.1f} MB"
                )
            print("    Consider reducing grid sizes or other parameters\n")
    else:
        print("No CRONOS processes found")


def main():
    """Command-line interface for the CRONOS memory monitoring utility.

    Provides three main commands:
    - monitor: Start real-time memory monitoring with configurable intervals and thresholds
    - check: Snapshot of current CRONOS processes and their memory usage
    - info: Display system memory information and recommendations

    Command-line arguments are parsed using argparse with subcommands for each mode.

    Returns:
        None: Executes the requested command and exits.

    Example:
        >>> main()  # Called when script is run directly
        # With arguments: python memory_monitor.py monitor --interval 2 --threshold 90
    """
    parser = argparse.ArgumentParser(
        description="Memory monitoring for CRONOS simulations"
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor", help="Start real-time memory monitoring"
    )
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Monitoring interval in seconds (default: 5)",
    )
    monitor_parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Warning threshold percentage (default: 80)",
    )
    monitor_parser.add_argument(
        "--log", type=str, help="Log file to save memory usage data"
    )

    # Check processes command
    check_parser = subparsers.add_parser(
        "check", help="Check current CRONOS processes"
    )

    # System info command
    info_parser = subparsers.add_parser(
        "info", help="Show system memory information"
    )

    args = parser.parse_args()

    if args.command == "monitor":
        monitor_memory(args.interval, args.threshold, args.log)

    elif args.command == "check":
        check_cronos_processes()

    elif args.command == "info":
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        print("💻 System Memory Information")
        print("=" * 40)
        print(f"Total RAM:      {memory.total / 1024**3:.1f} GB")
        print(f"Available RAM:  {memory.available / 1024**3:.1f} GB")
        print(
            f"Used RAM:       {memory.used / 1024**3:.1f} GB ({memory.percent:.1f}%)"
        )
        print(f"Free RAM:       {memory.free / 1024**3:.1f} GB")
        print()
        print(f"Total Swap:     {swap.total / 1024**3:.1f} GB")
        print(
            f"Used Swap:      {swap.used / 1024**3:.1f} GB ({swap.percent:.1f}%)"
        )

        # Memory recommendations
        print(f"\n📋 Recommendations:")
        if memory.percent > 90:
            print(
                "  🔴 Critical memory usage - consider stopping non-essential processes"
            )
        elif memory.percent > 75:
            print("  🟡 High memory usage - monitor closely during simulations")
        else:
            print("  🟢 Memory usage looks good for running simulations")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
