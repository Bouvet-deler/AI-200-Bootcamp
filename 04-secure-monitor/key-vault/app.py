"""Retrieve and version a harmless study secret in Azure Key Vault."""

import os  # The standard 'os' module exposes environment variables to Python.

# DefaultAzureCredential lets the same code use a developer login locally and a managed
# identity after deployment to Azure. SecretClient performs data-plane secret operations.
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Environment variables keep deployment-specific names and values out of source control.
# Square-bracket lookup fails immediately with KeyError when the required vault URL is absent.
vault_url = os.environ["KEY_VAULT_URL"]

# os.environ.get(..., default) uses a harmless study value when an optional variable is absent.
secret_name = os.environ.get("KEY_VAULT_SECRET_NAME", "demo-api-key")
rotated_value = os.environ.get(
    "KEY_VAULT_ROTATED_VALUE",
    "study-only-rotated-value",
)

# The credential authenticates the caller. A Key Vault data-plane RBAC role separately
# authorizes the get/set operations made through this client.
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)

# Omitting a version asks Key Vault for the latest version of this secret.
current_secret = client.get_secret(secret_name)
current_version = current_secret.properties.version
print(f"Current version: {current_version}")

# Setting the same secret name does not overwrite the old version. Key Vault creates a new,
# immutable version. For a real database password, the database must also be updated as part
# of the rotation workflow; this SDK call alone is not complete credential rotation.
rotated_secret = client.set_secret(secret_name, rotated_value)
rotated_version = rotated_secret.properties.version
print(f"Created version: {rotated_version}")

# A second versionless read now resolves to the newly created version.
latest_secret = client.get_secret(secret_name)
print(f"Latest read resolved to: {latest_secret.properties.version}")

# Supplying the old version pins the read to that immutable version. The value is deliberately
# not printed: secrets can leak through terminal history, logs, and captured CI output.
pinned_secret = client.get_secret(secret_name, current_version)
print(f"Pinned read resolved to: {pinned_secret.properties.version}")

# Close the client explicitly so its underlying network transport can release resources.
client.close()

# The credential can own its own authentication transport, so close that resource as well.
credential.close()
