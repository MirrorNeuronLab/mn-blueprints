# Suspicious User Activity Report

## Summary
High-risk user activity detected. Step-up authentication was required or recommended.

## Risk Level
HIGH (65 points)

## Suspicious Signals
- New device login
- New location login
- Api key created after risky login
- Large data download

## Response Taken
dry_run_recommendation_only (step_up_authentication_required)

## Evidence
- evt_001: login_success at 2026-05-11T14:00:00Z
- evt_002: new_location_login at 2026-05-11T14:08:00Z
- evt_003: api_key_created at 2026-05-11T14:10:00Z
- evt_004: large_data_download at 2026-05-11T14:12:00Z

## Candidate RMF/ATO/cATO Evidence Mapping
- Access Control
- Identification and Authentication
- Audit and Accountability
- Incident Response
- System and Communications Protection
- Security Assessment and Authorization
- Continuous Monitoring
- Risk Assessment

## Recommended Follow-up
Review API key usage and confirm whether the credential creation was legitimate.

## Compliance Caveat
Candidate evidence mappings are provided for compliance review only; this blueprint does not prove or grant RMF, ATO, cATO, FedRAMP, CMMC, or other compliance status.
