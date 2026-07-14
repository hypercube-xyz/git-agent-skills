# Release-readiness checklist

Establish:

- exact previous release tag/object and proposed version,
- authoritative version files and generated mirrors,
- semantic-version or project-specific bump policy,
- release-note categories and breaking-change evidence,
- build/test matrix and artifact provenance,
- whether dependency locks or vendored outputs are release inputs.

Use an exact range such as `<previous-tag>..<candidate>` and inspect merges/cherry-picks to avoid
duplicate or missing notes. Keep security-sensitive details out of public notes until disclosure
policy permits.

For generated artifacts, record tool version and inputs. When reproducibility matters, build twice
in clean temporary directories and compare declared outputs/hashes. A difference should be
investigated, not normalized away.
