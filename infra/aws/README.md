## Security checklist

- [x] Dedicated email used for this account
- [x] Root user has MFA enabled (authenticator app)
- [x] Root user has no access keys
- [x] Daily work uses IAM user `klarity-admin` with MFA
- [x] Access keys stored in a password manager, not in the repo
- [x] IAM access to billing is activated

## Tagging rule

Every resource gets `project=Klarity`.

## CLI check

`aws sts get-caller-identity` returns the user `klarity-admin`
(account ID not recorded here on purpose).

## Weekly routine

Every Friday: check Billing, Budgets and the cost of running resources.
Stop EC2 when idle.
