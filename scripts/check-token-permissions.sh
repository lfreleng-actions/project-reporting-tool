#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
#
# Script to check GitHub token permissions and rate limits
#
# Usage: check-token-permissions.sh [token]
#   If no token provided, checks GITHUB_TOKEN and CLASSIC_READ_ONLY_PAT_TOKEN env vars

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

log_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$*${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed"
    log_info "Install with: brew install jq (macOS) or apt-get install jq (Ubuntu)"
    exit 1
fi

# Get token from argument or environment
TOKEN=""
TOKEN_SOURCE=""

if [ $# -ge 1 ]; then
    TOKEN="$1"
    TOKEN_SOURCE="command line argument"
elif [ -n "${GITHUB_TOKEN:-}" ]; then
    TOKEN="$GITHUB_TOKEN"
    TOKEN_SOURCE="GITHUB_TOKEN environment variable"
elif [ -n "${CLASSIC_READ_ONLY_PAT_TOKEN:-}" ]; then
    TOKEN="$CLASSIC_READ_ONLY_PAT_TOKEN"
    TOKEN_SOURCE="CLASSIC_READ_ONLY_PAT_TOKEN environment variable"
else
    log_error "No GitHub token provided"
    echo ""
    echo "Usage: $0 [token]"
    echo ""
    echo "Or set one of these environment variables:"
    echo "  export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx"
    echo "  export CLASSIC_READ_ONLY_PAT_TOKEN=ghp_xxxxxxxxxxxxx"
    exit 1
fi

log_section "🔐 GitHub Token Permissions Checker"
echo ""
log_info "Token source: ${TOKEN_SOURCE}"
log_info "Token prefix: ${TOKEN:0:7}..."
echo ""

# Function to make GitHub API call
github_api() {
    local endpoint="$1"
    local method="${2:-GET}"

    curl -s -X "$method" \
        -H "Authorization: token ${TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com${endpoint}"
}

# Check rate limit
log_section "📊 Rate Limit Status"
echo ""

RATE_LIMIT=$(github_api "/rate_limit")

if echo "$RATE_LIMIT" | jq -e . >/dev/null 2>&1; then
    CORE_LIMIT=$(echo "$RATE_LIMIT" | jq -r '.resources.core.limit')
    CORE_REMAINING=$(echo "$RATE_LIMIT" | jq -r '.resources.core.remaining')
    CORE_RESET=$(echo "$RATE_LIMIT" | jq -r '.resources.core.reset')
    SEARCH_LIMIT=$(echo "$RATE_LIMIT" | jq -r '.resources.search.limit')
    SEARCH_REMAINING=$(echo "$RATE_LIMIT" | jq -r '.resources.search.remaining')

    # Convert reset time to human readable
    if command -v date >/dev/null 2>&1; then
        if date --version 2>&1 | grep -q GNU; then
            RESET_TIME=$(date -d "@${CORE_RESET}" '+%Y-%m-%d %H:%M:%S %Z')
        else
            RESET_TIME=$(date -r "${CORE_RESET}" '+%Y-%m-%d %H:%M:%S %Z')
        fi
    else
        RESET_TIME="timestamp: ${CORE_RESET}"
    fi

    echo "Core API:"
    if [ "$CORE_LIMIT" -eq 60 ]; then
        log_warning "  Limit: ${CORE_LIMIT}/hour (UNAUTHENTICATED - token may be invalid)"
    elif [ "$CORE_LIMIT" -eq 5000 ]; then
        log_success "  Limit: ${CORE_LIMIT}/hour (authenticated)"
    else
        log_info "  Limit: ${CORE_LIMIT}/hour"
    fi

    if [ "$CORE_REMAINING" -lt 100 ]; then
        log_warning "  Remaining: ${CORE_REMAINING}"
    else
        log_success "  Remaining: ${CORE_REMAINING}"
    fi

    log_info "  Reset at: ${RESET_TIME}"

    echo ""
    echo "Search API:"
    log_info "  Limit: ${SEARCH_LIMIT}/minute"
    log_info "  Remaining: ${SEARCH_REMAINING}"
else
    log_error "Failed to fetch rate limit - token may be invalid"
    echo "$RATE_LIMIT"
    exit 1
fi

# Check token scopes (Classic tokens only)
log_section "🔑 Token Scopes"
echo ""

SCOPES_RESPONSE=$(curl -s -I \
    -H "Authorization: token ${TOKEN}" \
    "https://api.github.com/user" 2>/dev/null || echo "")

if [ -n "$SCOPES_RESPONSE" ]; then
    SCOPES=$(echo "$SCOPES_RESPONSE" | grep -i "x-oauth-scopes:" | cut -d: -f2- | tr -d '\r' | xargs)

    if [ -z "$SCOPES" ]; then
        log_warning "No scopes found - this is likely a fine-grained token"
        log_info "Fine-grained tokens don't expose scopes via API"
        log_info "Check permissions in GitHub Settings → Developer settings → Personal access tokens"
    else
        log_info "Token scopes: ${SCOPES}"
        echo ""

        # Check for important scopes
        echo "Scope analysis:"

        if echo "$SCOPES" | grep -q "repo"; then
            log_success "  ✓ repo - Full repository access"
        elif echo "$SCOPES" | grep -q "public_repo"; then
            log_success "  ✓ public_repo - Public repository access"
        else
            log_warning "  ✗ repo/public_repo - Cannot access repositories"
        fi

        if echo "$SCOPES" | grep -q "read:org"; then
            log_success "  ✓ read:org - Can read organization data"
        else
            log_info "  ✗ read:org - Cannot read organization data"
        fi

        if echo "$SCOPES" | grep -q "workflow"; then
            log_success "  ✓ workflow - Can access GitHub Actions workflows"
        else
            log_info "  ✗ workflow - Cannot access workflow details"
        fi

        if echo "$SCOPES" | grep -q "read:user"; then
            log_success "  ✓ read:user - Can read user data"
        else
            log_info "  ✗ read:user - Cannot read user data"
        fi
    fi
else
    log_error "Failed to fetch token scopes"
fi

# Test token by fetching user info
log_section "👤 Token User Information"
echo ""

USER_INFO=$(github_api "/user")

if echo "$USER_INFO" | jq -e . >/dev/null 2>&1; then
    LOGIN=$(echo "$USER_INFO" | jq -r '.login // "unknown"')
    NAME=$(echo "$USER_INFO" | jq -r '.name // "N/A"')
    EMAIL=$(echo "$USER_INFO" | jq -r '.email // "N/A"')
    TOKEN_TYPE=$(echo "$USER_INFO" | jq -r '.type // "unknown"')

    log_success "Authenticated as: ${LOGIN}"
    log_info "Name: ${NAME}"
    log_info "Email: ${EMAIL}"
    log_info "Type: ${TOKEN_TYPE}"
else
    log_error "Failed to fetch user information"
    echo "$USER_INFO"
fi

# Test repository access
log_section "🧪 Test Repository Access"
echo ""

log_info "Testing public repository access..."
TEST_REPO="octocat/Hello-World"
REPO_CHECK=$(github_api "/repos/${TEST_REPO}")

if echo "$REPO_CHECK" | jq -e '.id' >/dev/null 2>&1; then
    log_success "✓ Can access public repositories (${TEST_REPO})"
else
    log_error "✗ Cannot access public repositories"
    echo "Response: $REPO_CHECK"
fi

# Test fine-grained permissions (if applicable)
log_section "🔍 Fine-Grained Token Permissions Check"
echo ""

log_info "Attempting to determine token type..."

# Try to get token metadata (only works for fine-grained tokens)
TOKEN_META=$(curl -s -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Authorization: token ${TOKEN}" \
    "https://api.github.com/applications/CLIENT_ID/token" 2>/dev/null || echo "")

if echo "$TOKEN_META" | jq -e '.scopes' >/dev/null 2>&1; then
    log_info "This appears to be a fine-grained token"
    log_info "Permissions must be checked in GitHub UI:"
    log_info "  https://github.com/settings/tokens"
else
    log_info "This appears to be a classic token"
    log_info "Scopes are listed in the 'Token Scopes' section above"
fi

# Summary and recommendations
log_section "📋 Summary & Recommendations"
echo ""

echo "For the lf-releng-project-reporting, you need:"
echo ""
echo "CLASSIC_READ_ONLY_PAT_TOKEN (for report generation):"
echo "   Minimum scopes:"
log_info "   ✓ public_repo - Access public repositories"
log_info "   ✓ read:org - Read org membership (optional)"
log_info "   ✓ repo:status - Read commit status (optional)"
echo ""

echo "Current token rate limit: ${CORE_REMAINING}/${CORE_LIMIT}"
if [ "$CORE_LIMIT" -eq 60 ]; then
    log_error "⚠️  WARNING: Token is not being recognized (unauthenticated rate limit)"
    log_error "    This will cause 404 errors and rate limiting issues"
    log_error "    Please check that your token is valid and has proper scopes"
elif [ "$CORE_REMAINING" -lt 1000 ]; then
    log_warning "⚠️  Rate limit is getting low - consider waiting or using a different token"
else
    log_success "✓ Token is working properly with good rate limit remaining"
fi

echo ""
log_section "✅ Check Complete"
echo ""
