"""Inspect App Service container configuration without printing secret values.

Install and authenticate before running this file:

    python -m pip install azure-identity azure-mgmt-web
    az login
    export AZURE_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
    export AZURE_RESOURCE_GROUP="ai200-rg"

The default operation lists apps. Use ``python app.py inspect --app-name <name>``
to inspect one classic or sidecar-enabled container app.
"""

import argparse  # Python's standard command-line argument parser.
import os  # Reads configuration supplied through environment variables.

from azure.core.exceptions import HttpResponseError  # Azure SDK HTTP failures use this type.
from azure.identity import DefaultAzureCredential  # Reuses `az login` locally or managed identity in Azure.
from azure.mgmt.web import WebSiteManagementClient  # Management client for App Service resources.


def create_parser() -> argparse.ArgumentParser:
    """Define the command-line interface and its environment-backed defaults."""
    # A parser turns shell text such as `inspect --app-name demo` into named Python values.
    parser = argparse.ArgumentParser(description="Inspect App Service container apps")
    parser.add_argument(
        "operation",
        choices=("list", "inspect", "slots"),
        nargs="?",
        default="list",
        help="Operation to run; the default is list",
    )
    parser.add_argument(
        "--subscription-id",
        default=os.environ.get("AZURE_SUBSCRIPTION_ID"),
        help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID)",
    )
    parser.add_argument(
        "--resource-group",
        default=os.environ.get("AZURE_RESOURCE_GROUP", "ai200-rg"),
        help="Resource group (or set AZURE_RESOURCE_GROUP)",
    )
    parser.add_argument(
        "--app-name",
        default=os.environ.get("AZURE_APP_NAME"),
        help="App name for inspect/slots (or set AZURE_APP_NAME)",
    )
    return parser


def print_heading(title: str) -> None:
    """Print a small, consistent section heading."""
    # Multiplying a string repeats it; this produces a readable rule without a library.
    print(f"\n{title}\n{'=' * len(title)}")


def list_apps(
    client: WebSiteManagementClient,
    resource_group: str,
) -> None:
    """List every App Service app in one resource group."""
    print_heading(f"Apps in {resource_group}")

    # The SDK returns a paged iterable, so convert it to a list before testing whether it is empty.
    apps = list(client.web_apps.list_by_resource_group(resource_group))
    if not apps:
        print("(none)")
        return

    for app in apps:
        # An app can have custom hosts; default_host_name is the Azure-provided hostname.
        hostname = app.default_host_name or "(no default hostname)"
        print(f"- {app.name}: {app.state or 'unknown'} — https://{hostname}")


def classify_setting(value: str | None) -> str:
    """Describe a setting without revealing its value."""
    # Key Vault references remain reference strings in App Service configuration; the platform
    # resolves the secret for the running app. Case-folding makes the prefix test robust.
    if value and value.casefold().startswith("@microsoft.keyvault("):
        return "Key Vault reference"
    return "configured value (redacted)"


def inspect_app(
    client: WebSiteManagementClient,
    resource_group: str,
    app_name: str,
) -> None:
    """Show classic/sidecar container metadata and redacted setting names."""
    print_heading(f"Container configuration: {app_name}")

    # `get_configuration` is the correct SDK call for the full SiteConfig. The shorter Site
    # object returned by `get` does not reliably populate all configuration properties.
    config = client.web_apps.get_configuration(resource_group, app_name)
    linux_image = config.linux_fx_version or ""
    windows_image = config.windows_fx_version or ""

    if linux_image.startswith("DOCKER|"):
        print(f"Classic Linux image: {linux_image.removeprefix('DOCKER|')}")
    elif windows_image.startswith("DOCKER|"):
        print(f"Classic Windows image: {windows_image.removeprefix('DOCKER|')}")
    elif linux_image.casefold() == "sitecontainers":
        print("Container mode: sidecar-enabled Linux app")
    else:
        print("Classic container image: not configured")

    print(f"Startup command: {config.app_command_line or '(image default)'}")
    print(f"Always On: {bool(config.always_on)}")
    print(f"Managed identity used for ACR: {bool(config.acr_use_managed_identity_creds)}")

    # Sidecar-enabled apps store each container as a SiteContainer resource rather than in
    # linuxFxVersion. Don't call that endpoint for a classic app, where the resource collection
    # isn't part of the app's configuration model.
    containers = []
    if linux_image.casefold() == "sitecontainers":
        containers = list(client.web_apps.list_site_containers(resource_group, app_name))
    for container in containers:
        role = "main" if container.is_main else "sidecar"
        print(
            f"{role.capitalize()} container {container.name}: "
            f"image={container.image}, target-port={container.target_port or '(none)'}"
        )

    # `list_application_settings` returns a mapping whose values can contain credentials.
    # Print only setting names and classifications, never their raw values.
    settings_resource = client.web_apps.list_application_settings(resource_group, app_name)
    settings = settings_resource.properties or {}
    print_heading("App setting names (values redacted)")
    if not settings:
        print("(none)")
    for name in sorted(settings):
        print(f"- {name}: {classify_setting(settings[name])}")


def list_slots(
    client: WebSiteManagementClient,
    resource_group: str,
    app_name: str,
) -> None:
    """List deployment slots without changing or swapping them."""
    print_heading(f"Deployment slots: {app_name}")

    # Slots are full App Service apps with their own hostnames and configuration.
    slots = list(client.web_apps.list_slots(resource_group, app_name))
    if not slots:
        print("(none)")
        return

    for slot in slots:
        hostname = slot.default_host_name or "(no default hostname)"
        print(f"- {slot.name}: {slot.state or 'unknown'} — https://{hostname}")


def main() -> int:
    """Validate input, authenticate, run one read-only operation, and return an exit code."""
    args = create_parser().parse_args()
    if not args.subscription_id:
        print("ERROR: set AZURE_SUBSCRIPTION_ID or pass --subscription-id")
        return 2
    if args.operation in ("inspect", "slots") and not args.app_name:
        print(f"ERROR: --app-name is required for the {args.operation} operation")
        return 2

    # DefaultAzureCredential uses the developer's Azure CLI sign-in locally. In hosted Azure,
    # the same code can use a managed identity, so no password is embedded in the sample.
    credential = DefaultAzureCredential()
    client = WebSiteManagementClient(credential, args.subscription_id)

    try:
        if args.operation == "list":
            list_apps(client, args.resource_group)
        elif args.operation == "inspect":
            inspect_app(client, args.resource_group, args.app_name)
        else:
            list_slots(client, args.resource_group, args.app_name)
    except HttpResponseError as exc:
        # Azure SDK exceptions include a concise service message. Catching the expected type keeps
        # authentication/authorization/not-found failures readable without hiding Python bugs.
        print(f"Azure request failed: {exc.message}")
        return 1
    finally:
        # Both SDK objects own HTTP transports. `finally` runs on success, handled failure, or an
        # unexpected exception, so sockets are released before the process exits.
        client.close()
        credential.close()
    return 0


# Python sets __name__ to "__main__" only when this file is executed directly. Raising
# SystemExit passes our numeric result back to the shell as the process exit code.
if __name__ == "__main__":
    raise SystemExit(main())
