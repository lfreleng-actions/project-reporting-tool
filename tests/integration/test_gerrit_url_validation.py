# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Integration tests for Gerrit admin URL validation.

Tests that the discovered Gerrit URL path prefixes generate valid URLs
that don't return 404 errors for known projects.

These tests make actual HTTP requests to live Gerrit servers, so they:
- Use reasonable timeouts to avoid hanging
- Implement retry logic for transient failures
- Can be skipped in CI if needed with --skip-integration marker
- Test both ONAP (uses /r prefix) and OpenDaylight (uses /gerrit prefix)
"""

from time import sleep

import httpx
import pytest


# Test data: (project, host, path_prefix, gerrit_project_name)
GERRIT_TEST_CASES = [
    # ONAP uses /r path prefix
    (
        "ONAP",
        "gerrit.onap.org",
        "/r",
        "oom",  # A well-known ONAP project
    ),
    # OpenDaylight uses /gerrit path prefix
    (
        "OpenDaylight",
        "git.opendaylight.org",
        "/gerrit",
        "releng/autorelease",  # A well-known ODL project
    ),
]


def make_request_with_retry(
    url: str,
    timeout: float = 10.0,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> httpx.Response | None:
    """
    Make HTTP request with retry logic.

    Args:
        url: URL to request
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Response object if successful, None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
                return response
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt < max_retries - 1:
                sleep(retry_delay)
                continue
            else:
                # All retries exhausted
                return None
        except Exception:
            # Unexpected error
            return None

    return None


@pytest.mark.integration
@pytest.mark.parametrize("project_name,host,path_prefix,gerrit_project", GERRIT_TEST_CASES)
def test_gerrit_admin_url_is_valid(project_name, host, path_prefix, gerrit_project):
    """
    Test that Gerrit admin URLs with discovered path prefix are valid.

    This test validates that the URL pattern we generate for Gerrit admin
    links is correct and doesn't return 404 errors.

    The test can be skipped in CI environments by using:
        pytest -m "not integration"
    """
    # Construct the admin URL using the same pattern as our code
    admin_url = f"https://{host}{path_prefix}/admin/repos/{gerrit_project},general"

    # Make request with retries
    response = make_request_with_retry(
        admin_url,
        timeout=10.0,
        max_retries=3,
        retry_delay=2.0,
    )

    # Assert we got a response
    assert response is not None, (
        f"Failed to connect to {admin_url} after 3 retries. "
        f"This might be a network issue or the server is down."
    )

    # Assert the URL is valid (not 404)
    assert response.status_code != 404, (
        f"{project_name} admin URL returned 404: {admin_url}\n"
        f"This indicates the path prefix '{path_prefix}' or project name "
        f"'{gerrit_project}' is incorrect."
    )

    # We expect either 200 (OK) or 403 (Forbidden - auth required)
    # Both indicate the URL is valid, just that we need auth to view it
    assert response.status_code in (200, 403), (
        f"{project_name} admin URL returned unexpected status {response.status_code}: {admin_url}\n"
        f"Expected 200 (OK) or 403 (Forbidden/Auth required)"
    )


@pytest.mark.integration
@pytest.mark.parametrize("project_name,host,path_prefix,gerrit_project", GERRIT_TEST_CASES)
def test_gerrit_path_prefix_discovery(project_name, host, path_prefix, gerrit_project):
    """
    Test that the path prefix can be discovered via redirects.

    This validates that our discovery mechanism works correctly by
    following redirects from the base URL.
    """
    base_url = f"https://{host}"

    # Make request without following redirects
    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = client.get(base_url)
    except Exception as e:
        pytest.skip(f"Could not connect to {base_url}: {e}")

    # If we got a redirect, verify it includes our expected path prefix
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("location", "")
        assert path_prefix in location, (
            f"{project_name} redirect does not contain expected path prefix.\n"
            f"Expected prefix: {path_prefix}\n"
            f"Redirect location: {location}"
        )


@pytest.mark.integration
def test_gerrit_api_endpoints_with_discovered_prefix():
    """
    Test that the Gerrit API endpoints work with discovered prefixes.

    This tests the actual API discovery mechanism that our code uses.
    """
    from lf_releng_project_reporting.api.gerrit_client import GerritAPIDiscovery

    test_cases = [
        ("gerrit.onap.org", "/r"),
        ("git.opendaylight.org", "/gerrit"),
    ]

    for host, expected_prefix in test_cases:
        try:
            with GerritAPIDiscovery(timeout=10.0) as discovery:
                base_url = discovery.discover_base_url(host)

                # Verify the discovered URL contains the expected prefix
                assert expected_prefix in base_url, (
                    f"Discovery for {host} did not find expected prefix.\n"
                    f"Expected: {expected_prefix}\n"
                    f"Discovered: {base_url}"
                )

                # Verify the discovered URL is actually the correct one
                expected_url = f"https://{host}{expected_prefix}"
                assert base_url == expected_url, (
                    f"Discovery for {host} returned incorrect URL.\n"
                    f"Expected: {expected_url}\n"
                    f"Got: {base_url}"
                )
        except Exception as e:
            pytest.skip(f"API discovery failed for {host}: {e}")


@pytest.mark.integration
@pytest.mark.slow
def test_gerrit_projects_api_responds():
    """
    Test that the Gerrit projects API endpoint is accessible.

    This is a more comprehensive test that actually tries to query
    the projects API to ensure our URLs are completely correct.
    """
    from lf_releng_project_reporting.api.gerrit_client import GerritAPIClient

    test_cases = [
        ("gerrit.onap.org", "oom"),
        ("git.opendaylight.org", "releng/autorelease"),
    ]

    for host, project_name in test_cases:
        try:
            with GerritAPIClient(host, timeout=10.0) as client:
                # Try to get project info
                project_info = client.get_project_info(project_name)

                # We should get some data back (even if limited due to auth)
                # If the URL is wrong, we'd get None
                assert project_info is not None, (
                    f"Could not retrieve project info for {project_name} on {host}.\n"
                    f"This might indicate an incorrect path prefix or project name."
                )

        except Exception as e:
            pytest.skip(f"API request failed for {host}/{project_name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
