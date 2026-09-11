# List everything in an Azure Container Registry: repositories, their tags, and their
# image manifests (by digest) — using passwordless Entra ID auth.
#
# First install the SDKs (run in your terminal, not in Python):
#   python -m pip install azure-containerregistry azure-identity
#
# Then make sure you're signed in and point the script at your registry (bash/fish):
#   az login
#   export ACR_ENDPOINT="https://<login-server-from-az-acr-show>"
#
# An RBAC-only registry needs AcrPull. An ABAC-enabled registry needs Container Registry
# Repository Reader plus Container Registry Repository Catalog Lister for this catalog-wide sample.
# This sample only READS. The delete calls at the bottom are commented out on purpose.

import os        # 'import' loads a module (a library). 'os' lets us read environment variables.

# urlparse separates an URL into parts such as scheme and host. Using it is safer than manually
# removing "https://", and it also handles an accidental trailing slash in ACR_ENDPOINT.
from urllib.parse import urlparse

# `from X import y` pulls just the named class into scope (instead of the whole module).
# ContainerRegistryClient is the DATA-PLANE client — it talks to the registry's image data
# (repositories/tags/manifests), as opposed to the management plane that creates the registry.
from azure.containerregistry import ContainerRegistryClient

# DefaultAzureCredential is the "just works" credential: it tries several sources in order
# (environment vars, managed identity, your `az login` session, ...) and uses the first that
# works. In dev it picks up your `az login`; in Azure it picks up the service's managed identity.
# Either way there is NO password/secret in this file — that's the whole point.
from azure.identity import DefaultAzureCredential

# Read the registry endpoint from the environment.
# os.environ is a dict-like object of environment variables; ["..."] looks one up
# (and raises a clear KeyError if you forgot to `export` it).
endpoint = os.environ["ACR_ENDPOINT"].rstrip("/")  # e.g. https://ai200acr.azurecr.io

# Parse once so we can validate every URL component before opening a network client.
# A ParseResult is a small object with fields such as scheme, hostname, path, query, and fragment.
parsed_endpoint = urlparse(endpoint)

# A real ACR endpoint is an HTTPS origin, not a repository URL. Reject paths, query strings, and
# fragments so a value such as "https://registry.azurecr.io/repository" cannot silently produce
# misleading image references.
if (
    parsed_endpoint.scheme != "https"
    or parsed_endpoint.hostname is None
    or parsed_endpoint.path not in ("", "/")
    or parsed_endpoint.params
    or parsed_endpoint.query
    or parsed_endpoint.fragment
):
    raise ValueError("ACR_ENDPOINT must be a full URL such as https://myregistry.azurecr.io")

# The hostname is now known to exist. It can include ACR's optional DNS-name-scope hash.
login_server = parsed_endpoint.hostname


def main() -> None:
    # `-> None` is a type hint meaning "this function returns nothing". Hints are optional docs.

    # Create one credential object we can reuse for the client.
    credential = DefaultAzureCredential()

    # `with <resource> as name:` is Python's context manager. It guarantees the client is
    # cleanly CLOSED (network connections released) when the block ends — even if an error is
    # raised. It's the Pythonic way to manage a resource with a lifetime, like a file handle.
    with ContainerRegistryClient(endpoint, credential) as client:

        # list_repository_names() returns an ITERATOR that streams repository names (strings),
        # fetching pages from the registry lazily as you loop. A registry holds many repos.
        print(f"Repositories in {login_server}:")
        for repository in client.list_repository_names():
            print(f"\n=== {repository} ===")

            # --- Tags: the human labels (v1.0, latest) that point at an image ---------------
            # list_tag_properties(repo) streams one ArtifactTagProperties per tag. Each has a
            # `.name` (the tag) and a `.digest` (the sha256 of the image the tag currently
            # points at). Remember: tags are MUTABLE — the same tag can move to a new digest.
            print("  tags:")
            for tag in client.list_tag_properties(repository):
                # An f-string ({} substitutes values) builds the reference you'd `docker pull`.
                # Two ways to name the same image:
                #   by tag:    <server>/<repo>:<tag>          (mutable, convenient)
                #   by digest: <server>/<repo>@<sha256:...>   (immutable, reproducible)
                by_tag = f"{login_server}/{repository}:{tag.name}"
                by_digest = f"{login_server}/{repository}@{tag.digest}"
                print(f"    - {tag.name:<12} -> {by_tag}")
                print(f"                   (immutable: {by_digest})")

            # --- Manifests: the actual image builds, identified by digest -------------------
            # list_manifest_properties(repo) streams one ArtifactManifestProperties per image
            # build. `.digest` is its immutable id; `.tags` is the list of tags on it (an image
            # can have several tags, or none — an "untagged"/dangling manifest).
            print("  manifests (image builds by digest):")
            for manifest in client.list_manifest_properties(repository):
                # `manifest.tags or ["<untagged>"]` uses Python's `or`: if the tags list is
                # empty (falsy), fall back to the placeholder so untagged images still print.
                tag_list = ", ".join(manifest.tags or ["<untagged>"])
                print(f"    - {manifest.digest}  tags: [{tag_list}]")

        # --- How you'd DELETE (left commented out so nothing is removed by accident) --------
        # delete_tag removes just the TAG (the label), leaving the underlying image/manifest.
        # delete_manifest removes the actual IMAGE by digest. RBAC-only registries use
        # AcrDelete; ABAC-enabled registries use Container Registry Repository Contributor.
        # Uncomment and set real values only when you intend to delete data. Artifact soft delete
        # can provide a recovery window when that preview policy is enabled; without it, deletion
        # is not recoverable through ACR.
        #
        #   client.delete_tag("web-api", "v1.1")                     # remove one tag
        #   client.delete_manifest("web-api", "sha256:<digest...>")  # remove one image build

        print("\nDone. Compare this against 'Repositories' for your registry in the portal.")


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (e.g. `python app.py`), NOT when it's imported by another file. Standard Python entry point.
if __name__ == "__main__":
    main()
