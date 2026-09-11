# Programmatic AKS troubleshooting tool — the SDK mirror of:
#   kubectl get pods  ->  kubectl describe / get events  ->  kubectl logs
#
# It lists pods in a namespace, flags the UNHEALTHY ones, and for each prints
# its recent events + last log lines. Then it lists Services and their endpoints
# so you can sanity-check end-to-end connectivity.
#
# ---------------------------------------------------------------------------
# First install the client (run in your terminal, NOT inside Python):
#   python -m pip install kubernetes
#
# BEFORE running, connect to your cluster (these populate the kubeconfig file):
#   az login
#   az aks get-credentials --resource-group ai200-rg --name ai200-aks --overwrite-existing
#
# Then run it, optionally choosing a namespace via an environment variable:
#   K8S_NAMESPACE=demo python app.py        # inspect the 'demo' namespace
#   python app.py                           # defaults to the 'default' namespace
# ---------------------------------------------------------------------------

import os  # 'import' loads a module (a library). 'os' lets us read environment variables.
from datetime import datetime, timezone  # Used to sort Kubernetes events by their real timestamps.

# `from X import y, z` pulls just the named things into scope.
#   - client : the classes/enums that build requests and hold responses.
#   - config : helpers that load your cluster connection details (kubeconfig).
from kubernetes import client, config

# The exception type EVERY Kubernetes API call can raise on an HTTP error
# (404 not found, 403 forbidden, etc.). We catch it so one failure doesn't crash the whole run.
from kubernetes.client.rest import ApiException


# Read the target namespace from the environment, defaulting to "default".
# os.environ.get("NAME", fallback) returns the variable's value, or the fallback
# if it isn't set — unlike os.environ["NAME"], it never raises when missing.
NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")


# load_kube_config() reads the SAME kubeconfig file (~/.kube/config) that
# `az aks get-credentials` populated. That's how this script knows WHICH cluster
# to talk to and how to authenticate — no connection string in code.
# (Inside a pod you'd instead call config.load_incluster_config().)
config.load_kube_config()

# CoreV1Api is the client for "core" objects: Pods, Services, Events, and Namespaces.
core = client.CoreV1Api()

# DiscoveryV1Api reads EndpointSlice objects. EndpointSlice is the current scalable replacement
# for the legacy Endpoints API, and shows which ready pod addresses back each Service.
discovery = client.DiscoveryV1Api()


# ---------------------------------------------------------------------------
# Tiny presentation helpers so the output reads as clear, spaced-out sections
# instead of a wall of text. None of this talks to Azure — it's pure formatting.
# ---------------------------------------------------------------------------
WIDTH = 74  # how many characters wide the separator lines are

def print_header(title: str) -> None:
    """Print a major section banner: a blank line, then the title between two '═' rules."""
    # `"═" * WIDTH` repeats the character WIDTH times — Python's quick way to draw a line.
    print()                 # blank line above the banner => visual breathing room
    print("═" * WIDTH)
    print(f"  {title}")     # two leading spaces indent the title 'inside' the banner
    print("═" * WIDTH)

def print_divider(label: str, indent: int = 8) -> None:
    """Print an indented sub-divider like '── recent events ─────────' beneath a pod."""
    pad = " " * indent                      # `" " * n` builds a string of n spaces (left margin)
    start = f"── {label} "                   # the labelled beginning of the divider
    # Right-fill with '─' so every divider ends at the same column. max(0, ...) guards against
    # a negative repeat count (which would raise) if the label is unusually long.
    print(pad + start + "─" * max(0, WIDTH - indent - len(start)))


def is_pod_healthy(pod) -> bool:
    """Return True if the pod is Running/Succeeded AND no container is stuck.

    `-> bool` is a type hint (optional documentation) meaning "returns a boolean".
    """
    # pod.status.phase is a high-level state string: Pending / Running / Succeeded / Failed.
    phase = pod.status.phase
    # A pod belonging to a completed Job is healthy even though its terminated containers are no
    # longer "ready". For a long-running workload, only Running is a healthy phase.
    if phase == "Succeeded":
        return True
    if phase != "Running":
        return False

    # Even a "Running" pod can hide a broken container (e.g. CrashLoopBackOff), so inspect
    # each container's state. container_statuses can be None before containers are created,
    # so `or []` gives us an empty list to loop over safely instead of crashing on None.
    for cs in pod.status.container_statuses or []:
        # A container in 'waiting' with a reason like 'CrashLoopBackOff' / 'ImagePullBackOff'
        # is unhealthy. cs.state.waiting is None when the container isn't waiting.
        if cs.state.waiting is not None:
            return False
        # A container not marked ready fails its readiness probe -> excluded from Services.
        if not cs.ready:
            return False
    return True


def describe_pod_container_states(pod) -> str:
    """Build a short human string of each container's state + reason (like `describe` shows)."""
    parts = []  # an empty list we'll append little strings to, then join at the end.
    for cs in pod.status.container_statuses or []:
        # A container is in exactly one of three states: waiting / running / terminated.
        if cs.state.waiting is not None:
            # e.g. reason='ImagePullBackOff', reason='CrashLoopBackOff'
            parts.append(f"{cs.name}: waiting ({cs.state.waiting.reason})")
        elif cs.state.terminated is not None:
            # e.g. reason='OOMKilled', or 'Error' with a non-zero exit code.
            parts.append(f"{cs.name}: terminated ({cs.state.terminated.reason})")
        elif cs.state.running is not None:
            parts.append(f"{cs.name}: running")
    # ", ".join(list) glues the pieces with commas; "(no containers yet)" if the list is empty.
    return ", ".join(parts) if parts else "(no containers yet)"


def total_restarts(pod) -> int:
    """Sum restart counts across the pod's containers (high restarts => CrashLoopBackOff)."""
    # A "list comprehension": build a list of restart counts, then sum() adds them up.
    # `[cs.restart_count for cs in ...]` reads: "cs.restart_count for each cs in the statuses".
    return sum(cs.restart_count for cs in (pod.status.container_statuses or []))


def print_recent_events_for_pod(pod_name: str) -> None:
    """Print the cluster events tied to one pod — the 'why did it fail' info from `describe`."""
    try:
        # A field_selector limits results server-side by object fields — here, events whose
        # involvedObject.name is our pod, rather than transferring every namespace event.
        events = core.list_namespaced_event(
            namespace=NAMESPACE,
            field_selector=f"involvedObject.name={pod_name}",
        )
    except ApiException as exc:
        # try/except: if the API call raises ApiException, we print the error and move on
        # instead of crashing. `exc` is the caught exception object.
        print(f"          (could not read events: {exc.status} {exc.reason})")
        return

    # The API does not promise chronological order. Pick each event's newest available timestamp,
    # sort descending, then slice the first five. A timezone-aware minimum keeps missing timestamps
    # comparable with the timezone-aware values returned by the client.
    minimum_time = datetime.min.replace(tzinfo=timezone.utc)
    recent = sorted(
        events.items,
        key=lambda event: (
            event.event_time
            or event.last_timestamp
            or event.metadata.creation_timestamp
            or minimum_time
        ),
        reverse=True,
    )[:5]
    if not recent:
        print("          (no events)")
        return
    for ev in recent:
        # ev.reason e.g. 'Failed', 'BackOff'; ev.message is the human explanation.
        # "• " is a bullet; the 10-space indent lines these up under the divider above.
        print(f"          • {ev.reason} — {ev.message}")


def print_container_logs(
    pod_name: str,
    container_name: str,
    *,
    previous: bool,
) -> None:
    """Print one container's current or previous logs without aborting the inspection."""
    try:
        # read_namespaced_pod_log fetches the container's stdout/stderr.
        #   tail_lines=10  -> only the last 10 lines (keeps output short).
        #   container      -> required when a pod has more than one container.
        #   previous       -> True reads the last terminated instance (`kubectl logs -p`).
        logs = core.read_namespaced_pod_log(
            name=pod_name,
            namespace=NAMESPACE,
            tail_lines=10,
            container=container_name,
            previous=previous,
        )
    except ApiException as exc:
        # A common case: 400 "container ... is waiting to start" — the container never ran,
        # so there are no logs yet (typical for ImagePullBackOff). We report and continue.
        print(f"          (could not read logs: {exc.status} {exc.reason})")
        return

    # `logs` is one big string with embedded newlines; splitlines() turns it into a list of lines.
    lines = logs.splitlines()
    if not lines:
        print("          (no log output)")
        return
    for line in lines:
        # 10-space indent so the raw log lines sit neatly under the divider above.
        print(f"          {line}")


def print_last_logs_for_pod(pod) -> None:
    """Print useful logs for every container, including a crashed previous instance."""
    # Build a dictionary so a container name quickly maps to its restart count. A dictionary
    # comprehension is Python's compact "one key/value entry for each item" syntax.
    restart_counts = {
        status.name: status.restart_count
        for status in (pod.status.container_statuses or [])
    }

    # `pod.spec.containers` contains every regular application container in the pod.
    for container_spec in pod.spec.containers:
        container_name = container_spec.name
        print(f"          [{container_name}: current]")
        print_container_logs(pod.metadata.name, container_name, previous=False)

        # If Kubernetes restarted this container, the previous log is often the only record of
        # the crash that caused CrashLoopBackOff. The API retains at most one previous instance.
        if restart_counts.get(container_name, 0) > 0:
            print(f"          [{container_name}: previous]")
            print_container_logs(pod.metadata.name, container_name, previous=True)


def inspect_pods() -> int:
    """List pods, print name/phase/restarts/node, and troubleshoot the unhealthy ones.

    Returns the count of unhealthy pods so the caller can print a summary.
    """
    print_header(f"Pods in namespace '{NAMESPACE}'")
    try:
        # list_namespaced_pod returns every pod in the namespace.
        pods = core.list_namespaced_pod(namespace=NAMESPACE)
    except ApiException as exc:
        print(f"\nCould not list pods: {exc.status} {exc.reason}")
        return 0

    if not pods.items:
        print("\n(no pods found — did you `kubectl apply` a workload to this namespace?)")
        return 0

    unhealthy = 0  # a running tally we bump by 1 for each broken pod
    for pod in pods.items:
        name = pod.metadata.name
        phase = pod.status.phase
        restarts = total_restarts(pod)
        node = pod.spec.node_name or "(unscheduled)"  # None while Pending -> show a placeholder
        healthy = is_pod_healthy(pod)

        # Put the badge FIRST so healthy vs broken pods form a scannable left-hand column.
        badge = "[ OK ]" if healthy else "[FAIL]"
        detail = " " * 8  # detail lines indent to sit under the name (6-char badge + 2 spaces)

        print()  # blank line before each pod => every pod is its own visual block
        print(f"{badge}  {name}")
        print(f"{detail}phase={phase}   restarts={restarts}   node={node}")
        print(f"{detail}containers: {describe_pod_container_states(pod)}")

        # Only dig into the pods that look broken — that's the "why is this pod broken" loop.
        if not healthy:
            unhealthy += 1
            print_divider("recent events")
            print_recent_events_for_pod(name)
            print_divider("last log lines")
            print_last_logs_for_pod(pod)

    # A one-line tally so you immediately know how bad things are, without re-scanning.
    total = len(pods.items)
    print()
    print("─" * WIDTH)
    print(f"  {total} pod(s): {total - unhealthy} healthy, {unhealthy} unhealthy")
    return unhealthy


def inspect_services() -> None:
    """List Services and their ready EndpointSlice addresses for connectivity checks."""
    print_header(f"Services in namespace '{NAMESPACE}'")
    try:
        services = core.list_namespaced_service(namespace=NAMESPACE)
    except ApiException as exc:
        print(f"\nCould not list services: {exc.status} {exc.reason}")
        return

    if not services.items:
        print("\n(no services found)")
        return

    for svc in services.items:
        svc_name = svc.metadata.name
        svc_type = svc.spec.type  # ClusterIP / NodePort / LoadBalancer

        # For a LoadBalancer, the public IP shows up here once Azure has provisioned it.
        external_ip = "(pending/none)"
        lb = svc.status.load_balancer
        if lb and lb.ingress:  # `and` short-circuits: only read .ingress if lb is truthy
            # ingress[0].ip is the assigned external IP (may be a hostname on some clouds).
            external_ip = lb.ingress[0].ip or lb.ingress[0].hostname or external_ip

        print()  # blank line before each service => its own visual block
        print(f"  {svc_name}   type={svc_type}   external-ip={external_ip}")

        # EndpointSlices contain the pod addresses behind a Service. An empty result is the
        # classic "Service returns nothing" symptom: no ready pod matches the Service selector.
        # The standard label below links each EndpointSlice to its owning Service.
        try:
            endpoint_slices = discovery.list_namespaced_endpoint_slice(
                namespace=NAMESPACE,
                label_selector=f"kubernetes.io/service-name={svc_name}",
            )
        except ApiException as exc:
            print(f"      (could not read EndpointSlices: {exc.status} {exc.reason})")
            continue  # skip to the next service

        # Collect every ready address across all slices into one flat list. `ready=None` means
        # "unknown" and, by Kubernetes convention, is treated as ready for Service routing.
        addresses = []
        for endpoint_slice in endpoint_slices.items:
            for endpoint in endpoint_slice.endpoints:
                if endpoint.conditions.ready is not False:
                    addresses.extend(endpoint.addresses)

        # A set removes duplicates, and sorted() makes repeated runs deterministic to compare.
        addresses = sorted(set(addresses))

        if addresses:
            print(f"      endpoints ({len(addresses)}): {', '.join(addresses)}")
        else:
            print("      endpoints: NONE  <- no ready pods behind this Service (check labels / readiness)")


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (not when imported by another file). Standard Python entry-point idiom.
if __name__ == "__main__":
    inspect_pods()      # returns the unhealthy count too, but we don't need it here
    inspect_services()

    # A framed footer so the end of the run is unmistakable (not lost in the scrollback).
    print()
    print("═" * WIDTH)
    print("  Done. For retained/searchable logs, query Container Insights with KQL")
    print("  (see ../../04-secure-monitor/kql/).")
    print("═" * WIDTH)
