# Authentication

Registration validates password strength, terms acceptance, email uniqueness, and optional referral-code existence. New referral codes are eight characters (`WB` plus six unambiguous uppercase letters or digits). Existing codes remain valid after the short-code migration, so links already shared by users continue to work. Passwords are Argon2 hashes. Successful login sends a signed, HTTP-only, SameSite=Lax cookie. Logout removes that cookie.

Verification and reset values are random opaque tokens; only SHA-256 token hashes are stored with an expiration and single-use timestamp. The mock email provider never logs raw tokens. Password-reset responses do not reveal account existence.

Privileged endpoints use permission dependencies, not a broad implicit admin bypass.
