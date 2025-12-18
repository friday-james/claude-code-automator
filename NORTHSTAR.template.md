# Project North Star

> This file defines the vision and goals for this project. The auto-improvement daemon
> will iterate towards these goals, making incremental progress with each run.
>
> Customize this file to match your project's specific needs and priorities.

## Vision

A high-quality, well-maintained codebase that is secure, performant, and easy to work with.

---

## Goals

### Code Quality
- [ ] Clean, readable code with consistent style
- [ ] No code duplication (DRY principle)
- [ ] Functions and classes have single responsibilities
- [ ] Meaningful variable and function names
- [ ] Appropriate use of design patterns

### Bug-Free
- [ ] No runtime errors or crashes
- [ ] All edge cases handled properly
- [ ] No logic errors in business logic
- [ ] No race conditions or concurrency issues

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No command injection risks
- [ ] No hardcoded secrets or credentials
- [ ] Proper input validation on all user inputs
- [ ] Secure authentication and authorization

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms (no unnecessary O(n²) where O(n) works)
- [ ] Appropriate caching where beneficial
- [ ] No memory leaks

### Testing
- [ ] Unit tests for critical business logic
- [ ] Integration tests for key workflows
- [ ] Edge cases covered in tests
- [ ] Tests are meaningful, not just for coverage

### Documentation
- [ ] Public APIs and functions are documented
- [ ] Complex logic has explanatory comments
- [ ] README is up to date
- [ ] Type hints where applicable

### User Experience
- [ ] Clear, helpful error messages
- [ ] Good feedback for user actions
- [ ] Intuitive interfaces
- [ ] Accessible to all users (a11y)

### Code Health
- [ ] No dead or unused code
- [ ] No unused imports or variables
- [ ] No commented-out code blocks
- [ ] Modern language features used appropriately

---

## Priority Order

1. **Security** - Fix any security vulnerabilities first
2. **Bugs** - Fix any bugs that affect functionality
3. **Tests** - Add tests to prevent regressions
4. **Code Quality** - Improve maintainability
5. **Performance** - Optimize where it matters
6. **Documentation** - Help future developers
7. **UX** - Improve the user experience
8. **Cleanup** - Remove cruft and modernize

---

## Notes

- Focus on incremental improvements
- Don't over-engineer; keep it simple
- Prioritize impact over perfection
- Mark items as [x] when complete
