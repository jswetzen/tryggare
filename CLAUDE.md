The Conference Child Management System has a detailed specification in the file PROJECT_SPECIFICATION.md. TECHNICAL_DESIGN.md specifies the technical details and a high-level implementation plan is in IMPLEMENTATION_PLAN.md.

Update IMPLEMENTATION_PLAN.md to check off items that are done. Also keep CURRENT_TASKS.md up-to-date as you complete items.

The app database is running on localhost, you only need to start the dev server.
Never stop a process without asking for permission first, you've closed the root process before, stopping claude code by accident.

Task completion checklist, before considering an implementation phase complete, make sure to:
- Write tests that cover your new functionality
- IMPORTANT: Run the full test suite so there are no regressions
- Use next-devtools-mcp to analyze the application and check that it's working before consdering a task done
- Update CURRENT_TASKS.md so everything that you actually finished is checked off
- Commit all you changes to git, with clear commit messages.

**When starting work on a Next.js project, ALWAYS call the `init` tool from
next-devtools-mcp FIRST to set up proper context and establish documentation
requirements. Do this automatically without being asked.**

