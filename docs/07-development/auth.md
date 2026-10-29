---
id: api-key-auth-guide
title: API key authentication
type: reference
domain: security
module: src/app/security/auth.py
tags: [auth, api-key, t-014]
priority: 2
---
# API key authentication

Run from the repository root. Select `AUTH_BACKEND=apikey` and set
`API_KEYS_FILE=config/api_keys.json` (or an absolute path). `AUTH_BACKEND=fake`
returns the development user `dev/public/staff`; use it only for development.
Unknown backends and unreadable or invalid registries return 503.
The entire registry is validated on each request: one malformed record makes all
authenticated requests return 503 until the registry is corrected.

The Compose API mounts the host `config/` directory read-only at `/app/config`.
Keep `API_KEYS_FILE=config/api_keys.json` for this setup. For a custom registry
outside `config/`, add a read-only directory mount and set the container path.
Mount the directory so atomic file replacements remain visible after provisioning
or revocation; mounting an individual file can leave the container on its old inode.
You may copy `config/api_keys.example.json` to `config/api_keys.json` to start empty.

Generate a key in a private terminal:

```bash
python scripts/make_key.py --user-id staff-01 --department credit --role staff
python scripts/make_key.py --user-id approver-01 --department credit --role approver
```

The script prints each secret once. Store it securely and send it through the
`X-API-Key` header. Only its SHA-256 digest and `user_id/department/role` are
written to the git-ignored registry. Run provisioning commands serially to avoid
concurrent writers overwriting one another. Departments: public, credit, hr;
roles: staff, approver, service. Existing records are preserved.

The registry is a JSON object mapping lowercase SHA-256 hex digests to objects
with exactly `user_id`, `department`, `role`. Start with `{}` for no authorized keys.
To revoke a key, remove its digest entry; changes apply on the next request.
Missing or unknown keys return 401. `Depends(require_role("approver"))` returns
403 for authenticated users with another role and returns the User on success.
`/health` stays public. No approval endpoint is added by T-014.
