# Security Policy

Do not disclose live credentials, tokens, private keys, personal data, or unredacted secret-scan
findings in a public issue.

Report a vulnerability through GitHub private vulnerability reporting or a private security
advisory when that channel is enabled for the repository. If no private channel is available, open
a minimal public issue that contains no exploit details or sensitive values and asks the maintainers
for a private contact path.

Security-sensitive changes include remote destination handling, credential redaction, hooks and
aliases, force-with-lease behavior, destructive reset/clean paths, release provenance, and migration
cutover controls. Review these changes with the relevant high-consequence scenarios before release.

Supported versions are the latest published release and the current default branch unless a release
notice states otherwise.
