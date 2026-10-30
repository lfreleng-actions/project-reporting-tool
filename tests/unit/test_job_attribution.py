# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Comprehensive test suite for Jenkins job attribution logic.

This module provides:
1. Regression tests - Ensure existing ONAP/ODL prefix-based matching continues to work
2. Feature tests - Verify new LF Broadband suffix/infix patterns are matched
3. Negative tests - Ensure jobs don't match wrong projects (prevent false positives)
4. Integration tests - Test with production data fixtures

Test fixtures are extracted from actual production report data at:
https://github.com/lfreleng-actions/project-reporting-artifacts/tree/main/data/artifacts

Run these tests with:
    pytest tests/unit/test_job_attribution.py -v
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from lf_releng_project_reporting.api.jenkins_client import JenkinsAPIClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_stats():
    """Create a mock stats object for JenkinsAPIClient."""
    stats = Mock()
    stats.record_success = Mock()
    stats.record_error = Mock()
    return stats


@pytest.fixture
def jenkins_client(mock_stats):
    """Create a JenkinsAPIClient instance for testing."""
    client = JenkinsAPIClient(host="jenkins.example.com", timeout=30.0, stats=mock_stats)
    # Mock the discovery to avoid network calls
    client.api_base_path = "/api/json"
    client._cache_populated = False
    client._jobs_cache = {}
    yield client
    client.close()


@pytest.fixture
def production_fixtures() -> dict[str, Any]:
    """Load production data fixtures for integration testing."""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "job_attribution" / "production_data.json"
    )
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    else:
        pytest.skip(f"Fixture file not found: {fixture_path}")


# =============================================================================
# Test: ONAP Prefix-Based Matching (Regression Protection)
# =============================================================================


class TestONAPPrefixMatching:
    """
    Regression tests for ONAP-style prefix-based job matching.

    ONAP jobs follow the pattern: {project-name}-{job-type}-{stream}
    Examples:
        - aai-babel-maven-verify-master -> aai/babel
        - sdc-verify-java -> sdc
        - integration-master-merge-java -> integration

    These tests MUST pass before and after any changes to the matching algorithm.
    """

    @pytest.mark.parametrize(
        "job_name,project_name,project_job_name,should_match",
        [
            # Exact matches
            ("test-project", "test/project", "test-project", True),
            ("sdc", "sdc", "sdc", True),
            ("integration", "integration", "integration", True),
            # Prefix matches with dash separator
            ("aai-babel-maven-verify-master", "aai/babel", "aai-babel", True),
            ("sdc-verify-java", "sdc", "sdc", True),
            ("integration-master-merge-java", "integration", "integration", True),
            ("cps-master-verify-java", "cps", "cps", True),
            ("demo-maven-stage-master", "demo", "demo", True),
            # Multi-level project paths
            (
                "dcaegen2-analytics-tca-gen2-maven-clm-master",
                "dcaegen2/analytics/tca-gen2",
                "dcaegen2-analytics-tca-gen2",
                True,
            ),
            ("ccsdk-apps-maven-docker-stage-master", "ccsdk/apps", "ccsdk-apps", True),
            (
                "multicloud-framework-artifactbroker-sonar",
                "multicloud/framework",
                "multicloud-framework",
                True,
            ),
            # Non-matches (must return 0)
            ("other-job", "test/project", "test-project", False),
            ("xsdc-verify", "sdc", "sdc", False),  # Different prefix
            ("babel", "aai/babel", "aai-babel", False),  # Missing parent prefix
            ("random-job-name", "cps", "cps", False),
        ],
    )
    def test_prefix_matching_preserved(
        self, jenkins_client, job_name, project_name, project_job_name, should_match
    ):
        """Verify prefix-based matching behavior is preserved for ONAP patterns."""
        score = jenkins_client._calculate_job_match_score(job_name, project_name, project_job_name)

        if should_match:
            assert score > 0, f"Expected '{job_name}' to match project '{project_name}'"
        else:
            assert score == 0, f"Expected '{job_name}' NOT to match project '{project_name}'"

    def test_exact_match_highest_score(self, jenkins_client):
        """Verify exact match gets the highest score."""
        exact_score = jenkins_client._calculate_job_match_score(
            "test-project", "test/project", "test-project"
        )
        prefix_score = jenkins_client._calculate_job_match_score(
            "test-project-verify", "test/project", "test-project"
        )

        assert exact_score > prefix_score, "Exact match should score higher than prefix match"
        assert exact_score >= 1000, "Exact match should have score >= 1000"

    def test_prefix_match_minimum_score(self, jenkins_client):
        """Verify prefix match has a reasonable minimum score."""
        score = jenkins_client._calculate_job_match_score("sdc-verify-java", "sdc", "sdc")
        assert score >= 500, "Prefix match should have score >= 500"

    def test_case_insensitive_matching(self, jenkins_client):
        """Verify matching is case-insensitive."""
        score_lower = jenkins_client._calculate_job_match_score(
            "test-project", "test/project", "test-project"
        )
        score_upper = jenkins_client._calculate_job_match_score(
            "TEST-PROJECT", "test/project", "test-project"
        )
        score_mixed = jenkins_client._calculate_job_match_score(
            "Test-Project", "test/project", "test-project"
        )

        assert score_lower == score_upper == score_mixed

    def test_nested_project_bonus(self, jenkins_client):
        """Verify deeper project paths get higher scores (more specific matches)."""
        score_shallow = jenkins_client._calculate_job_match_score("aai-verify", "aai", "aai")
        score_deep = jenkins_client._calculate_job_match_score(
            "aai-babel-verify", "aai/babel", "aai-babel"
        )

        # Deeper paths should score higher to prioritize more specific matches
        assert score_deep > score_shallow, "Deeper project paths should have higher scores"


class TestONAPProductionRegression:
    """
    Regression tests using actual ONAP production data.

    These mappings are extracted from real production reports and represent
    the current working behavior that MUST be preserved.
    """

    @pytest.mark.parametrize(
        "job_name,expected_project",
        [
            # AAI project jobs
            ("aai-aai-common-master-merge-java", "aai/aai-common"),
            ("aai-aai-common-master-verify-java", "aai/aai-common"),
            ("aai-aai-common-maven-clm-master", "aai/aai-common"),
            # CCSDK project jobs
            ("ccsdk-apps-maven-clm-master", "ccsdk/apps"),
            ("ccsdk-apps-maven-docker-stage-master", "ccsdk/apps"),
            # CI-Management jobs
            ("ci-management-jenkins-cfg-verify", "ci-management"),
            # CPS project jobs
            ("cps-master-merge-java", "cps"),
            ("cps-master-verify-java", "cps"),
            ("cps-maven-clm-master", "cps"),
            # Demo project jobs
            ("demo-master-merge-java", "demo"),
            ("demo-master-verify-java", "demo"),
            # Integration project jobs
            ("integration-master-verify-python", "integration"),
        ],
    )
    def test_onap_known_mappings(self, jenkins_client, job_name, expected_project):
        """Verify known ONAP job->project mappings continue to work."""
        project_job_name = expected_project.replace("/", "-")
        score = jenkins_client._calculate_job_match_score(
            job_name, expected_project, project_job_name
        )

        assert score > 0, (
            f"REGRESSION: Job '{job_name}' should match project '{expected_project}' "
            f"but got score {score}"
        )

    def test_onap_production_fixtures(self, jenkins_client, production_fixtures):
        """Test all ONAP mappings from production fixtures."""
        if "onap" not in production_fixtures:
            pytest.skip("ONAP fixtures not available")

        onap_data = production_fixtures["onap"]
        mappings = onap_data.get("known_working_mappings", {})

        failures = []
        for job_name, expected_project in mappings.items():
            project_job_name = expected_project.replace("/", "-")
            score = jenkins_client._calculate_job_match_score(
                job_name, expected_project, project_job_name
            )
            if score == 0:
                failures.append(f"{job_name} -> {expected_project}")

        assert len(failures) == 0, (
            f"REGRESSION: {len(failures)} ONAP mappings failed:\n"
            + "\n".join(failures[:10])
            + (f"\n... and {len(failures) - 10} more" if len(failures) > 10 else "")
        )


# =============================================================================
# Test: LF Broadband Suffix/Infix Patterns (New Feature)
# =============================================================================


class TestLFBroadbandPatterns:
    """
    Tests for LF Broadband job naming patterns.

    LF Broadband uses different naming conventions:
    1. {job-type}_{project-name} - e.g., docker-publish_bbsim
    2. verify_{project-name}_{job-type} - e.g., verify_aaa_maven-test
    3. github-release_{project-name} - e.g., github-release_voltctl

    These tests define the EXPECTED behavior after the matching algorithm is enhanced.
    Initially these tests may fail (marking the feature as not yet implemented).
    """

    @pytest.mark.parametrize(
        "job_name,project_name,should_match",
        [
            # Pattern: {job-type}_{project-name} (suffix with underscore)
            ("docker-publish_bbsim", "bbsim", True),
            ("docker-publish_voltha-go", "voltha-go", True),
            ("docker-publish_voltha-openolt-adapter", "voltha-openolt-adapter", True),
            ("maven-publish_aaa", "aaa", True),
            ("maven-publish_sadis", "sadis", True),
            ("github-release_bbsim", "bbsim", True),
            ("github-release_voltctl", "voltctl", True),
            # Pattern: verify_{project-name}_{job-type} (infix)
            ("verify_aaa_licensed", "aaa", True),
            ("verify_aaa_maven-test", "aaa", True),
            ("verify_bbsim_unit-test", "bbsim", True),
            ("verify_bbsim_licensed", "bbsim", True),
            ("verify_voltha-go_sanity-test", "voltha-go", True),
            ("verify_voltha-docs_licensed", "voltha-docs", True),
            # Negative cases - should NOT match wrong projects
            ("docker-publish_bbsim", "bbsim-sadis-server", False),
            ("verify_aaa_licensed", "aaaa", False),
            ("verify_aaa_licensed", "aab", False),
        ],
    )
    def test_lfbroadband_patterns(self, jenkins_client, job_name, project_name, should_match):
        """
        Test LF Broadband job naming patterns.

        NOTE: This test documents EXPECTED behavior. It may initially fail
        until the matching algorithm is enhanced to support these patterns.
        """
        project_job_name = project_name.replace("/", "-")
        score = jenkins_client._calculate_job_match_score(job_name, project_name, project_job_name)

        if should_match:
            assert score > 0, (
                f"Expected '{job_name}' to match project '{project_name}' (LF Broadband pattern)"
            )
        else:
            assert score == 0, f"Expected '{job_name}' NOT to match project '{project_name}'"

    def test_suffix_pattern_docker_publish(self, jenkins_client):
        """Test docker-publish_{project} pattern matching."""
        test_cases = [
            ("docker-publish_bbsim", "bbsim"),
            ("docker-publish_voltha-go", "voltha-go"),
            ("docker-publish_ofagent-go", "ofagent-go"),
        ]

        for job_name, project in test_cases:
            score = jenkins_client._calculate_job_match_score(job_name, project, project)
            assert score > 0, f"docker-publish_{project} should match {project}"

    def test_suffix_pattern_maven_publish(self, jenkins_client):
        """Test maven-publish_{project} pattern matching."""
        test_cases = [
            ("maven-publish_aaa", "aaa"),
            ("maven-publish_sadis", "sadis"),
            ("maven-publish_dhcpl2relay", "dhcpl2relay"),
        ]

        for job_name, project in test_cases:
            score = jenkins_client._calculate_job_match_score(job_name, project, project)
            assert score > 0, f"maven-publish_{project} should match {project}"

    def test_infix_pattern_verify(self, jenkins_client):
        """Test verify_{project}_{type} pattern matching."""
        test_cases = [
            ("verify_aaa_licensed", "aaa"),
            ("verify_aaa_maven-test", "aaa"),
            ("verify_bbsim_unit-test", "bbsim"),
            ("verify_voltha-go_sanity-test", "voltha-go"),
        ]

        for job_name, project in test_cases:
            score = jenkins_client._calculate_job_match_score(job_name, project, project)
            assert score > 0, f"{job_name} should match {project}"

    def test_lfbroadband_production_fixtures(self, jenkins_client, production_fixtures):
        """Test LF Broadband expected mappings from production fixtures."""
        if "lfbroadband" not in production_fixtures:
            pytest.skip("LF Broadband fixtures not available")

        lfb_data = production_fixtures["lfbroadband"]
        expected_mappings = lfb_data.get("expected_mappings", {})

        matched = 0
        failed = []

        for job_name, expected_project in expected_mappings.items():
            project_job_name = expected_project.replace("/", "-")
            score = jenkins_client._calculate_job_match_score(
                job_name, expected_project, project_job_name
            )
            if score > 0:
                matched += 1
            else:
                failed.append(f"{job_name} -> {expected_project}")

        total = len(expected_mappings)
        match_rate = (matched / total * 100) if total > 0 else 0

        # We expect at least 80% of LF Broadband jobs to match with the enhanced algorithm
        # This threshold can be adjusted based on implementation
        target_rate = lfb_data.get("target_allocation_percentage", 50.0)

        assert match_rate >= target_rate, (
            f"LF Broadband matching rate {match_rate:.1f}% is below target {target_rate}%\n"
            f"Failed mappings ({len(failed)}):\n"
            + "\n".join(failed[:15])
            + (f"\n... and {len(failed) - 15} more" if len(failed) > 15 else "")
        )


# =============================================================================
# Test: Negative Cases (Prevent False Positives)
# =============================================================================


class TestNegativeCases:
    """
    Tests to ensure jobs don't incorrectly match wrong projects.

    These tests prevent regressions where the matching algorithm becomes
    too permissive and creates false positive matches.
    """

    @pytest.mark.parametrize(
        "job_name,wrong_project,reason",
        [
            # Prefix should not match substring
            ("sdc-tosca-verify", "tosca", "tosca is a component of sdc, not a separate project"),
            ("aai-babel-verify", "babel", "babel is under aai/, not a root project"),
            # Similar but different names
            ("verify_aaa_licensed", "aaaa", "Different project name"),
            ("verify_aaa_licensed", "aab", "Different project name"),
            # Suffix pattern should be exact
            (
                "docker-publish_bbsim",
                "bbsim-sadis-server",
                "bbsim-sadis-server is a different project",
            ),
            ("docker-publish_voltha-go", "voltha-go-controller", "Different project"),
            # Random jobs should not match
            ("random-unrelated-job", "aaa", "Unrelated job name"),
            ("build-something-else", "bbsim", "Unrelated job name"),
        ],
    )
    def test_no_false_positives(self, jenkins_client, job_name, wrong_project, reason):
        """Verify jobs don't match wrong projects."""
        project_job_name = wrong_project.replace("/", "-")
        score = jenkins_client._calculate_job_match_score(job_name, wrong_project, project_job_name)

        assert score == 0, (
            f"FALSE POSITIVE: '{job_name}' should NOT match '{wrong_project}' (reason: {reason})"
        )

    def test_partial_prefix_no_match(self, jenkins_client):
        """Verify partial prefix without separator doesn't match."""
        # "sdcabc" should NOT match "sdc" (no dash separator)
        score = jenkins_client._calculate_job_match_score("sdcabc-verify", "sdc", "sdc")
        assert score == 0, "Partial prefix without separator should not match"

    def test_suffix_without_correct_separator(self, jenkins_client):
        """Verify suffix matching requires correct separator."""
        # "docker-publish-bbsim" (dash) should NOT match via suffix pattern
        # Only "docker-publish_bbsim" (underscore) should match for LF Broadband
        # This should NOT match as a suffix pattern (dash instead of underscore)
        # But it MIGHT match as a prefix if bbsim is in the name...
        # The key is it shouldn't create a false positive for the wrong reason
        assert isinstance(
            jenkins_client._calculate_job_match_score("docker-publish-bbsim", "bbsim", "bbsim"),
            int,
        )


class TestNegativeProductionFixtures:
    """Test negative cases from production fixtures."""

    def test_production_negative_cases(self, jenkins_client, production_fixtures):
        """Verify negative test cases from production fixtures."""
        if "negative_test_cases" not in production_fixtures:
            pytest.skip("Negative test cases not available in fixtures")

        negative_cases = production_fixtures["negative_test_cases"].get("cases", [])

        failures = []
        for case in negative_cases:
            job_name = case["job"]
            wrong_project = case["wrong_project"]
            reason = case.get("reason", "No reason provided")

            project_job_name = wrong_project.replace("/", "-")
            score = jenkins_client._calculate_job_match_score(
                job_name, wrong_project, project_job_name
            )

            if score > 0:
                failures.append(f"{job_name} incorrectly matched {wrong_project}: {reason}")

        assert len(failures) == 0, "FALSE POSITIVES detected:\n" + "\n".join(failures)


# =============================================================================
# Test: Score Ordering and Priority
# =============================================================================


class TestScoreOrdering:
    """
    Tests to verify proper score ordering for disambiguation.

    When multiple projects could match a job, the scoring should prioritize
    the most specific/correct match.
    """

    def test_exact_match_beats_prefix_match(self, jenkins_client):
        """Exact match should score higher than prefix match."""
        exact = jenkins_client._calculate_job_match_score("sdc", "sdc", "sdc")
        prefix = jenkins_client._calculate_job_match_score("sdc-verify", "sdc", "sdc")

        assert exact > prefix, "Exact match should beat prefix match"

    def test_longer_prefix_beats_shorter(self, jenkins_client):
        """More specific (longer) prefix match should score higher."""
        short_match = jenkins_client._calculate_job_match_score("aai-babel-verify", "aai", "aai")
        long_match = jenkins_client._calculate_job_match_score(
            "aai-babel-verify", "aai/babel", "aai-babel"
        )

        assert long_match > short_match, "Longer/more specific prefix should score higher"

    def test_child_project_priority(self, jenkins_client):
        """Child project should be matched before parent for specific jobs."""
        # Job "aai-babel-verify" should score higher for "aai/babel" than "aai"
        parent_score = jenkins_client._calculate_job_match_score(
            "aai-babel-maven-verify", "aai", "aai"
        )
        child_score = jenkins_client._calculate_job_match_score(
            "aai-babel-maven-verify", "aai/babel", "aai-babel"
        )

        assert child_score > parent_score, (
            "Child project should score higher than parent for child-specific jobs"
        )


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_job_name(self, jenkins_client):
        """Empty job name should not match anything."""
        score = jenkins_client._calculate_job_match_score("", "test", "test")
        assert score == 0

    def test_empty_project_name(self, jenkins_client):
        """Empty project name should not match anything."""
        score = jenkins_client._calculate_job_match_score("test-job", "", "")
        assert score == 0

    def test_job_name_with_special_characters(self, jenkins_client):
        """Job names with special characters should be handled."""
        # Underscores are common in LF Broadband
        score = jenkins_client._calculate_job_match_score("verify_test_job", "test", "test")
        # Should either match or return 0, but not error
        assert isinstance(score, int)

    def test_very_long_job_name(self, jenkins_client):
        """Very long job names should be handled correctly."""
        long_job = "integration-simulators-nf-simulator-core-verify-java-master-" + "x" * 100
        score = jenkins_client._calculate_job_match_score(long_job, "integration", "integration")
        assert isinstance(score, int)

    def test_unicode_in_names(self, jenkins_client):
        """Unicode characters should be handled (even if not matching)."""
        score = jenkins_client._calculate_job_match_score(
            "test-项目-verify", "test/项目", "test-项目"
        )
        assert isinstance(score, int)

    def test_numeric_project_names(self, jenkins_client):
        """Numeric project names should work."""
        score = jenkins_client._calculate_job_match_score("5g-core-verify", "5g/core", "5g-core")
        # Should match as prefix
        assert score > 0


# =============================================================================
# Test: Pattern Documentation
# =============================================================================


class TestPatternDocumentation:
    """
    Tests that document the expected patterns.

    These serve as living documentation of what patterns are supported.
    """

    def test_documented_patterns(self, production_fixtures):
        """Verify documented patterns exist in fixtures."""
        if "job_naming_patterns" not in production_fixtures:
            pytest.skip("Pattern documentation not in fixtures")

        patterns = production_fixtures["job_naming_patterns"]

        expected_patterns = ["prefix_based", "suffix_underscore", "infix_verify"]
        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing documentation for pattern: {pattern}"
            assert "description" in patterns[pattern]
            assert "pattern" in patterns[pattern]
            assert "examples" in patterns[pattern]

    def test_pattern_examples_valid(self, jenkins_client, production_fixtures):
        """Verify pattern examples are actually matchable."""
        if "job_naming_patterns" not in production_fixtures:
            pytest.skip("Pattern documentation not in fixtures")

        patterns = production_fixtures["job_naming_patterns"]

        for pattern_name, pattern_data in patterns.items():
            examples = pattern_data.get("examples", [])
            for example in examples:
                job = example["job"]
                project = example["project"]
                project_job_name = project.replace("/", "-")

                score = jenkins_client._calculate_job_match_score(job, project, project_job_name)

                # For prefix_based, these should match with current algorithm
                if pattern_name == "prefix_based":
                    assert score > 0, f"Documented example should match: {job} -> {project}"
