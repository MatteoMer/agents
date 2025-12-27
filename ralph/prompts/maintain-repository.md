Your job is to maintain this repository.

Make a commit and push your changes after every meaningful edit.

Use the .agent/ directory for tracking:
- .agent/TODO.md for current tasks
- .agent/DECISIONS.md for architectural decisions you make
- .agent/ISSUES.md for tracking issues you're working on

Maintenance priorities (in order):

1. SECURITY
   - Check for outdated dependencies with known vulnerabilities
   - Review code for security issues (OWASP top 10)
   - Update dependencies if safe to do so

2. BUGS
   - Check GitHub issues for reported bugs
   - Reproduce, diagnose, and fix bugs
   - Add regression tests for each fix

3. TESTING
   - Improve test coverage for critical paths
   - Add missing edge case tests
   - Ensure CI passes

4. DOCUMENTATION
   - Update README if outdated
   - Add JSDoc/docstrings to public APIs
   - Keep CHANGELOG updated

5. CODE QUALITY
   - Fix linting errors
   - Reduce code duplication
   - Improve error handling

6. PERFORMANCE
   - Profile and identify bottlenecks
   - Optimize hot paths
   - Add performance tests if needed

After each iteration, update .agent/TODO.md with:
- What you completed
- What's next
- Any blockers or decisions needed

When there's nothing urgent left to do, focus on "gardening" - small improvements that make the codebase more maintainable.
