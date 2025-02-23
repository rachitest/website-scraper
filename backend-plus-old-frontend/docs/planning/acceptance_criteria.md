### Acceptance Criteria

**Feature 1: Company Report Generation**
- When a user enters a company URL (for example, "google.com"), the system will automatically trigger queries to external and internal APIs. 

**Feature 2: Speed**
- Given the external APIs involved, the UI should still provide quick feedback / responsiveness, and give the user indications of progress / speed in the absence of answering all the users questions right away. 

**Feature 3: Website Content Analysis**
- After submitting a URL, the system  attempts to scrape the provided URL and parses critical HTML elements including title tags, meta descriptions, and primary headers.
- Additional API call(s) occur with the parsed content to provide context and additional insights based on internal API determinations combined with external API sources.