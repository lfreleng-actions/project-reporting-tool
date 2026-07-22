#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Jenkins Connection Diagnostic Tool

This script helps diagnose why Jenkins API calls are failing by:
1. Testing connectivity to the Jenkins server
2. Trying different API endpoint patterns
3. Checking authentication requirements
4. Providing detailed error information

Usage:
    python scripts/diagnose_jenkins.py <jenkins-host>
    python scripts/diagnose_jenkins.py jenkins.lf-broadband.org
    python scripts/diagnose_jenkins.py jenkins.lfbroadband.org --verbose
"""

import argparse
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json

import httpx


class Colors:
    """ANSI color codes."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")


def test_basic_connectivity(host, verbose=False):
    """Test basic HTTP/HTTPS connectivity."""
    print_header("Test 1: Basic Connectivity")

    protocols = ["https", "http"]

    for protocol in protocols:
        url = f"{protocol}://{host}"
        print_info(f"Testing {url}...")

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(url)

                if response.status_code < 400:
                    print_success(
                        f"{protocol.upper()} connection successful (status: {response.status_code})"
                    )
                    if verbose:
                        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
                        print(f"   Server: {response.headers.get('server', 'N/A')}")
                    return f"{protocol}://{host}"
                else:
                    print_warning(f"{protocol.upper()} returned status {response.status_code}")

        except httpx.ConnectError as e:
            print_error(f"{protocol.upper()} connection failed: {e}")
        except httpx.TimeoutException:
            print_error(f"{protocol.upper()} connection timeout")
        except Exception as e:
            print_error(f"{protocol.upper()} error: {type(e).__name__}: {e}")

    return None


def _probe_jenkins_pattern(base_url, pattern, verbose=False):
    """Probe one Jenkins API pattern; return (pattern, job_count) or None."""
    url = f"{base_url}{pattern}?tree=jobs[name]"
    print_info(f"Testing: {pattern}")

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url)
    except httpx.ConnectError as e:
        print_error(f"Connection failed: {e}")
        return None
    except httpx.TimeoutException:
        print_error("Timeout")
        return None
    except Exception as e:
        print_error(f"Error: {type(e).__name__}: {e}")
        return None

    if response.status_code == 403:
        print_warning("Access forbidden (403) - may require authentication")
        return None
    if response.status_code == 404:
        print_info("Not found (404)")
        return None
    if response.status_code != 200:
        print_warning(f"HTTP {response.status_code}")
        if verbose:
            print(f"   Response: {response.text[:200]}")
        return None

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response: {e}")
        if verbose:
            print(f"   Response preview: {response.text[:200]}")
        return None

    if "jobs" not in data:
        print_warning(f"Valid JSON but no 'jobs' key: {list(data.keys())}")
        return None

    job_count = len(data.get("jobs", []))
    print_success(f"Working endpoint! Found {job_count} jobs")

    if verbose and job_count > 0:
        print("   Sample jobs:")
        for job in data["jobs"][:5]:
            print(f"      - {job.get('name', 'N/A')}")

    return pattern, job_count


def test_jenkins_api_patterns(base_url, verbose=False):
    """Test different Jenkins API endpoint patterns."""
    print_header("Test 2: Jenkins API Endpoint Discovery")

    patterns = [
        "/api/json",
        "/releng/api/json",
        "/jenkins/api/json",
        "/ci/api/json",
        "/build/api/json",
        "/sandbox/api/json",
        "/production/api/json",
    ]

    working_endpoints = []

    for pattern in patterns:
        result = _probe_jenkins_pattern(base_url, pattern, verbose)
        if result is not None:
            working_endpoints.append(result)

    return working_endpoints


def test_authentication(base_url):
    """Test if authentication is required."""
    print_header("Test 3: Authentication Check")

    # Test without auth
    url = f"{base_url}/api/json"
    print_info("Testing without authentication...")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)

            if response.status_code == 401:
                print_warning("401 Unauthorized - authentication required")
                print_info("Jenkins requires credentials")
                return True
            elif response.status_code == 403:
                print_warning("403 Forbidden - may need authentication or permissions")
                return True
            elif response.status_code == 200:
                print_success("No authentication required")
                return False
            else:
                print_info(f"Status: {response.status_code}")
                return None

    except Exception as e:
        print_error(f"Error: {e}")
        return None


def test_dns_resolution(host):
    """Test DNS resolution."""
    print_header("Test 4: DNS Resolution")

    import socket

    print_info(f"Resolving {host}...")

    try:
        ip_addresses = socket.getaddrinfo(host, None)
        unique_ips = {addr[4][0] for addr in ip_addresses}

        print_success("DNS resolution successful")
        for ip in unique_ips:
            print(f"   → {ip}")

        return True

    except socket.gaierror as e:
        print_error(f"DNS resolution failed: {e}")
        print_warning("The hostname cannot be resolved")
        print_info("Possible issues:")
        print("   - Hostname typo")
        print("   - DNS server issues")
        print("   - Hostname doesn't exist")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_common_jenkins_hosts(original_host):
    """Test common variations of the hostname."""
    print_header("Test 5: Common Hostname Variations")

    variations = []

    # Extract base name
    if "." in original_host:
        parts = original_host.split(".")
        base = parts[0]

        # Common patterns
        variations = [
            original_host,
            f"jenkins.{original_host}",
            f"{base}-jenkins.{'.'.join(parts[1:])}",
            original_host.replace("jenkins.", ""),
        ]

        # Remove duplicates
        variations = list(dict.fromkeys(variations))
    else:
        variations = [original_host]

    print_info("Testing hostname variations...")

    working_hosts = []

    for host in variations:
        print(f"\n   Testing: {host}")

        for protocol in ["https", "http"]:
            url = f"{protocol}://{host}/api/json"

            try:
                with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                    response = client.get(url)

                    if response.status_code < 400:
                        print_success(f"   {protocol.upper()} works: {url}")
                        working_hosts.append(f"{protocol}://{host}")
                        break

            except Exception:
                continue

    if working_hosts:
        print_success(f"\nFound {len(working_hosts)} working host(s)")
    else:
        print_warning("\nNo working hosts found")

    return working_hosts


def get_jenkins_info(base_url):
    """Get Jenkins version and info if available."""
    print_header("Jenkins Server Information")

    url = f"{base_url}/api/json"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()

                print_info("Server details:")
                print(f"   Mode: {data.get('mode', 'N/A')}")
                print(f"   Node Name: {data.get('nodeName', 'N/A')}")
                print(f"   Description: {data.get('nodeDescription', 'N/A')}")
                print(f"   Jobs: {len(data.get('jobs', []))}")

                # Jenkins version from headers
                jenkins_version = response.headers.get("X-Jenkins", "N/A")
                print(f"   Jenkins Version: {jenkins_version}")

                return True
            else:
                print_warning(f"Could not retrieve info (status: {response.status_code})")
                return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def main():
    """Main diagnostic routine."""
    parser = argparse.ArgumentParser(description="Diagnose Jenkins API connectivity issues")
    parser.add_argument("host", help="Jenkins hostname (e.g., jenkins.example.org)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              Jenkins Connection Diagnostic Tool                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    print_info(f"Target: {args.host}")
    print()

    # Test DNS first
    dns_ok = test_dns_resolution(args.host)
    if not dns_ok:
        print_error("\n❌ DNS resolution failed - cannot continue")
        print_info("Fix DNS issues before proceeding")
        return 1

    # Test basic connectivity
    base_url = test_basic_connectivity(args.host, args.verbose)
    if not base_url:
        print_warning("\n⚠️  Basic connectivity failed")
        print_info("Trying hostname variations...")
        working_hosts = test_common_jenkins_hosts(args.host)

        if working_hosts:
            base_url = working_hosts[0]
            print_success(f"Using: {base_url}")
        else:
            print_error("\n❌ Could not establish connection to any host")
            return 1

    # Test Jenkins API endpoints
    working_endpoints = test_jenkins_api_patterns(base_url, args.verbose)

    # Test authentication
    auth_required = test_authentication(base_url)

    # Get server info if possible
    if working_endpoints:
        get_jenkins_info(base_url)

    # Summary
    print_header("Diagnostic Summary")

    if working_endpoints:
        print_success("Jenkins API is accessible!")
        print(f"\n{Colors.BOLD}Working configuration:{Colors.END}")
        print(f"   Base URL: {base_url}")
        print("   API Endpoints:")
        for endpoint, job_count in working_endpoints:
            print(f"      • {endpoint} ({job_count} jobs)")

        if auth_required:
            print(
                f"\n{Colors.YELLOW}⚠️  Authentication may be required for some operations{Colors.END}"
            )

        return 0
    else:
        print_error("Could not find working Jenkins API endpoint")
        print(f"\n{Colors.BOLD}Troubleshooting steps:{Colors.END}")
        print("   1. Verify the hostname is correct")
        print("   2. Check if Jenkins is running")
        print("   3. Verify firewall rules allow access")
        print("   4. Check if authentication is required")
        print("   5. Verify the Jenkins installation is using standard paths")

        return 1


if __name__ == "__main__":
    sys.exit(main())
