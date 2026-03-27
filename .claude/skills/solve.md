---
name: solve
description: Research solutions for a problem, suggest best 3, recommend 1 that also prevents future similar issues
user_invocable: true
---

# Solve — Research, Compare, Recommend

When the user reports a problem or shows a screenshot of an issue:

## Step 1: Diagnose the Root Cause
- Read the relevant source code files
- Check server logs if applicable (VPS: ssh root@100.101.115.46)
- Identify the EXACT code path causing the issue
- Check if this is a recurring pattern (has this type of issue happened before?)

## Step 2: Search for Solutions
- Search the web for how world-class tools (Vector Magic, Vectorizer.AI, Adobe) solve this
- Search for open-source implementations and algorithms
- Search the project memory for past fixes to similar issues
- Check if the issue is in preprocessing, tracing, post-processing, or frontend

## Step 3: Propose 3 Solutions
Present exactly 3 solutions in this format:

### Solution 1: [Name]
- **What**: Brief description
- **How**: Specific code changes needed
- **Pros**: What it fixes
- **Cons**: What it doesn't fix or what it might break
- **Future-proof**: Does it prevent similar issues in the future?
- **Effort**: Low / Medium / High

### Solution 2: [Name]
(same format)

### Solution 3: [Name]
(same format)

## Step 4: Recommend ONE Solution
Choose the solution that:
1. Fixes the CURRENT issue
2. Prevents the MOST similar future issues
3. Has the LOWEST risk of breaking existing features
4. Requires the LEAST effort

Explain WHY this solution is recommended over the other two.

## Step 5: Implement
After recommendation is approved (or if user said "go"):
1. Implement the recommended solution
2. Test locally
3. Push to GitHub
4. Deploy to VPS
5. Verify the fix is live

## Rules
- Never propose a fix that only solves the symptom — always fix the root cause
- If 3 similar issues have been fixed before, propose an ARCHITECTURAL fix that prevents the entire class of issues
- Check memory files for past learnings about this type of issue
- Always consider: "Will this fix break something that's currently working?"
- Prefer fixes that make the system more robust, not more complex
- If the issue is fundamentally about the tracing engine's limitations, say so honestly instead of adding workarounds

## Common Issue Categories
- **Missing colors**: Color detection threshold, cluster count, merge distance
- **Noise/artifacts**: Preprocessing too aggressive, or not enough
- **Slow conversion**: Upscaling too high, preprocessing too heavy
- **SVG not rendering**: Namespace issues, broken XML, too large
- **Gradient problems**: Need color quantization or different tracing approach
- **Edge quality**: vtracer vs potrace, parameter tuning
- **Stray objects**: Component filter threshold, border cleanup

## Memory Check
Before proposing solutions, read these memory files for context:
- feedback_color_merge.md
- feedback_component_filter.md
- feedback_border_cleanup.md
- feedback_svg_xml.md
- project_potrace_pipeline.md
