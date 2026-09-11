# First install the SDK (run in your terminal, not in Python):
#   python -m pip install azure-appconfiguration
#
# Then set the connection string from the CLI setup step (bash/fish):
#   export APPCONFIG_CONNECTION_STRING="<paste the Primary connectionString>"
#
# This sample uses the CONNECTION STRING for simplicity. For the passwordless
# (Entra ID / managed identity) alternative, see the commented block below where
# the client is created.

import os        # 'import' loads a module (a library). 'os' lets us read environment variables.

# `from X import y, z` pulls just the named classes into scope (instead of the whole module).
# These three classes each represent one KIND of setting you can store in App Configuration:
#   - ConfigurationSetting                -> a plain key/value
#   - FeatureFlagConfigurationSetting     -> an on/off feature flag
#   - SecretReferenceConfigurationSetting -> a pointer to a Key Vault secret
from azure.appconfiguration import (
    AzureAppConfigurationClient,
    ConfigurationSetting,
    FeatureFlagConfigurationSetting,
    SecretReferenceConfigurationSetting,
)

# Read the connection string from the environment.
# os.environ is a dict-like object of environment variables; [".."] looks one up
# (and raises a clear KeyError if you forgot to `export` it).
connection_string = os.environ["APPCONFIG_CONNECTION_STRING"]

# Create the client. `from_connection_string(...)` is a "class method" constructor —
# a common Python/Azure-SDK pattern where the class builds an instance for you from a string.
client = AzureAppConfigurationClient.from_connection_string(connection_string)

# --- Entra ID (passwordless) ALTERNATIVE -------------------------------------
# Instead of a connection string, use your Azure identity + RBAC. No secret to store.
# Requires: `pip install azure-identity`, an App Configuration "Data Reader"/"Data Owner"
# role assignment, and the store's endpoint (looks like https://<name>.azconfig.io).
#
#   from azure.identity import DefaultAzureCredential
#   endpoint = os.environ["APPCONFIG_ENDPOINT"]
#   client = AzureAppConfigurationClient(
#       base_url=endpoint,
#       credential=DefaultAzureCredential(),  # uses your `az login` (or managed identity in Azure)
#   )
# -----------------------------------------------------------------------------


def set_and_get_plain_value() -> None:
    # `-> None` is a type hint meaning "returns nothing". Hints are optional docs.
    # Build a plain key/value object. The ':' in the key is just a NAMING convention for
    # hierarchy — App Configuration stores a flat list, there are no real folders.
    setting = ConfigurationSetting(key="Ordering:MaxItemsPerPage", value="50")

    # Write it. set_configuration_setting creates the key or overwrites the existing value.
    client.set_configuration_setting(setting)

    # Read it back by key. Returns a ConfigurationSetting; `.value` is the stored string.
    fetched = client.get_configuration_setting(key="Ordering:MaxItemsPerPage")
    print(f"[plain]   {fetched.key} = {fetched.value}")


def set_and_get_labeled_values() -> None:
    # LABELS are a second axis on a key: the SAME key can hold a different value per label.
    # This is how you get per-environment config (dev vs prod) from ONE key.
    # A Python list of (label, value) tuples we loop over below.
    for label, value in [("dev", "Hello from DEV"), ("prod", "Hello from PROD")]:
        client.set_configuration_setting(
            ConfigurationSetting(key="App:Greeting", label=label, value=value)
        )

    # Read the SAME key twice, narrowing by label each time -> two different values.
    dev = client.get_configuration_setting(key="App:Greeting", label="dev")
    prod = client.get_configuration_setting(key="App:Greeting", label="prod")
    print(f"[label]   App:Greeting (dev)  = {dev.value}")
    print(f"[label]   App:Greeting (prod) = {prod.value}")


def set_and_get_feature_flag() -> None:
    # A FEATURE FLAG is really just a specially-namespaced key (prefix '.appconfig.featureflag/')
    # with a reserved content type. This helper class builds that for you so you don't hand-write
    # the JSON. Flip `enabled` to turn a feature on/off WITHOUT redeploying the app.
    flag = FeatureFlagConfigurationSetting(feature_id="BetaCheckout", enabled=False)
    client.set_configuration_setting(flag)

    # Read it back. get_configuration_setting returns the raw setting, whose `.value` is the
    # feature-flag JSON. We keep it simple and just show it exists + its stored value.
    fetched = client.get_configuration_setting(key=flag.key)  # flag.key includes the reserved prefix
    print(f"[flag]    {fetched.key} -> {fetched.value}")


def set_and_get_keyvault_reference() -> None:
    # A KEY VAULT REFERENCE stores a POINTER (a secret URI), NOT the secret value itself.
    # App Configuration never holds the actual secret — it holds the address in Key Vault.
    # Resolving the real value requires the app to ALSO have Key Vault access (see ../key-vault/).
    # Here we only store and read the reference; we do not fetch the secret.
    # This URI identifies an existing Key Vault secret. Keep it optional so the otherwise
    # runnable sample does not write a fake '<your-vault>' reference into a real config store.
    secret_uri = os.environ.get("KEY_VAULT_SECRET_URI")
    if not secret_uri:
        print("[kv-ref]  skipped (set KEY_VAULT_SECRET_URI to an existing secret URI)")
        return
    reference = SecretReferenceConfigurationSetting(key="App:DbPassword", secret_id=secret_uri)
    client.set_configuration_setting(reference)

    fetched = client.get_configuration_setting(key="App:DbPassword")
    # `.value` is JSON like {"uri": "https://.../secrets/db-password"} — the pointer, not the secret.
    print(f"[kv-ref]  {fetched.key} -> {fetched.value}")


def list_app_keys() -> None:
    # list_configuration_settings streams matching settings. key_filter supports '*' wildcards.
    # This mirrors the CLI `az appconfig kv list --key "App:*"`.
    print("[list]    keys matching 'App:*':")
    # A `for ... in` loop over the returned iterator; each item is a ConfigurationSetting.
    for item in client.list_configuration_settings(key_filter="App:*"):
        # An f-string with a fallback: `item.label or '(none)'` prints '(none)' when label is empty.
        print(f"          - {item.key} [label={item.label or '(none)'}]")


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (not when imported by another file). Standard Python entry-point idiom.
if __name__ == "__main__":
    try:
        # Run each small demonstration in sequence against the same reusable SDK client.
        set_and_get_plain_value()
        set_and_get_labeled_values()
        set_and_get_feature_flag()
        set_and_get_keyvault_reference()
        list_app_keys()

        print("Done. Open App Configuration > Configuration explorer in the portal to see these keys.")
    finally:
        # `finally` runs even if an Azure request fails, so network resources are still released.
        client.close()
