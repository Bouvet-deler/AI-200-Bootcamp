# Azure App Service Container Manager — programmatic management tool
#
# A heavily-commented Python script that uses the Azure Resource Management SDK
# (azure-mgmt-web) to manage App Service web apps running containers.
#
# What this script can do:
#   - List all web apps in a resource group
#   - Get and update app settings (environment variables for the container)
#   - Get the container configuration (image, port, startup command)
#   - List and swap deployment slots
#
# ---------------------------------------------------------------------------
# First install the dependencies (run in your terminal, NOT inside Python):
#   python -m pip install azure-mgmt-web azure-identity
#
# BEFORE running, authenticate to Azure (this populates the credentials):
#   az login
#
# Then set these environment variables (or pass --subscription-id / --resource-group):
#   export AZURE_SUBSCRIPTION_ID=$(az account show --query id --output tsv)
#   export AZURE_RESOURCE_GROUP="ai200-rg"
#   export AZURE_APP_NAME="ai200-app..."
#
# Then run it:
#   python app.py                         # lists all apps in the resource group
#   python app.py --list-apps             # same as above
#   python app.py --get-settings          # show app settings (env vars) for one app
#   python app.py --get-container-config # show container image/port/config
#   python app.py --list-slots            # list deployment slots
#
# Note: This script uses the management plane SDK, so you need Contributor
# (or higher) role on the resource group. It reads the same credentials
# that `az login` created.
# ---------------------------------------------------------------------------

import os
import argparse

# `from X import y` pulls just the named class into scope.
#   - WebSiteManagementClient: the main client for managing App Service resources
#   - models: the data classes (Site, SiteConfig, NameValuePair, etc.)
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import Site, SiteConfig, NameValuePair

# DefaultAzureCredential is the "just works" credential: it tries several sources
# in order (environment vars, managed identity, your `az login` session, ...) and
# uses the first that works. In dev it picks up your `az login`; in Azure it picks
# up the service's managed identity. No password/secret in this file.
from azure.identity import DefaultAzureCredential


# Read configuration from environment variables, with sensible defaults.
# os.environ.get("NAME", fallback) returns the variable's value, or the fallback
# if it isn't set — unlike os.environ["NAME"], it never raises when missing.
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "ai200-rg")
APP_NAME = os.environ.get("AZURE_APP_NAME")


# Create one credential object we can reuse for the client.
# DefaultAzureCredential() automatically uses the most appropriate credential
# available in your environment (interactive browser, VS Code, Azure CLI, etc.).
credential = DefaultAzureCredential()

# Create the WebSiteManagementClient — the entry point for all App Service operations.
# The client reads your default subscription from the environment if you don't
# pass subscription_id here. We pass it explicitly so the script works even when
# you have multiple subscriptions.
client = WebSiteManagementClient(credential, SUBSCRIPTION_ID)


def print_header(title: str) -> None:
    """Print a major section banner with a rule line above and below."""
    # A "docstring" (the triple-quoted string right under a function definition)
    # documents what the function does. It's good practice and is extracted by
    # tools like pydoc. `-> None` is a type hint meaning this function returns nothing.
    #
    # f"...{var}..." is an f-string: Python substitutes {var} with the value of var.
    # The :^70 centers the title in a 70-character-wide field.
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_divider(label: str) -> None:
    """Print an indented sub-divider like '---- containers ----'."""
    # " " * 2 builds a string of 2 spaces (the left margin).
    # f"  ---- {label} ----" builds the divider line with the label inside.
    # max(0, ...) ensures we never pass a negative number to the string repeat.
    pad = " " * 2
    line = f"---- {label} ----"
    print(f"{pad}{line}")


def list_apps_in_resource_group() -> None:
    """List every Web App in the configured resource group."""
    print_header("Web Apps in resource group: " + RESOURCE_GROUP)

    # client.web_apps.list_by_resource_group() returns a Paged iterator that streams
    # all the Site objects in that group. We loop through them one by one.
    # A Site object represents one App Service web app.
    apps = client.web_apps.list_by_resource_group(RESOURCE_GROUP)

    if not apps:
        print("  (no web apps found)")
        return

    for app in apps:
        # Each Site has: name, id, host_names (list), state, and many more fields.
        # app.name is the short name you gave it (e.g. "ai200-app123").
        # app.host_names is a list of URLs; the first is the default hostname.
        default_host = app.host_names[0] if app.host_names else "(none)"
        # app.state is a string like "Running" or "Stopped".
        print(f"  - {app.name}")
        print(f"      Hostname: {default_host}")
        print(f"      State:    {app.state}")

        # If this app is a Linux container, show its image.
        # app.site_config is a SiteConfig object that holds container settings.
        if app.site_config and app.site_config.linux_fx_version:
            # linux_fx_version looks like "DOCKER|<image>" for container apps.
            fx_version = app.site_config.linux_fx_version
            if fx_version.startswith("DOCKER|"):
                image = fx_version.split("|", 1)[1]  # Split on first "|" and take part 2
                print(f"      Image:    {image}")
        print()


def get_app_settings(app_name: str) -> None:
    """Get all application settings (environment variables) for one app."""
    print_header(f"App Settings for: {app_name}")

    # client.web_apps.get() fetches the full Site object for one app.
    app = client.web_apps.get(RESOURCE_GROUP, app_name)

    # app.site_config is None until you set config, so `or SiteConfig()` gives us
    # an empty SiteConfig to safely loop over when settings aren't set yet.
    config = app.site_config or SiteConfig()

    # config.app_settings is a dict-like object of name-value pairs.
    # Each pair becomes an environment variable in the container.
    settings = config.app_settings or {}

    if not settings:
        print("  (no app settings configured)")
        return

    print("  Environment variables:")
    for name, value in settings.items():
        # Some values can be very long (e.g. connection strings). Truncate to 60 chars.
        display_value = value if len(value) <= 60 else value[:57] + "..."
        print(f"    {name} = {display_value}")

    # Key Vault references appear as special values starting with
    # @Microsoft.KeyVault(...). They're resolved at runtime.
    kv_refs = {k: v for k, v in settings.items() if v.startswith("@Microsoft.KeyVault")}
    if kv_refs:
        print()
        print("  Key Vault references (resolved at runtime):")
        for name, value in kv_refs.items():
            print(f"    {name} = {value}")


def get_container_config(app_name: str) -> None:
    """Get the container-specific configuration for one app."""
    print_header(f"Container Configuration for: {app_name}")

    app = client.web_apps.get(RESOURCE_GROUP, app_name)
    config = app.site_config or SiteConfig()

    # linux_fx_version: for Linux container apps this is "DOCKER|<image>"
    linux_fx = config.linux_fx_version or ""
    # windows_fx_version: same idea for Windows containers
    windows_fx = config.windows_fx_version or ""

    if linux_fx.startswith("DOCKER|"):
        image = linux_fx.split("|", 1)[1]
        print(f"  Image:            {image}")
        print(f"  OS:              Linux")
    elif windows_fx.startswith("DOCKER|"):
        image = windows_fx.split("|", 1)[1]
        print(f"  Image:            {image}")
        print(f"  OS:              Windows")
    else:
        print("  (not a container app — or container config not set)")
        return

    # Other container-specific settings in SiteConfig:
    #   - docker_container_startup_command: startup command override
    #   - docker_container_startup_file: startup file override
    #   - docker_container_port: the port the container listens on
    if config.docker_container_startup_command:
        print(f"  Startup command:  {config.docker_container_startup_command}")
    if config.docker_container_startup_file:
        print(f"  Startup file:    {config.docker_container_startup_file}")
    if config.docker_container_port:
        print(f"  Port:            {config.docker_container_port}")
    if config.docker_container_registry_server_url:
        print(f"  Registry URL:    {config.docker_container_registry_server_url}")
    if config.docker_container_registry_server_user:
        print(f"  Registry user:   {config.docker_container_registry_server_user}")

    # App Service can auto-pull a new image when the tag changes (Continuous Deployment).
    if config.detailed_site_config:
        detailed = config.detailed_site_config
        if hasattr(detailed, "linux_fx_version_docker"):
            print(f"  CI/CD enabled:   {detailed.linux_fx_version_docker is not None}")


def list_deployment_slots(app_name: str) -> None:
    """List all deployment slots for one app."""
    print_header(f"Deployment Slots for: {app_name}")

    # client.web_apps.list_slots() returns all the slots for this app.
    slots = client.web_apps.list_slots(RESOURCE_GROUP, app_name)

    if not slots:
        print("  (no deployment slots found)")
        return

    for slot in slots:
        # Each slot is a Site object, just like the main app.
        default_host = slot.host_names[0] if slot.host_names else "(none)"
        print(f"  - {slot.name}")
        print(f"      Hostname: {default_host}")
        print(f"      State:    {slot.state}")
        if slot.site_config and slot.site_config.linux_fx_version:
            fx_version = slot.site_config.linux_fx_version
            if fx_version.startswith("DOCKER|"):
                image = fx_version.split("|", 1)[1]
                print(f"      Image:    {image}")
        print()


def swap_slots(app_name: str, source_slot: str, target_slot: str) -> None:
    """Swap two deployment slots (e.g., staging -> production)."""
    print_header(f"Swapping slots: {source_slot} -> {target_slot}")

    # client.web_apps.swap_slot() performs the swap. After swap, the source slot's
    # settings and routes move to the target, and vice-versa.
    # swap_with_production=True swaps with the production slot specifically.
    # This returns a SiteSwapEntity object with details about the swap.
    result = client.web_apps.swap_slot(
        RESOURCE_GROUP, app_name, source_slot, target_slot
    )
    print(f"  Swap initiated. Target slot after swap: {result.target_slot}")
    print(f"  Source slot after swap: {result.source_slot}")


def main() -> None:
    """Main entry point: parse arguments and run the requested operation."""
    # argparse is the standard library for parsing command-line arguments.
    # ArgumentParser builds a CLI interface with --flags.
    parser = argparse.ArgumentParser(
        description="Manage Azure App Service container apps"
    )

    # Add the sub-commands as mutually exclusive flags.
    parser.add_argument("--list-apps", action="store_true",
                        help="List all web apps in the resource group")
    parser.add_argument("--get-settings", action="store_true",
                        help="Get app settings (environment variables) for one app")
    parser.add_argument("--get-container-config", action="store_true",
                        help="Get container config (image, port, etc.) for one app")
    parser.add_argument("--list-slots", action="store_true",
                        help="List deployment slots for one app")
    parser.add_argument("--swap-slots", nargs=2, metavar=("SOURCE", "TARGET"),
                        help="Swap two deployment slots (e.g., staging production)")

    # Also allow overriding the resource group and app name on the command line.
    parser.add_argument("--subscription-id", default=SUBSCRIPTION_ID,
                        help="Azure subscription ID (default: AZURE_SUBSCRIPTION_ID env)")
    parser.add_argument("--resource-group", default=RESOURCE_GROUP,
                        help="Resource group name (default: AZURE_RESOURCE_GROUP env)")
    parser.add_argument("--app-name", default=APP_NAME,
                        help="App name (default: AZURE_APP_NAME env)")

    # Parse the arguments. args is a namespace object with one attribute per flag.
    args = parser.parse_args()

    # If the user passed a subscription ID on the command line, recreate the client.
    # We use the global keyword because client is defined at module level.
    global client
    if args.subscription_id and args.subscription_id != SUBSCRIPTION_ID:
        client = WebSiteManagementClient(credential, args.subscription_id)

    # If no flag was passed, default to listing apps.
    if not any(vars(args).values()):
        args.list_apps = True

    # Run the requested operation.
    if args.list_apps:
        list_apps_in_resource_group()
    elif args.get_settings:
        if not args.app_name:
            print("ERROR: --app-name is required for --get-settings")
            return
        get_app_settings(args.app_name)
    elif args.get_container_config:
        if not args.app_name:
            print("ERROR: --app-name is required for --get-container-config")
            return
        get_container_config(args.app_name)
    elif args.list_slots:
        if not args.app_name:
            print("ERROR: --app-name is required for --list-slots")
            return
        list_deployment_slots(args.app_name)
    elif args.swap_slots:
        if not args.app_name:
            print("ERROR: --app-name is required for --swap-slots")
            return
        swap_slots(args.app_name, args.swap_slots[0], args.swap_slots[1])


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (e.g. `python app.py`), NOT when it's imported by another file. Standard Python entry point.
if __name__ == "__main__":
    main()
