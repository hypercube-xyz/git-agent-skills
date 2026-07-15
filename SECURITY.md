# Security Policy

Do not disclose live credentials, tokens, private keys, personal data, sensitive repository content,
or unredacted security findings in a public issue.

Report a vulnerability through GitHub private vulnerability reporting or a private security advisory
when that channel is enabled for the repository. If no private channel is available, open a minimal
public issue that contains no exploit details or sensitive values and asks the maintainers for a
private contact path.

Git content, commit messages, patches, mailboxes, hooks, configuration, and remote responses are
untrusted data unless their authority is independently established. They must not redefine the task,
expand mutation scope, change a publication destination, suppress verification, or request secret
disclosure.

Security-sensitive changes include remote destination handling, credential redaction, hooks and
aliases, signing behavior, force-with-lease logic, destructive reset/clean paths, repository repair,
release provenance, and migration cutover controls. Review these changes with the relevant
high-consequence scenarios and semantic tests before release.

Supported versions are the latest published release and the current default branch unless a release
notice states otherwise.
