# First install the SDK (run in your terminal, not in Python):
#   python -m pip install azure-identity azure-keyvault-secrets azure-keyvault-keys
#
# Then set your Key Vault URI from the CLI setup, e.g. (bash/fish):
#   export AZURE_KEYVAULT_URI="https://ai200-keyvault.vault.azure.net/"
#
# Your application will automatically authenticate using DefaultAzureCredential,
# which tries multiple methods in order: environment variables, managed identity,
# VS Code, Azure CLI, Azure PowerShell.

import os        # 'import' loads a module (a library). 'os' lets us read environment variables.
import base64   # For encoding/decoding binary data to/from Base64 strings
import time     # For generating timestamped secret names

# Import the credential and client classes from the Azure SDK.
# DefaultAzureCredential tries multiple authentication methods automatically.
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm

# Read the Key Vault URI from the environment.
# os.environ is a dict-like object of environment variables; [".."] looks one up.
# This is the URL to your Key Vault (e.g., https://ai200-keyvault.vault.azure.net/).
vault_uri = os.environ["AZURE_KEYVAULT_URI"]

# Create a credential object. DefaultAzureCredential will automatically try:
# 1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
# 2. Managed Identity (if running on Azure - VM, App Service, Function App, etc.)
# 3. Visual Studio Code
# 4. Azure CLI (if you're logged in locally with 'az login')
# 5. Azure PowerShell
# This means the same code works locally and in production without changes!
credential = DefaultAzureCredential()

# Create a SecretClient to interact with secrets in your Key Vault.
# The SecretClient provides methods to get, set, list, and delete secrets.
secret_client = SecretClient(vault_url=vault_uri, credential=credential)

# Create a KeyClient to interact with keys in your Key Vault.
# The KeyClient provides methods to create, get, list, and delete keys.
key_client = KeyClient(vault_url=vault_uri, credential=credential)


def get_secret(secret_name: str) -> str:
    # `-> str` is a type hint meaning "returns a string". Hints are optional docs; Python
    # doesn't enforce them at runtime.
    #
    # Retrieve a secret by name. The get_secret method returns a KeyVaultSecret object
    # which contains the secret name, value, and metadata (created time, expiration, etc.)
    try:
        retrieved_secret = secret_client.get_secret(secret_name)
        # The actual secret value is in the .value property
        return retrieved_secret.value
    except Exception as e:
        # Print the error and re-raise it. This helps with debugging.
        print(f"Error retrieving secret '{secret_name}': {e}")
        raise


def list_secrets() -> list:
    # `-> list` means "returns a list".
    #
    # List all secrets in the vault. This returns a generator/iterator of SecretProperties.
    # We convert it to a list so we can work with it more easily.
    try:
        # list_properties_of_secrets returns properties (metadata) of all secrets
        secret_properties = secret_client.list_properties_of_secrets()
        # Extract just the names into a list
        return [secret.name for secret in secret_properties]
    except Exception as e:
        print(f"Error listing secrets: {e}")
        raise


def encrypt_message(key_name: str, plaintext: str) -> str:
    # Encrypt a message using a key from Key Vault.
    #
    # First, get the key's ID (URI). Keys in Key Vault have unique IDs.
    try:
        key = key_client.get_key(key_name)
        key_id = key.id  # e.g., https://ai200-keyvault.vault.azure.net/keys/MyEncryptionKey/abc123
        
        # Create a CryptographyClient for this specific key.
        # This client can perform cryptographic operations using the key.
        crypto_client = CryptographyClient(key_id, credential=credential)
        
        # Encrypt the plaintext using RSA1_5 algorithm (common for RSA keys).
        # The encrypt method takes the algorithm and the plaintext (as bytes).
        plaintext_bytes = plaintext.encode("utf-8")  # Convert string to bytes
        encryption_result = crypto_client.encrypt(
            EncryptionAlgorithm.rsa1_5,
            plaintext_bytes
        )
        
        # The result is a dict with 'ciphertext' (the encrypted data as bytes).
        # Base64-encode to make it a safe string, then return as ASCII.
        return base64.b64encode(encryption_result.ciphertext).decode("ascii")
    except Exception as e:
        print(f"Error encrypting message: {e}")
        raise


def decrypt_message(key_name: str, ciphertext: str) -> str:
    # Decrypt a message using a key from Key Vault.
    try:
        key = key_client.get_key(key_name)
        key_id = key.id
        
        crypto_client = CryptographyClient(key_id, credential=credential)
        
        # Decrypt takes the algorithm and the ciphertext (as bytes).
        # Base64-decode the ciphertext string back to bytes.
        ciphertext_bytes = base64.b64decode(ciphertext)
        decryption_result = crypto_client.decrypt(
            EncryptionAlgorithm.rsa1_5,
            ciphertext_bytes
        )
        
        # The result contains the plaintext as bytes. Convert back to string.
        return decryption_result.plaintext.decode("utf-8")
    except Exception as e:
        print(f"Error decrypting message: {e}")
        raise


def demonstrate_secret_rotation():
    # Demonstrate how secret rotation works with versioning.
    #
    # Use a timestamped secret name to avoid conflicts with pre-existing versions
    secret_name = f"RotationDemoSecret-{int(time.time())}"
    
    print("\n=== Secret Rotation Demo ===")
    
    # Set initial value
    print("Setting initial secret value...")
    secret_client.set_secret(secret_name, "initial-value-v1")
    print(f"Version 1: {get_secret(secret_name)}")
    
    # Update the secret (creates version 2)
    print("Updating secret value...")
    secret_client.set_secret(secret_name, "updated-value-v2")
    print(f"Version 2 (latest): {get_secret(secret_name)}")
    
    # Get a specific version
    print("\nGetting version 1 explicitly...")
    # To get a specific version, we need its version ID (the GUID part of the URL)
    secret_versions = list(secret_client.list_properties_of_secret_versions(secret_name))
    if len(secret_versions) >= 1:
        # Sort by creation time to get the oldest version (version 1)
        secret_versions_sorted = sorted(secret_versions, key=lambda v: v._attributes.created)
        first_version_id = secret_versions_sorted[0].id
        # Extract just the version GUID from the full version ID URL
        # Version ID format: https://{vault}.vault.azure.net/secrets/{name}/{version-guid}
        version_guid = first_version_id.split("/")[-1]  # Get the last part of the URL
        # Get the first version
        first_version = secret_client.get_secret(secret_name, version=version_guid)
        print(f"Version 1 value: {first_version.value}")
    
    print("\nNote: Applications always get the latest version unless they specify a version.")


def main():
    # This is the entry point of the script. The 'if __name__ == "__main__":' block
    # at the bottom ensures this only runs when the file is executed directly,
    # not when imported by another file.
    
    print("=== Azure Key Vault Demo ===\n")
    
    # List all secrets in the vault
    print("Secrets in your vault:")
    secrets = list_secrets()
    for secret in secrets:
        print(f"  - {secret}")
    
    print("\n=== Retrieving Secrets ===")
    
    # Try to retrieve common secrets that were set up in the README
    try:
        db_connection = get_secret("DatabaseConnectionString")
        print(f"DatabaseConnectionString: {db_connection[:50]}... (truncated)")
    except Exception as e:
        print(f"Could not retrieve DatabaseConnectionString: {e}")
    
    try:
        api_key = get_secret("ApiKey")
        print(f"ApiKey: {api_key}")
    except Exception as e:
        print(f"Could not retrieve ApiKey: {e}")
    
    print("\n=== Encryption Demo ===")
    
    # Try encryption/decryption with a key
    try:
        plaintext = "Hello, Azure Key Vault!"
        print(f"Original message: {plaintext}")
        
        # Encrypt using MyEncryptionKey (created in the README setup)
        ciphertext = encrypt_message("MyEncryptionKey", plaintext)
        print(f"Encrypted: {ciphertext[:50]}... (Base64 encoded)")
        
        # Decrypt
        decrypted = decrypt_message("MyEncryptionKey", ciphertext)
        print(f"Decrypted: {decrypted}")
        
        if decrypted == plaintext:
            print("Success! Encryption and decryption worked.")
        else:
            print("ERROR: Decrypted text doesn't match original!")
    except Exception as e:
        print(f"Encryption demo failed: {e}")
    
    # Demonstrate secret rotation
    try:
        demonstrate_secret_rotation()
    except Exception as e:
        print(f"Rotation demo failed: {e}")
    
    print("\n=== Demo Complete ===")
    print("Your application can now:")
    print("  - Retrieve secrets from Azure Key Vault")
    print("  - Use keys for encryption/decryption")
    print("  - Handle secret rotation automatically")
    print("\nNext steps:")
    print("  1. Use these secrets in your application configuration")
    print("  2. Deploy your app to Azure with a Managed Identity")
    print("  3. Grant the Managed Identity access to this Key Vault")
    print("  4. No code changes needed - it will just work!")


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (not when imported by another file). Standard Python entry-point idiom.
if __name__ == "__main__":
    main()
