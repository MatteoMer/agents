Your job is to implement {FEATURE_DESCRIPTION} in this iOS app.

Make a commit and push your changes after every meaningful edit.

Use the .agent/ directory for tracking:
- .agent/TODO.md for current tasks
- .agent/PLAN.md for implementation plan
- .agent/NOTES.md for observations and decisions
- .agent/screenshots/ for UI verification screenshots

VISUAL VERIFICATION WORKFLOW:
This is critical for iOS development. After making UI changes, ALWAYS verify visually:

1. Build and run the app:
   xcodebuild -scheme {SCHEME_NAME} -destination 'platform=iOS Simulator,name=iPhone 16 Pro' build
   xcrun simctl launch booted {BUNDLE_ID}

2. Take a screenshot to verify:
   python -m ralph.simulator screenshot --context "description of expected screen" --json

3. Use the Read tool on the screenshot path to analyze visually.
   You can see the UI and determine if it matches your expectations.

4. If you need to navigate to a different screen:
   - Analyze the screenshot to find buttons/elements
   - Estimate coordinates (e.g., "Login button appears at ~200, 600")
   - Tap: python -m ralph.simulator tap --x 200 --y 600
   - Screenshot again to verify navigation worked

5. Document observations in .agent/NOTES.md

PROACTIVE SCREENSHOTS:
Take screenshots at these key moments:
- After building the app (verify it launched correctly)
- After making UI changes (verify layout matches intent)
- When debugging visual issues (see current state)
- After fixing UI bugs (confirm the fix)
- Before committing UI-related changes (final verification)

SIMULATOR COMMANDS:
```bash
# Screenshot
python -m ralph.simulator screenshot --context "..." --json

# Tap at coordinates
python -m ralph.simulator tap --x 200 --y 400

# Swipe/scroll
python -m ralph.simulator swipe --from 200,800 --to 200,200

# Type text
python -m ralph.simulator type "text to enter"

# Press home button
python -m ralph.simulator button home

# Check status
python -m ralph.simulator status --json
```

DEVELOPMENT PRIORITIES:
1. Understand the existing codebase structure
2. Plan the implementation approach
3. Implement incrementally with commits
4. Verify each UI change visually
5. Write/update tests as needed
6. Ensure the app builds and runs correctly

After each iteration, update .agent/TODO.md with progress and next steps.
