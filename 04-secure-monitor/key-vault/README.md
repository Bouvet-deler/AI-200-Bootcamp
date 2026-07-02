# Azure Key Vault

**Domain:** 04 — Secure, monitor, troubleshoot Azure solutions (20–25%)
**Maps to skill:** *Secure secrets by using Azure Key Vault, including rotation and retrieval*

> This is the **fully-written reference topic** for Azure Key Vault. Other topic guides should match
> its depth, structure, and comment style. See [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md).

---

## What it is

**Azure Key Vault** is a **centralized, cloud-hosted service** for securely storing and managing **secrets, keys, and certificates** used by your applications and services. It solves the critical problem of **hardcoded credentials** in configuration files, connection strings, or source code — a major security anti-pattern.

Think of it as a **digital safe deposit box** in the cloud. Your application never stores sensitive data; instead, it retrieves it at runtime from Key Vault using its own Azure identity.

Three types of things you can store:

- **Secrets** — connection strings, passwords, API keys, and other sensitive configuration values (up to 25 KB each). These are the most commonly used for application development.
- **Keys** — cryptographic keys for encryption, decryption, signing, and verification. Key Vault can manage RSA and EC keys, or you can import your own.
- **Certificates** — X.509 certificates that can be used for TLS/SSL and authentication. Key Vault can provision certificates from integrated Certificate Authorities or import existing ones.

> Mental model: Your app → **Azure AD Identity** (managed identity or service principal) → **Key Vault** (retrieves secrets/keys/certs) → Your app uses them at runtime. Secrets never appear in code or config.

Key Vault provides:
- **Centralized management** — one place to store, update, and audit all sensitive data
- **Access control** — fine-grained permissions via Azure RBAC or Key Vault-specific access policies
- **Audit logging** — every access and operation is logged for compliance
- **Automatic rotation** — certificates can be automatically rotated via policy configuration; secrets require manual updates (applications get the latest version on next read)
- **High availability** — 99.9% SLA with automatic failover

---

## Quick Start (2 minutes)

Want to try Key Vault right now? Run these commands:

```bash
# 0. (One-time per subscription) Register the Microsoft.KeyVault resource provider
#    Only needed the first time you use Key Vault in this subscription
az provider register --namespace Microsoft.KeyVault --wait

# 1. Create a resource group
az group create --name kv-demo-rg --location westeurope

# 2. Create your Key Vault with RBAC enabled (name must be globally unique)
#    Note: RBAC is the modern, recommended authorization model
#    --name can be shortened to "-n"
#    --resource-group can be shortened to "-g"
#    --location can be shortened to "-l"
az keyvault create \
  --name kv-demo-<yourname> \
  --resource-group kv-demo-rg \
  --location westeurope \
  --sku standard \
  --enable-rbac-authorization true

# 3. Grant yourself Key Vault permissions (no objectId needed!)
#    Replace <subscription-id> and <user-email> with your values from:
#    - Subscription: az account show --query id --output tsv
#    - Email:       az account show --query user.name --output tsv
az role assignment create \
  --assignee "<user-email>" \
  --role "Key Vault Secrets Officer" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/kv-demo-rg/providers/Microsoft.KeyVault/vaults/kv-demo-<yourname>"

# Wait 30-60 seconds for role assignment to propagate
sleep 60

# 4. Store and retrieve your first secret
az keyvault secret set \
  --name MyFirstSecret \
  --vault-name kv-demo-<yourname> \
  --value "Hello, Key Vault!"

# 5. Retrieve the secret value
az keyvault secret show \
  --name MyFirstSecret \
  --vault-name kv-demo-<yourname> \
  --query value --output tsv
```

> **Note:** When you create a vault via CLI, your user account does **not** automatically get access. Step 3 above grants you the necessary permissions. When creating via the Azure Portal, your account does get automatic access.

> **Cleanup when done:** `az group delete --name kv-demo-rg --yes --no-wait`

---

## Why it's on the exam

The skill bullet is literally *"Secure secrets by using Azure Key Vault, including rotation and retrieval."* Expect the exam to:

- Ask you to **identify the best service** for storing sensitive configuration data (Key Vault vs App Configuration vs Storage Account)
- Test **retrieval patterns** — how applications access secrets at runtime (managed identity vs service principal vs connection strings)
- Cover **rotation** — how secrets can be updated without redeploying applications
- Test **access control** — who can read, write, delete, recover secrets
- Ask about **key types** — when to use secrets vs keys vs certificates
- Cover **integration** — how Key Vault works with App Configuration, Azure Functions, VMs, and other services
- Test **CLI/SDK usage** — creating vaults, storing secrets, retrieving values

You must understand:
- The **difference between secrets, keys, and certificates** and when to use each
- **Managed identity** as the preferred way to authenticate (no credentials in code)
- **Access policies** and **RBAC** for controlling access
- **Soft delete and purge protection** for disaster recovery
- **Secret versioning** and how it enables safe rotation

---

## Core concepts

### The three object types

| Type | Use Case | Storage Format | Max Size |
| --- | --- | --- | --- |
| **Secret** | Connection strings, passwords, API keys | Key-value pairs (string) | 25 KB |
| **Key** | Cryptographic operations (encrypt/decrypt, sign/verify) | RSA, EC, octet (symmetric) | 4 KB (RSA/EC) |
| **Certificate** | TLS/SSL certificates, code signing | X.509 (PKCS#12 or PEM) | 20 KB |

### Authentication and authorization

**Authentication** — "Who are you?" Your app proves its identity to Key Vault.
- **Managed Identity** (recommended) — Azure automatically creates and manages an identity for your VM, App Service, Function App, or other Azure resources. No credentials to manage.
- **Service Principal** — A standalone identity in Azure AD that your app uses. Requires client ID and secret/certificate.
- **User Identity** — For development/testing, a user with appropriate permissions.

**Authorization** — "What are you allowed to do?" After authentication, Key Vault checks permissions.
- **Access Policies** (vault-specific) — Granular control over operations (get, list, set, delete, recover, purge) on secrets, keys, or certificates
- **Azure RBAC** (recommended for new deployments) — Role-based access using standard Azure roles (Key Vault Reader, Key Vault Secrets User, etc.)

> **Important:** Managed Identity + RBAC is the modern, recommended approach. Access Policies are legacy but still widely used.

### Secret lifecycle

1. **Create** — `az keyvault secret set --name mySecret --vault-name myVault --value myValue`
2. **Version** — Every change creates a new version; old versions are kept for recovery
3. **Retrieve** — `az keyvault secret show --name mySecret --vault-name myVault` (gets the latest version)
4. **Rotate** — Update the secret value (using `az keyvault secret set --name mySecret --vault-name myVault --value newValue`); applications get the new value **only when they re-read** the secret (not automatically if cached)
5. **Disable/Delete** — Secrets can be disabled (still exists but can't be read) or deleted (soft-deleted by default, using `az keyvault secret delete --name mySecret --vault-name myVault`)
6. **Purge** — Permanent deletion (requires purge protection to be disabled, using `az keyvault secret purge --name mySecret --vault-name myVault`)

### Key Vault tiers

| Tier | Use Case | SLA | Features |
| --- | --- | --- | --- |
| **Standard** | Most production scenarios | 99.9% | Secrets, Keys (RSA 2048/3072/4096, EC P-256/P-384/P-521), Certificates, HSM-backed keys |
| **Premium** | Compliance, HSM requirements | 99.9% | Everything in Standard + HSM-backed keys, hardware-backed keys, premium certificate issuance |

> **Exam tip:** Standard tier is sufficient for most AI-200 scenarios. Premium is needed for FIPS 140-2 Level 2/3 compliance.

### Access control models

| Model | Scope | Management | Best For |
| --- | --- | --- | --- |
| **Access Policies** | Per-vault | Vault-specific UI/CLI | Legacy, fine-grained control |
| **Azure RBAC** | Per-vault or management group | Standard Azure RBAC | New deployments, consistency with other Azure resources |

**Common RBAC roles:**
- **Key Vault Reader** — Read metadata (list secrets/keys/certs) but not values
- **Key Vault Secrets User** — Read secret values, list, get
- **Key Vault Secrets Officer** — All secret operations (read, write, delete, recover)
- **Key Vault Contributor** — Manage the vault itself (not the contents)
- **Key Vault Administrator** — Full control over vault and contents

### Network security

- **Public endpoint** — Accessible over the public internet (default)
- **Private endpoint** — Accessible only through a private network (VNet)
- **Firewall** — Restrict access to specific IP ranges or VNets
- **Service endpoints** — Allow traffic from specific Azure services without going over the public internet

> **Exam gotcha:** Even with firewall rules, Azure services (like Azure Functions, App Services) can access Key Vault using service endpoints or managed identity without requiring public internet access.

---

## Setup

Goal: create an Azure Key Vault, store a secret, and configure access for your application.

> **Two methods available:**
> - **[CLI Setup](#cli-setup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-setup)** — Point-and-click in your browser

### CLI Setup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first).
Replace the `<placeholders>`.

```bash
# 1. Create the resource group (replace <resource-group> with your name).
az group create --name <resource-group> --location westeurope

# 2. Create the Key Vault (replace <vault-name> with your globally unique name).
#    --enabled-for-deployment: allows Azure Resource Manager to deploy certificates from this vault
#    --enabled-for-disk-encryption: allows Azure Disk Encryption to use keys from this vault
#    --enabled-for-template-deployment: allows Azure Resource Manager templates to use this vault
#    --sku standard: Standard tier (premium for HSM-backed keys)
#    --soft-delete-retention-days 7: keeps deleted items for 7 days before permanent deletion
az keyvault create \
  --name <vault-name> \
  --resource-group <resource-group> \
  --location westeurope \
  --enabled-for-deployment true \
  --enabled-for-disk-encryption true \
  --enabled-for-template-deployment true \
  --sku standard \
  --soft-delete-retention-days 7 \
  --enable-rbac-authorization true

# 3. Grant yourself permissions using RBAC (recommended).
#    Replace <subscription-id> and <user-email> with your values from:
#    - Subscription: az account show --query id --output tsv
#    - Email:       az account show --query user.name --output tsv
#    Grant both secret and key permissions (app.py needs both)
az role assignment create \
  --assignee "<user-email>" \
  --role "Key Vault Secrets Officer" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.KeyVault/vaults/<vault-name>"
az role assignment create \
  --assignee "<user-email>" \
  --role "Key Vault Crypto Officer" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.KeyVault/vaults/<vault-name>"

# Wait 30-60 seconds for role assignments to propagate
sleep 60

# 4. Store your first secret (a database connection string).
#    The secret name becomes the identifier you use to retrieve it.
#    The value is the actual sensitive data.
az keyvault secret set \
  --name "DatabaseConnectionString" \
  --vault-name <vault-name> \
  --value "Server=my-server.database.windows.net;Database=my-db;User Id=admin;Password=SuperSecret123!;"

# 4. Store an API key secret.
az keyvault secret set \
  --name "ApiKey" \
  --vault-name <vault-name> \
  --value "abc123def456ghi789jkl012mno345"

# 5. Create a key for encryption.
#    This creates an RSA 2048-bit key that can be used for encryption/decryption.
#    Note: Hardware protection requires Premium tier; Standard tier uses software protection
az keyvault key create \
  --name "MyEncryptionKey" \
  --vault-name <vault-name> \
  --kty RSA \
  --size 2048 \
  --hardware-protected false

# 6. List all secrets in your vault.
az keyvault secret list --vault-name <vault-name>

# 7. Retrieve a specific secret value (this will output the value).
#    The --query 'value' extracts just the secret value from the JSON output.
#    The --output tsv formats it as plain text (no quotes).
az keyvault secret show \
  --name "DatabaseConnectionString" \
  --vault-name <vault-name> \
  --query "value" \
  --output tsv

# 8. Get the Key Vault URI (needed for your application configuration).
#    This returns the base URI for your vault.
az keyvault show --name <vault-name> --query "properties.vaultUri" --output tsv
```

### Portal Setup (Web UI)

Prefer the browser? Create the same resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Create Resource Group:**
   - Click **Resource groups** → **+ Create**
   - Name: `ai200-rg` (or your chosen name)
   - Region: `West Europe` (or your preference)
   - Click **Review + create** → **Create**

3. **Create Key Vault:**
   - Click **+ Create a resource** → Search for "Key Vault" → **Create**
   - Subscription: your subscription
   - Resource group: `ai200-rg` (the one you just created)
   - Key Vault name: `ai200-keyvault` (must be globally unique — 3-24 characters, alphanumeric)
   - Region: `West Europe` (match your resource group)
   - Pricing tier: **Standard**
   - Days to retain deleted vaults: **7** (soft delete retention)
   - Enable soft delete: **Yes** (recommended)
   - Enable purge protection: **Enabled** (prevents accidental permanent deletion)
   - **Review + create** → **Create**

4. **Add a Secret:**
   - Navigate to your Key Vault (`ai200-keyvault`)
   - In the left menu, under **Objects**, select **Secrets**
   - Click **+ Generate/Import**
   - Upload options: **Manual**
   - Name: `DatabaseConnectionString`
   - Value: `Server=my-server.database.windows.net;Database=my-db;User Id=admin;Password=SuperSecret123!;`
   - Set activation date / expiration date: Leave blank (optional)
   - Enabled: **Yes**
   - Click **Create**

5. **Add an API Key Secret:**
   - Repeat the above process
   - Name: `ApiKey`
   - Value: `abc123def456ghi789jkl012mno345`
   - Click **Create**

6. **Create a Key:**
   - In the left menu, under **Objects**, select **Keys**
   - Click **+ Generate/Import**
   - Upload options: **Generate**
   - Name: `MyEncryptionKey`
   - RSA key size: **2048**
   - Hardware protection: **No** (for Standard tier)
   - Click **Create**

7. **Note the Vault URI:**
   - In the **Overview** section of your Key Vault
   - Copy the **Vault URI** (e.g., `https://ai200-keyvault.vault.azure.net/`)
   - Your application will use this URI to access the vault

8. **Grant yourself access (RBAC):**
   - In your Key Vault, go to **Access Control (IAM)**
   - Click **+ Add** → **Add role assignment**
   - Select **Key Vault Secrets Officer** role and assign to your user
   - Repeat for **Key Vault Crypto Officer** role (needed for encryption demo)
   - Wait 1-2 minutes for permissions to propagate

---

## Hands-on (Python)

A sample application that retrieves secrets from Azure Key Vault using **DefaultAzureCredential**, which automatically tries multiple authentication methods in this order:

1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
2. Managed Identity (if running on Azure)
3. Local development tools
4. Azure CLI (if you're logged in locally)

This means the same code works **locally for development** and **in production** without changes.

> New to Python? The script is **heavily commented** — every non-trivial line explains both the Python idiom and the Azure concept. See [`app.py`](app.py) for the full source.

> **Remember:** Run all commands below from this folder (`04-secure-monitor/key-vault/`).

### Setup a virtual environment

```bash
# Use Python 3.11 (As of 2026-07-06, Python 3.12+ has Azure SDK compatibility issues)
# Azure SDK (azure-keyvault-keys, azure-identity) is fully tested with Python 3.11
python3.11 -m venv venv
```

### Activate the virtual environment

The activation command depends on your shell and operating system:

```bash
# --- bash/zsh (macOS/Linux) ---
source venv/bin/activate

# --- fish (macOS/Linux) ---
source venv/bin/activate.fish

# --- Windows PowerShell ---
."venv\Scripts\Activate.ps1"

# --- Windows cmd ---
venv\Scripts\activate.bat
```

### Install dependencies

```bash
# Install the Azure Key Vault SDK and DefaultAzureCredential support
# As of 2026-07-06: Use Python 3.11 (Azure SDK has compatibility issues with Python 3.12+)
# Azure SDK is fully tested with Python 3.11; Python 3.12 support is pending SDK updates
pip install azure-identity azure-keyvault-secrets azure-keyvault-keys

# If you encounter 'JsonWebKey' object has no attribute 'id' errors with Python 3.12:
# 1. Make sure you're in the activated virtual environment
# 2. Upgrade all packages: pip install --upgrade azure-identity azure-keyvault-secrets azure-keyvault-keys
# 3. Use Python 3.11 instead (recommended workaround)
```

### Set your Key Vault URI

```bash
# Set the Key Vault URI from your setup
export AZURE_KEYVAULT_URI="https://ai200-keyvault.vault.azure.net/"
```

> **For local development authentication:** The DefaultAzureCredential will use your Azure CLI login. Make sure you're logged in with `az login` and have the appropriate permissions on the Key Vault.

> **For Azure-hosted applications:** If your app runs on Azure (App Service, Function App, VM), enable a **Managed Identity** for the resource and grant it access to the Key Vault. No code changes needed!

### Run the sample

```bash
python app.py
```

The script will:
1. Retrieve the DatabaseConnectionString secret
2. Retrieve the ApiKey secret
3. Encrypt and decrypt a message using the MyEncryptionKey
4. List all secrets in the vault
5. Print the values (in a real app, you'd use these values to connect to your database, call APIs, etc.)

> **Tip:** To deactivate the virtual environment when done: `deactivate`

---

## Worked examples

After running `app.py` and verifying everything works, try these common Key Vault operations.

### Using the Azure CLI

**List all secrets with their versions:**
```bash
az keyvault secret list --vault-name ai200-keyvault
```

**Get a specific secret version:**
```bash
# List all versions of a secret
az keyvault secret list-versions --name DatabaseConnectionString --vault-name ai200-keyvault

# Get a specific version
az keyvault secret show --name DatabaseConnectionString --vault-name ai200-keyvault --version <version-id>
```

**Update (rotate) a secret:**
```bash
# Update the value - this creates a new version, old version is still accessible
az keyvault secret set \
  --name DatabaseConnectionString \
  --vault-name ai200-keyvault \
  --value "Server=my-server.database.windows.net;Database=my-db;User Id=admin;Password=NewSuperSecret456!;"
```

**Enable automatic rotation for a certificate:**
```bash
# Create a self-signed certificate with automatic renewal enabled
# Standard tier supports self-signed certificates; Premium tier supports DigiCert, GlobalSign
az keyvault certificate create \
  --name MyCertificate \
  --vault-name ai200-keyvault \
  --policy "{\"issuerName\":\"Self\",\"subjectName\":\"CN=myapp.example.com\",\"validityInMonths\":12,\"autoRenew\":true,\"renewBeforePercentage\":25}"

# Certificate will automatically renew 3 months before expiration (25% of 12 months)
# New version is created automatically; applications get the latest version on next read
```

**Grant access to a service principal:**
```bash
# First, get the service principal's object ID (requires Graph permissions)
# SP_OBJECT_ID=$(az ad sp list --display-name MyServicePrincipal --query '[0].objectId' --output tsv)

# Grant secret get permission
# az keyvault set-policy \
#   --name ai200-keyvault \
#   --object-id "<service-principal-object-id>" \
#   --secret-permissions get list

# Grant key encrypt/decrypt permissions
# az keyvault set-policy \
#   --name ai200-keyvault \
#   --object-id "<service-principal-object-id>" \
#   --key-permissions encrypt decrypt
```

**Grant access using Azure RBAC (recommended):**
```bash
# Grant Key Vault Secrets User role to a service principal
# Replace <service-principal-object-id> with the SP's object ID
az role assignment create \
  --assignee "<service-principal-object-id>" \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/ai200-rg/providers/Microsoft.KeyVault/vaults/ai200-keyvault"
```

### Using Python SDK directly

```python
# List all secrets
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://ai200-keyvault.vault.azure.net/", credential=credential)

# List all secret names
secrets = client.list_properties_of_secrets()
for secret in secrets:
    print(secret.name)

# Get a specific secret
retrieved_secret = client.get_secret("DatabaseConnectionString")
print(retrieved_secret.value)

# Create a new secret
client.set_secret("NewSecret", "my-secret-value")

# Update an existing secret (creates new version)
client.set_secret("NewSecret", "updated-secret-value")

# Delete a secret (soft delete)
from azure.keyvault.secrets import DeletedSecret
poller = client.begin_delete_secret("NewSecret")
deleted_secret = poller.result()

# Recover a deleted secret
recovered_secret = client.begin_recover_deleted_secret("NewSecret").result()
```

### Using Key Vault with Azure App Configuration

Key Vault can be **referenced from App Configuration**, allowing you to store configuration values in App Configuration while keeping the sensitive parts in Key Vault.

```bash
# Create an App Configuration store
az appconfig create \
  --name ai200-appconfig \
  --resource-group ai200-rg \
  --location westeurope \
  --sku standard

# Create a key-value that references a Key Vault secret
# For Managed Identity auth, use --auth-mode login (requires az login context)
# For production, configure the App Configuration store to use Managed Identity in the portal
az appconfig kv set \
  --name DatabaseConnectionString \
  --value "@Microsoft.KeyVault(SecretUri=https://ai200-keyvault.vault.azure.net/secrets/DatabaseConnectionString)" \
  --type vault \
  --endpoint https://ai200-appconfig.azconfig.io
```

Your application can then read from App Configuration, and it will automatically retrieve the secret from Key Vault.

---

## Troubleshooting

Common errors and their solutions when working with Azure Key Vault.

### Error: `(Unauthorized) [AggregatedAuthenticationFailure] Error validating token: 'S2S17001'`

**Cause:** Your Azure CLI login (`az login`) is authenticated, but your user account lacks the **secret set** permission on the Key Vault.

**Solutions:**

1. **Grant yourself access using RBAC (recommended):**
   ```bash
   # Enable RBAC for the vault (if not already enabled)
   az keyvault update --name <vault-name> --enabled-for-rbac-authorization true
   
   # Grant permissions using your email (no objectId needed)
   # Replace <subscription-id> and <user-email> with your values from:
   # - Subscription: az account show --query id --output tsv
   # - Email:       az account show --query user.name --output tsv
   az role assignment create \
     --assignee "<user-email>" \
     --role "Key Vault Secrets Officer" \
     --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.KeyVault/vaults/<vault-name>"
   
   # Wait 30-60 seconds for propagation
   sleep 60
   ```

2. **Create a new vault where you have full control:**
   ```bash
   # Create a resource group
   az group create --name myTestRG --location westeurope
   
   # Create a Key Vault (your account automatically gets admin access)
   az keyvault create --name myTestVault-12345 --resource-group myTestRG --location westeurope --sku standard
   
   # Now try your command with the new vault name
   az keyvault secret set --name mySecret --vault-name myTestVault-12345 --value myValue
   ```

3. **Check your current access:**
   ```bash
   # List your current permissions on a vault
   az keyvault show --name <vault-name> --query properties.accessPolicies
   ```

### Error: `(Forbidden) Caller is not authorized to perform action on resource` or `ForbiddenByRbac`

**Cause:** When you create a Key Vault via CLI, your user account does **not** automatically receive any permissions on the vault. You need to explicitly grant yourself access.

**Solutions:**
1. **Use Azure RBAC (recommended):**
   ```bash
   # Enable RBAC for the vault
   az keyvault update --name <vault-name> --enabled-for-rbac-authorization true
   
   # Grant permissions using your email (no objectId needed)
   # Replace <subscription-id> and <user-email> with your values from:
   # - Subscription: az account show --query id --output tsv
   # - Email:       az account show --query user.name --output tsv
   az role assignment create \
     --assignee "<user-email>" \
     --role "Key Vault Secrets Officer" \
     --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.KeyVault/vaults/<vault-name>"
   
   # Wait 30-60 seconds for propagation
   sleep 60
   ```
2. **Or use access policies (legacy):**
   ```bash
   # First, ensure you have Microsoft Graph permissions:
   # Run: az login --scope https://graph.microsoft.com/User.Read
   # Then get your object ID:
   # USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)
   
   # Grant full secret permissions
   # az keyvault set-policy \
   #   --name <vault-name> \
   #   --object-id "$USER_OBJECT_ID" \
   #   --secret-permissions get list set delete recover purge
   ```
3. **If the vault was created via the Azure Portal:** Your account should have automatic access. If not, wait a few minutes for permissions to propagate, or check you're using the correct subscription (`az account show`).

### Error: `az keyvault: 'vault-name' is a required parameter`

**Cause:** You forgot to specify `--vault-name` in your command.

**Solution:** Always include `--vault-name <your-vault-name>` when using Key Vault CLI commands:
```bash
az keyvault secret set --name mySecret --vault-name myVault --value myValue
az keyvault secret show --name mySecret --vault-name myVault
```

### Error: `The vault name '<name>' is already in use`

**Cause:** Key Vault names must be **globally unique** across all Azure subscriptions.

**Solutions:**
- Use a unique suffix: `myvault-12345` or `myvault-<yourname>`
- Try a different name

### Error: `Key Vault not found` or `ResourceNotFound`

**Cause:** The vault doesn't exist or you're using the wrong name/region.

**Solutions:**
- Verify the vault exists: `az keyvault list`
- Check the vault name is correct
- Verify you're in the correct subscription: `az account show`

### Error: `DefaultAzureCredential failed to acquire a token`

**Cause:** Your Python application can't authenticate. This happens when running locally without proper Azure CLI login or environment variables.

**Solutions:**
1. **Log in with Azure CLI:**
   ```bash
   az login
   ```
2. **Verify your login:**
   ```bash
   az account show
   ```

### Error: `(MissingSubscriptionRegistration) The subscription is not registered to use namespace 'Microsoft.KeyVault'`

**Cause:** Your Azure subscription hasn't been registered to use the Microsoft.KeyVault resource provider. This is a one-time registration required per subscription.

**Solutions:**
1. **Register the resource provider:**
   ```bash
   az provider register --namespace Microsoft.KeyVault
   ```
2. **Wait for registration to complete and verify:**
   ```bash
   az provider show --namespace Microsoft.KeyVault --query "registrationState"
   ```
   The command should return `"Registered"` when complete.
3. **Register and wait in one command:**
   ```bash
   az provider register --namespace Microsoft.KeyVault --wait
   ```
4. **If you lack permissions:** Ask your Azure admin to register the provider, or switch to a different subscription where Key Vault is already registered using `az account set --subscription <subscription-name-or-id>`.

---

## Cleanup

Goal: delete all resources created during setup to avoid unnecessary Azure charges.
Run this when you're done experimenting, or whenever you want to start fresh.

> **Two methods available:**
> - **[CLI](#cli-cleanup)** — Copy-paste commands below (requires [Azure CLI](https://learn.microsoft.com/cli/azure/))
> - **[Azure Portal (Web UI)](#portal-cleanup)** — Point-and-click in your browser

### CLI Cleanup

Run these in the [Azure CLI](https://learn.microsoft.com/cli/azure/) (`az login` first).
Replace <resource-group> and <vault-name> with your actual names.

```bash
# 1. Delete all secrets first (optional, but good practice)
#    Note: These loops use bash syntax. For fish/Windows, run commands individually.
#    Get all secret names and delete them
az keyvault secret list --vault-name <vault-name> --query "[].name" --output tsv | while read secret; do
  az keyvault secret delete --name "$secret" --vault-name <vault-name>
done

# 2. Delete all keys
az keyvault key list --vault-name <vault-name> --query "[].name" --output tsv | while read key; do
  az keyvault key delete --name "$key" --vault-name <vault-name>
done

# 3. Delete the entire resource group and everything in it.
# This removes: Key Vault, and any other resources in the group.
# The '--yes' flag skips the confirmation prompt. Use '--no-wait' to not wait for completion.
az group delete --name <resource-group> --yes --no-wait

# Optional: verify the resource group is gone
az group list --output table
```

> **Important:** Deleting a resource group is **permanent and immediate**. All resources in that group (Key Vault, secrets, keys, certificates) will be deleted and cannot be recovered. Even with soft delete enabled, **purge protection disabled** resources can be permanently deleted. With purge protection enabled, deleted vaults can be recovered within the retention period (7 days by default in our setup).

> **Soft Delete Note:** Even after deleting a resource group, Key Vaults with soft-delete enabled are retained in a soft-deleted state for the retention period. To completely remove them, you would need to purge, but this requires disabling purge protection first.

### Portal Cleanup (Web UI)

Prefer the browser? Delete resources in the [Azure Portal](https://portal.azure.com):

1. **Sign in** to [https://portal.azure.com](https://portal.azure.com)

2. **Delete individual secrets (optional):**
   - Navigate to your Key Vault (`ai200-keyvault`)
   - In the left menu, select **Secrets**
   - Click on each secret, then click **Delete** in the top toolbar
   - Confirm the deletion

3. **Delete the Key Vault:**
   - Navigate to your Key Vault (`ai200-keyvault`)
   - Click **Delete** in the top toolbar
   - In the confirmation blade, type the vault name to confirm
   - If purge protection is enabled, you'll need to either:
     - Wait for the soft delete retention period (7 days by default), OR
     - Temporarily disable purge protection to purge immediately
   - Click **Delete**

4. **Delete the Resource Group (recommended):**
   - Click **Resource groups** in the left menu
   - Find and click on your resource group (`ai200-rg` or your chosen name)
   - Click **Delete resource group** at the top
   - In the confirmation blade, type the resource group name to confirm
   - Click **Delete**

   This deletes **all resources** in the group in one operation.

5. **OR: Delete individual resources:**
   - Navigate to **Key Vault** (`ai200-keyvault`)
   - Click **Delete** in the top toolbar, confirm the name, and click **Delete**
   - Finally, delete the **Resource group** (now empty) if desired

> **Tip:** Deleting the resource group is faster and ensures you don't miss anything. Individual resource deletion is useful if you want to keep some resources while removing others.

> **Important:** With **purge protection enabled** (recommended for production), deleted Key Vaults are retained in a soft-deleted state for the retention period. They can be recovered during this time. To permanently delete them, purge protection must be disabled first.

---

## Exam gotchas

- **Managed Identity is the gold standard.** Exam questions often test whether you know that managed identity (not connection strings, not service principals with secrets) is the best practice for Azure-hosted applications. Your app uses its Azure identity to access Key Vault — no secrets stored anywhere.
- **Soft delete vs purge protection.** Soft delete retains deleted items for a configurable period (default 7-90 days). Purge protection prevents permanent deletion until it's disabled. **Both should be enabled in production.**
- **Secret versioning.** Every time you update a secret, a new version is created. Old versions are accessible via their version ID. Applications get the latest version by default. This enables **rotation without redeployment**.
- **Key Vault vs App Configuration.** Key Vault stores **secrets, keys, certificates**. App Configuration stores **configuration settings and feature flags**. They can work together — App Configuration can reference Key Vault secrets.
- **Access policies vs RBAC.** Access policies are Key Vault-specific and provide granular control (get, list, set, delete, recover, purge). Azure RBAC provides standard Azure roles. **RBAC is recommended for new deployments.**
- **CLI secret output.** By default, `az keyvault secret show` returns JSON with the secret value. Use `--query "value" --output tsv` to get just the value as plain text.
- **Secret name restrictions.** Secret names are **case-insensitive**, can only contain alphanumeric characters and hyphens, and cannot start or end with a hyphen. Max length is 127 characters.
- **Key Vault naming.** Key Vault names are **globally unique** across all Azure subscriptions. They must be 3-24 characters, alphanumeric only.
- **Authentication order.** DefaultAzureCredential tries: Environment variables → Managed Identity → Local development tools → Azure CLI. Know this order.
- **Network isolation.** To access Key Vault from a VNet, you need either a **private endpoint** or **service endpoints** configured. Public access with firewall rules can still allow Azure services through.
- **Certificates vs Keys.** Certificates contain a public key + private key pair with an X.509 certificate. Keys are just the key material. Use certificates when you need the full certificate (e.g., for TLS), use keys for pure cryptographic operations.
- **Certificate auto-rotation.** Certificates can auto-renew via policy (`autoRenew: true` + `validityInMonths`), but **secrets cannot** — they require manual updates or external automation.
- **Rotation impacts.** When a secret is rotated, applications **do not automatically** get the new value. They must re-read the secret. With proper caching strategies, this can happen seamlessly.
- **Cost.** Key Vault itself has a small per-operation cost, but the biggest cost risk comes from **unintended public access** leading to data exfiltration or **unused vaults** accumulating charges.
- **Regional availability.** Key Vault is a regional service. For disaster recovery, consider **geo-replication** (Premium tier) or deploying to multiple regions.
- **Service-to-service auth.** When one Azure service needs to access another (e.g., Azure Function reading from Key Vault), **managed identity** is the way to authenticate — never store connection strings or credentials.

---

## Test yourself

Try these operations against your live Key Vault. Click to reveal the solution and explanation.

<details>
<summary>Create a new secret called 'StorageAccountKey' with the value 'supersecretstoragekey123'</summary>

```bash
az keyvault secret set \
  --name "StorageAccountKey" \
  --vault-name "ai200-keyvault" \
  --value "supersecretstoragekey123"
```

**Why it works:** The `az keyvault secret set` command creates a new secret or updates an existing one. This creates version 1 of the StorageAccountKey secret.
</details>

<details>
<summary>Retrieve the value of the 'ApiKey' secret using CLI</summary>

```bash
az keyvault secret show \
  --name "ApiKey" \
  --vault-name "ai200-keyvault" \
  --query "value" \
  --output tsv
```

**Why it works:** The `--query "value"` extracts just the secret value from the JSON response, and `--output tsv` formats it as plain text without quotes.
</details>

<details>
<summary>List all versions of the 'DatabaseConnectionString' secret</summary>

```bash
az keyvault secret list-versions \
  --name "DatabaseConnectionString" \
  --vault-name "ai200-keyvault"
```

**What you'll see:** All versions of the secret, each with a unique version ID. The most recent version is the one retrieved when you don't specify a version.
</details>

<details>
<summary>Delete the 'StorageAccountKey' secret (soft delete)</summary>

```bash
az keyvault secret delete \
  --name "StorageAccountKey" \
  --vault-name "ai200-keyvault"
```

**Important:** This performs a **soft delete**. The secret is marked as deleted but can be recovered within the soft-delete retention period (7 days in our setup).
</details>

<details>
<summary>Recover the deleted 'StorageAccountKey' secret</summary>

```bash
az keyvault secret recover \
  --name "StorageAccountKey" \
  --vault-name "ai200-keyvault"
```

**Why it works:** As long as the secret is within the soft-delete retention period, you can recover it with this command.
</details>

<details>
<summary>Purge (permanently delete) the 'StorageAccountKey' secret</summary>

```bash
# First, disable purge protection (if enabled)
az keyvault update --name "ai200-keyvault" --purge-protection false

# Then purge the secret
az keyvault secret purge \
  --name "StorageAccountKey" \
  --vault-name "ai200-keyvault"
```

**WARNING:** This is **permanent and cannot be undone**. In production, keep purge protection enabled to prevent accidental permanent deletion.
</details>

<details>
<summary>Create an RSA 4096-bit key called 'LargeEncryptionKey'</summary>

```bash
az keyvault key create \
  --name "LargeEncryptionKey" \
  --vault-name "ai200-keyvault" \
  --kty RSA \
  --size 4096
```

**Note:** RSA 4096-bit keys are supported in both Standard and Premium tiers.
</details>

<details>
<summary>Encrypt a plaintext message using the 'MyEncryptionKey' key</summary>

```bash
# Encrypt using the Azure CLI (replace <key-id> with your key ID)
# Get key ID: az keyvault key show --name "MyEncryptionKey" --vault-name "ai200-keyvault" --query "key.kid" --output tsv
az keyvault key encrypt \
  --id "<key-id>" \
  --algorithm RSA1_5 \
  --value "Hello, Key Vault!"
```

**What you'll see:** The encrypted ciphertext in Base64 format.
</details>

<details>
<summary>Grant your user account read access to all secrets</summary>

```bash
# Using RBAC (recommended)
# Replace <subscription-id> and <user-email> with your values from:
# - Subscription: az account show --query id --output tsv
# - Email:       az account show --query user.name --output tsv
az role assignment create \
  --assignee "<user-email>" \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/ai200-rg/providers/Microsoft.KeyVault/vaults/ai200-keyvault"

# Wait 30-60 seconds for propagation
sleep 60

# Or using access policies (legacy - requires Graph permissions)
# USER_OBJECT_ID=$(az ad signed-in-user show --query "objectId" --output tsv)
# az keyvault set-policy --name "ai200-keyvault" --object-id "$USER_OBJECT_ID" --secret-permissions get list
```

**Why it works:** This grants your user the ability to read secret values and list secret names. Other permissions include: set, delete, recover, purge, backup, restore.
</details>

<details>
<summary>Enable Azure RBAC for your Key Vault</summary>

```bash
# Enable RBAC authorization
az keyvault update --name "ai200-keyvault" --enabled-for-rbac-authorization true

# Assign Key Vault Secrets User role to your user
# Replace <subscription-id> and <user-email> with your values from:
# - Subscription: az account show --query id --output tsv
# - Email:       az account show --query user.name --output tsv
az role assignment create \
  --assignee "<user-email>" \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/ai200-rg/providers/Microsoft.KeyVault/vaults/ai200-keyvault"
```

**Note:** Replace `<subscription-id>` and `<user-email>` with your actual values.
</details>

<details>
<summary>Create a secret that expires in 30 days</summary>

```bash
# Replace <expiration-date> with a date 30 days from now in ISO 8601 format
# Linux: date -u -d "+30 days" +"%Y-%m-%dT%H:%M:%SZ"
# macOS: date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ"
# Windows (PowerShell): (Get-Date).AddDays(30).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
az keyvault secret set \
  --name "TempSecret" \
  --vault-name "ai200-keyvault" \
  --value "temporary-value" \
  --expires "<expiration-date>"
```

**What you'll see:** The secret will be automatically disabled after the expiration date.
</details>

<details>
<summary>Disable a secret without deleting it</summary>

```bash
az keyvault secret set-attributes \
  --name "ApiKey" \
  --vault-name "ai200-keyvault" \
  --enabled false
```

**Why it works:** Disabled secrets cannot be retrieved but still exist. This is useful for temporarily disabling access without losing the secret.
</details>

<details>
<summary>Re-enable the disabled 'ApiKey' secret</summary>

```bash
az keyvault secret set-attributes \
  --name "ApiKey" \
  --vault-name "ai200-keyvault" \
  --enabled true
```

**What you'll see:** The secret becomes accessible again immediately.
</details>

---

## Quiz yourself

Take the **Azure Key Vault** quiz in the [quiz app](../../quiz/) (bank:
[`quiz/src/questions/04-secure-monitor/key-vault.json`](../../quiz/src/questions/04-secure-monitor/key-vault.json)).

---

## Further reading

- Azure Key Vault overview: <https://learn.microsoft.com/azure/key-vault/general/overview>
- Key Vault best practices: <https://learn.microsoft.com/azure/key-vault/general/best-practices>
- DefaultAzureCredential: <https://learn.microsoft.com/python/api/overview/azure/identity-readme?view=azure-python#defaultazurecredential>
- Azure Key Vault for Python: <https://learn.microsoft.com/python/api/overview/azure/keyvault-secrets-readme?view=azure-python>
- Managed identities: <https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview>
- Azure RBAC for Key Vault: <https://learn.microsoft.com/azure/key-vault/general/rbac-guide>
- Key Vault security: <https://learn.microsoft.com/azure/key-vault/general/security-overview>
