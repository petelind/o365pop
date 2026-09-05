# Definition of Done Checklist Template

**Type**: Template  
**Required**: Yes  
**Produced by**: Check Definition of Done

# Definition of Done Checklist - {FeatureName}

**Feature**: {FeatureScreenID} {FeatureTitle}  
**Branch**: `feature/{feature-slug}`  
**Reviewer**: {ReviewerName}  
**Date**: {Date}

---

## Code Implementation

### Backend
- [ ] All models implemented with proper fields and relationships
- [ ] All services/business logic implemented
- [ ] All views/controllers implemented
- [ ] All URL routes configured
- [ ] All database migrations created and applied
- [ ] No hardcoded values - use settings/environment variables
- [ ] Proper error handling and logging
- [ ] All docstrings complete with examples (`:param:`, `:return:`, `:raises:`)
- [ ] Type hints on all function signatures

### Frontend
- [ ] All templates implemented with semantic HTML
- [ ] All HTMX interactions implemented
- [ ] All forms have proper validation (client + server)
- [ ] All `data-testid` attributes added for Playwright
- [ ] Bootstrap components used correctly
- [ ] Font Awesome icons added to all buttons
- [ ] Tooltips added to all action buttons
- [ ] Responsive design verified (mobile, tablet, desktop)
- [ ] Accessibility: ARIA labels, keyboard navigation, focus management

---

## Testing

### Test Coverage
- [ ] Unit tests: **{UnitTestCount}** tests written
- [ ] Integration tests: **{IntegrationTestCount}** tests written
- [ ] View tests: **{ViewTestCount}** tests written
- [ ] E2E tests: **{E2ETestCount}** tests written
- [ ] **Test pass rate: 100%** (no failing tests)
- [ ] **Code coverage: {CoveragePercentage}%** (minimum {CoverageTarget}%)

### Test Quality
- [ ] All happy path scenarios tested
- [ ] All error scenarios tested
- [ ] All edge cases tested
- [ ] All validation rules tested
- [ ] All authentication/authorization checks tested
- [ ] All state changes verified
- [ ] All redirects verified
- [ ] All messages (success/error) verified
- [ ] No mocking in integration tests (use real objects)

---

## Code Quality

### Linting & Formatting
- [ ] `make lint` passes with 0 errors, 0 warnings
- [ ] Code follows project style guide
- [ ] No commented-out code blocks
- [ ] No debug print statements
- [ ] No TODO comments (convert to issues)

### Code Review
- [ ] Code reviewed by {ReviewerName}
- [ ] All review comments addressed
- [ ] No merge conflicts
- [ ] Branch up to date with main/develop

---

## Documentation

### Code Documentation
- [ ] All functions have docstrings with examples
- [ ] All classes have docstrings
- [ ] All complex logic has inline comments
- [ ] All magic numbers explained

### User Documentation
- [ ] README updated if needed
- [ ] Feature file marked complete
- [ ] Implementation plan marked complete
- [ ] Any new setup steps documented

---

## User Experience

### Functionality
- [ ] All scenarios from feature file implemented
- [ ] All user flows work end-to-end
- [ ] All forms submit correctly
- [ ] All validation messages are clear and helpful
- [ ] All success messages are clear
- [ ] All error messages are user-friendly (no stack traces)
- [ ] All empty states have helpful messages and actions

### UI/UX
- [ ] UI matches mockups/design
- [ ] Consistent styling across all pages
- [ ] Loading states for async operations
- [ ] Proper focus management
- [ ] No layout shifts or flickering
- [ ] Icons are semantically appropriate
- [ ] Button labels are clear and actionable

### Performance
- [ ] Page load time < {LoadTimeTarget}ms
- [ ] No N+1 queries
- [ ] Database queries optimized
- [ ] Static assets cached properly

---

## Security

- [ ] All user inputs validated and sanitized
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] CSRF protection enabled
- [ ] Authentication required where needed
- [ ] Authorization checks in place
- [ ] Sensitive data not logged
- [ ] No secrets in code (use environment variables)

---

## Deployment Readiness

### Configuration
- [ ] All environment variables documented
- [ ] Database migrations tested
- [ ] Static files collected
- [ ] Settings configured for production

### Monitoring
- [ ] Logging configured at appropriate levels
- [ ] Error tracking configured
- [ ] Key metrics identified

---

## Git & GitHub

### Commits
- [ ] All commits follow Angular convention
- [ ] Commit messages are descriptive
- [ ] No WIP commits in final PR
- [ ] Commits are atomic (one logical change per commit)

### Pull Request
- [ ] PR title follows convention: `{FeatureName} - {ScenarioIDs}`
- [ ] PR description includes:
  - [ ] Link to feature file
  - [ ] Link to implementation plan
  - [ ] List of GitHub issues closed
  - [ ] Screenshots/GIFs of UI changes
  - [ ] Testing instructions
- [ ] PR labeled appropriately
- [ ] PR assigned to reviewer
- [ ] All CI/CD checks passing

### Issues
- [ ] All related GitHub issues closed
- [ ] Issues reference PR number
- [ ] Issues have completion comments

---

## Final Verification

### Manual Testing
- [ ] Tested in Chrome
- [ ] Tested in Firefox
- [ ] Tested in Safari (if applicable)
- [ ] Tested on mobile device
- [ ] Tested with screen reader (basic check)
- [ ] Tested keyboard navigation

### Smoke Test
- [ ] Can create {EntityName}
- [ ] Can view {EntityName}
- [ ] Can edit {EntityName}
- [ ] Can delete {EntityName}
- [ ] Can search/filter {EntityName}
- [ ] All error scenarios handled gracefully

---

## Sign-Off

### Developer
- [ ] I confirm all items above are complete
- [ ] I have tested all scenarios manually
- [ ] I have reviewed my own code
- [ ] I am confident this is production-ready

**Developer**: {DeveloperName}  
**Date**: {Date}  
**Signature**: _________________

### Reviewer
- [ ] I have reviewed the code
- [ ] I have tested the feature
- [ ] All DoD items verified
- [ ] Approved for merge

**Reviewer**: {ReviewerName}  
**Date**: {Date}  
**Signature**: _________________

---

## Placeholder Reference

- `{FeatureName}` - Feature name
- `{FeatureScreenID}` - Screen ID
- `{feature-slug}` - Branch slug
- `{ReviewerName}` - Code reviewer name
- `{Date}` - Current date
- `{UnitTestCount}` - Number of unit tests
- `{IntegrationTestCount}` - Number of integration tests
- `{ViewTestCount}` - Number of view tests
- `{E2ETestCount}` - Number of E2E tests
- `{CoveragePercentage}` - Actual coverage percentage
- `{CoverageTarget}` - Target coverage percentage (e.g., 80)
- `{LoadTimeTarget}` - Target page load time in ms
- `{EntityName}` - Entity being managed
- `{DeveloperName}` - Developer name
- `{ScenarioIDs}` - Scenario IDs implemented
