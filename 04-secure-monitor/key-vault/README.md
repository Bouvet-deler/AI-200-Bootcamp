# Azure Key Vault

**Domain:** 04 — Secure, monitor, troubleshoot Azure solutions (20–25%)
**Maps to skill:** *Secure secrets by using Azure Key Vault, including rotation and retrieval*

## What it is

**Azure Key Vault** is a managed service for protecting three kinds of sensitive material:

- **Secrets** — opaque values such as passwords, API keys, and connection strings.
- **Keys** — cryptographic keys used for operations such as encrypt, decrypt, sign, and verify.
- **Certificates** — X.509 certificates and their associated keys and lifecycle metadata.

An application should not contain a Key Vault credential in its source code. An Azure-hosted
application normally uses a **managed identity**: Microsoft Entra ID authenticates that identity,
and Azure role-based access control (**Azure RBAC**) decides which vault operations it may perform.

```text
application
   │  1. DefaultAzureCredential obtains a Microsoft Entra token
   ▼
Key Vault data endpoint (https://<vault-name>.vault.azure.net)
   │  2. Azure RBAC checks whether the identity may read the secret
   ▼
requested secret version
```

The application receives a secret only at runtime. This removes hard-coded credentials, but it
does **not** make secret handling risk-free: do not log the value, keep permissions narrow, and
refresh any cache when the secret rotates.

## Why it's on the exam

The AI-200 objective names two operations directly: **retrieval** and **rotation**. Expect a
scenario to test whether you can:

- authenticate with `DefaultAzureCredential` and a managed identity;
- grant the correct **data-plane** role, such as **Key Vault Secrets User**;
- retrieve the latest secret or an explicitly versioned secret with the Python SDK;
- distinguish creating a new Key Vault version from rotating the credential in its source
  system;
- use versionless identifiers and refresh cached values so consumers adopt a new version; and
- distinguish soft delete from purge protection.

## Core concepts

### Control plane and data plane

Key Vault has two permission surfaces:

| Plane | Example operations | Typical authorization |
| --- | --- | --- |
| **Control plane** | Create a vault, configure networking, or delete the vault resource | Azure RBAC management roles such as **Key Vault Contributor** |
| **Data plane** | Get or set secrets; use keys; manage certificates | Azure RBAC data roles such as **Key Vault Secrets User** or **Key Vault Secrets Officer** |

**Key Vault Contributor does not read secret values.** It manages the vault resource. For a
vault using Azure RBAC, common data roles are:

- **Key Vault Secrets User** — read secret contents;
- **Key Vault Secrets Officer** — perform secret operations except managing permissions;
- **Key Vault Reader** — read object metadata, but not sensitive values; and
- **Key Vault Administrator** — all data-plane operations on keys, secrets, and certificates,
  but not control-plane resource management or role assignments.

Azure RBAC is the recommended authorization model. The older **vault access policy** model is
legacy. Changing an existing vault from access policies to RBAC invalidates those policies, so
equivalent role assignments must exist before a production migration.

### Authentication with `DefaultAzureCredential`

`DefaultAzureCredential` is a credential chain from the `azure-identity` Python package. The
same application code can use a developer identity locally (for example, an `az login` session)
and a managed identity in Azure. Do not memorize a fixed credential-chain order: the chain has
changed as new developer credentials have been added. Know the intended pattern instead:

```text
local development: DefaultAzureCredential → developer sign-in
Azure hosting:      DefaultAzureCredential → managed identity
```

Authentication proves **who** the caller is. An RBAC role separately determines **what** that
identity may do.

### Secret identifiers and versions

Setting a secret with an existing name creates a **new immutable value version**. Older versions
remain stored under that secret until the secret is deleted; their attributes can still be
updated independently.

```text
Versionless identifier: https://<vault>.vault.azure.net/secrets/db-password
Versioned identifier:   https://<vault>.vault.azure.net/secrets/db-password/<version>
```

- A **versionless** SDK read (`get_secret("db-password")`) targets the latest version. Use this
  when a consumer should follow rotation. It does not search backward for an older version.
- A **versioned** read pins a particular version. That is useful for rollback or for decrypting
  data that must stay tied to the original material, but it will not follow rotation.

Applications often cache secrets. Creating a new version does not magically replace a value
already held in process memory. The app must read again, or use a provider with an appropriate
secret refresh interval.

### Rotation is more than a new vault version

For an external credential such as a database password, these actions must be coordinated:

1. Generate a new credential.
2. Update the database or service that validates that credential.
3. Store the new value as a new Key Vault secret version.
4. Refresh consumers and verify they use the new version.
5. Disable the old version only after the transition is safe.

Merely calling `set_secret` performs step 3; it does **not** change the password in the database.
Azure commonly automates secret rotation with a Key Vault near-expiry event, Event Grid, and an
Azure Function that updates both the source system and Key Vault.

Cryptographic **keys** have native Key Vault rotation policies that can create new key versions on
a schedule. Arbitrary **secrets** generally need an integration workflow because Key Vault cannot
know how to change the credential in the system that issued it.

### Deletion protection

- **Soft delete** is the recoverable state after deleting a vault or object. The retention period
  is configurable from 7 through 90 days and defaults to 90 days. Soft delete cannot be disabled.
- **Purge** permanently removes a soft-deleted item when permissions and policy allow it.
- **Purge protection** blocks purge until the retention period expires. Once enabled, nobody —
  including Microsoft — can disable or bypass it.

Purge protection is strongly recommended for production. The study setup below leaves it off so
you can release the globally unique demo vault name during cleanup.

## Setup

Prerequisites: an Azure subscription, [Azure CLI](https://learn.microsoft.com/cli/azure/), and
permission to create a resource group, vault, and role assignment. The examples use the
**West Europe** region. Run `az login` first.

Choose a globally unique vault name. Key Vault names are part of a public DNS name.

```bash
# Set bash/zsh variables once. Replace the vault name with a globally unique value.
RG="ai200-rg"
LOCATION="westeurope"
VAULT="<globally-unique-vault-name>"

# Create the resource group in West Europe.
az group create --name "$RG" --location "$LOCATION"

# Create a Standard vault that uses Azure RBAC for data access.
# A 7-day retention period keeps this disposable study resource recoverable briefly.
az keyvault create \
  --name "$VAULT" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku standard \
  --enable-rbac-authorization true \
  --retention-days 7

# Get the vault resource ID, which is the scope for the role assignment.
VAULT_ID="$(az keyvault show --name "$VAULT" --query id --output tsv)"

# Get the object ID of the user authenticated by 'az login'.
USER_OBJECT_ID="$(az ad signed-in-user show --query id --output tsv)"

# This study script both reads and creates secret versions, so grant Secrets Officer.
# A read-only application should normally receive the narrower Secrets User role instead.
az role assignment create \
  --assignee-object-id "$USER_OBJECT_ID" \
  --assignee-principal-type User \
  --role "Key Vault Secrets Officer" \
  --scope "$VAULT_ID"

# Seed a harmless demo value. Never put a real credential in shell history.
# A repeated 'secret set' with the same name creates a new version.
az keyvault secret set \
  --vault-name "$VAULT" \
  --name "demo-api-key" \
  --value "study-only-not-a-real-secret"

# Export the data-plane URL used by the Python sample.
export KEY_VAULT_URL="$(az keyvault show --name "$VAULT" --query properties.vaultUri --output tsv)"
```

Role assignments can take a few minutes to propagate. If the final `secret set` returns a 403
immediately after assignment, wait briefly and retry it.

For an Azure-hosted application, enable its managed identity and assign that identity **Key Vault
Secrets User** at the vault scope. The Python code remains unchanged.

## Hands-on (Python)

The sample retrieves the current secret, creates a new version with a harmless study value, and
then demonstrates latest-version and pinned-version reads. It prints version identifiers only —
never the secret values.

```bash
# Create and activate an isolated Python environment.
python -m venv venv
source venv/bin/activate

# Install the authentication and Key Vault secret clients.
python -m pip install azure-identity azure-keyvault-secrets

# KEY_VAULT_URL was exported during setup. These two have safe study defaults in app.py.
export KEY_VAULT_SECRET_NAME="demo-api-key"
export KEY_VAULT_ROTATED_VALUE="study-only-rotated-value"

python app.py
```

See [`app.py`](app.py) for the fully commented source.

## Worked examples

List the versions without printing their values:

```bash
az keyvault secret list-versions \
  --vault-name "$VAULT" \
  --name "demo-api-key" \
  --query "[].{version:id, enabled:attributes.enabled, expires:attributes.expires}" \
  --output table
```

Create another harmless version and then retrieve only its metadata:

```bash
az keyvault secret set \
  --vault-name "$VAULT" \
  --name "demo-api-key" \
  --value "study-only-version-3"

az keyvault secret show \
  --vault-name "$VAULT" \
  --name "demo-api-key" \
  --query "{id:id, enabled:attributes.enabled, created:attributes.created}" \
  --output json
```

The CLI can return the value with `--query value`, but avoid doing so in shared terminals, logs,
or shell scripts. An application should retrieve the value directly through the SDK and keep it
out of diagnostics.

## Cleanup

Deleting the resource group removes the active vault, but soft delete retains the vault name for
the configured retention period. Purge the deleted study vault if you need to release the name
immediately. These commands are destructive; verify `RG`, `VAULT`, and `LOCATION` first.

```bash
az group delete --name "$RG" --yes --no-wait

# Run this after the vault has reached the deleted state. Purging requires both that the study
# vault was created without purge protection and that your subscription-level identity has the
# deleted-vault purge permission (for example, through the Key Vault Purge Operator role).
az keyvault purge --name "$VAULT" --location "$LOCATION"
```

## Exam gotchas

- **Managed identity removes stored application credentials; it does not grant access.** Assign a
  data-plane role as well.
- **Key Vault Contributor is control-plane only.** It cannot read secret values. Use Key Vault
  Secrets User for a read-only consumer.
- **Key Vault Reader cannot read secret contents.** It reads metadata.
- **RBAC is recommended; access policies are legacy.** Do not switch a live vault's permission
  model until equivalent RBAC assignments are ready.
- **A new secret value creates a new version.** A versionless read targets the latest version;
  a versioned identifier remains pinned.
- **Creating a secret version is not complete rotation** for an external credential. The source
  system and all consumers must be coordinated.
- **Caching can delay rotation.** A consumer must refresh before it sees a new version.
- **Soft delete is not purge protection.** Soft-deleted items can normally be purged; purge
  protection prevents that until retention expires and cannot be disabled once enabled.
- **Do not log secret values.** Even a successful demo can leak a secret through terminal history,
  telemetry, exception messages, or CI output.

## Quiz yourself

Take the **Key Vault** quiz in the [quiz app](../../quiz/) (bank:
[`quiz/src/questions/04-secure-monitor/key-vault.json`](../../quiz/src/questions/04-secure-monitor/key-vault.json)).

## Further reading

- Key Vault overview: <https://learn.microsoft.com/azure/key-vault/general/overview>
- Python secret client quickstart: <https://learn.microsoft.com/azure/key-vault/secrets/quick-create-python>
- Azure RBAC guide: <https://learn.microsoft.com/azure/key-vault/general/rbac-guide>
- RBAC versus legacy access policies: <https://learn.microsoft.com/azure/key-vault/general/rbac-access-policy>
- Soft delete and purge protection: <https://learn.microsoft.com/azure/key-vault/general/key-vault-recovery>
- Secret rotation patterns: <https://learn.microsoft.com/azure/key-vault/secrets/tutorial-rotation>
- Cryptographic key rotation policies: <https://learn.microsoft.com/azure/key-vault/keys/how-to-configure-key-rotation>
