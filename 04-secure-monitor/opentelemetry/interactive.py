"""Interactive OpenTelemetry playground for Application Insights.

Run this and pick from a menu to:
  - SEND any telemetry type with your own text (a log, request, dependency, exception, metric).
  - QUERY BACK the last 5 minutes of each type from Application Insights.

This is a learning tool: it lets you *emit* a signal, wait a minute or two, then *read* it back
so you can see exactly which table it landed in and what it looks like.

------------------------------------------------------------------------------------------------
SETUP (run these in your terminal, from this folder, with the venv activated):

  python -m pip install azure-monitor-opentelemetry azure-monitor-query azure-identity

  # (1) SENDING needs the connection string of your Application Insights resource:
  export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString>"

  # (2) QUERYING needs two more things:
  #   a) You must be signed in so the app can authenticate. The easiest way is the Azure CLI:
  #        az login
  #      (DefaultAzureCredential below automatically picks up your `az login` session.)
  #   b) The RESOURCE ID of the Application Insights resource, so we know what to query:
  #        az monitor app-insights component show \
  #          --app ai200-appinsights --resource-group ai200-rg --query id -o tsv
  #      Then:
  #        export APPLICATIONINSIGHTS_RESOURCE_ID="<paste the id, /subscriptions/...>"
  #
  # You can SEND without step (2). You only need it to use the QUERY menu options.
------------------------------------------------------------------------------------------------
"""

import os          # read environment variables
import time        # small sleeps (realistic span durations) + flush-before-exit
import logging     # standard Python logging -> lands in the 'traces' table
from datetime import timedelta   # a duration, used for the "last 5 minutes" query window

# --- The Azure Monitor OpenTelemetry Distro: one call wires OTel -> Application Insights. ---
from azure.monitor.opentelemetry import configure_azure_monitor

# --- The OpenTelemetry APIs we use to create spans and metrics by hand. ---
from opentelemetry import metrics, trace
from opentelemetry.trace import SpanKind, Status, StatusCode
# SpanKind is what decides which table a span lands in:
#   SpanKind.SERVER   -> the 'requests' table      (work done in response to an incoming call)
#   SpanKind.CLIENT   -> the 'dependencies' table  (an outbound call your app makes)
# Status/StatusCode let us mark a span as failed.


# ================================================================================================
# One-time configuration
# ================================================================================================

# Read the connection string. os.environ[...] raises a clear error if it's missing, which is a
# good early signal that setup step (1) wasn't done.
CONNECTION_STRING = os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]

# Wire traces + metrics + logs to Application Insights in one call.
configure_azure_monitor(connection_string=CONNECTION_STRING)

# A named logger (the conventional Python pattern). __name__ is this module's name.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)   # emit INFO and above

# A tracer makes spans; a meter makes metrics. Naming them after the module is the OTel convention.
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# A counter is a metric that only goes up. We create it once and .add(...) to it later.
# It surfaces in the 'customMetrics' table.
demo_counter = meter.create_counter("playground.events", description="Events from the playground")

# The resource id is only needed for the QUERY options; may be absent. .get() returns None if unset
# (unlike [...], which would raise) — so SENDING still works without it.
RESOURCE_ID = os.environ.get("APPLICATIONINSIGHTS_RESOURCE_ID")


# ================================================================================================
# SENDING — one function per telemetry type
# ================================================================================================

def send_log() -> None:
    """Emit a log line (lands in the 'traces' table) at a severity you choose."""
    # A dict maps your menu choice to (a logging function, a friendly label).
    levels = {
        "1": (logger.info, "INFO"),
        "2": (logger.warning, "WARNING"),
        "3": (logger.error, "ERROR"),
    }
    choice = input("  Severity — 1) INFO  2) WARNING  3) ERROR  [1]: ").strip() or "1"
    log_func, label = levels.get(choice, (logger.info, "INFO"))

    # input() reads a line of text from the user and returns it as a string.
    message = input("  Message to log: ").strip() or "Hello from the playground"

    log_func(message)   # actually emit the log at the chosen level
    print(f"  ✓ Sent {label} log: {message!r}  (table: traces)")


def send_request() -> None:
    """Emit a SERVER span (lands in the 'requests' table) — as if a call came into your app."""
    name = input("  Request name (e.g. 'GET /orders') [GET /demo]: ").strip() or "GET /demo"

    # start_as_current_span(...) opens a span; the `with` block auto-closes it (recording its
    # duration). kind=SERVER tells the Azure exporter to file it under 'requests'.
    with tracer.start_as_current_span(name, kind=SpanKind.SERVER) as span:
        # Attributes are searchable key/value tags on the span.
        span.set_attribute("demo.source", "playground")
        time.sleep(0.05)   # tiny pause so the request has a non-zero duration
    print(f"  ✓ Sent request {name!r}  (table: requests)")


def send_dependency() -> None:
    """Emit a CLIENT span (lands in 'dependencies') — as if your app called out to a DB/API."""
    name = input("  Dependency name (e.g. 'SELECT orders') [GET example.com]: ").strip() or "GET example.com"
    target = input("  Target it called (e.g. 'db.example.com') [example.com]: ").strip() or "example.com"

    # kind=CLIENT tells the exporter to file this under 'dependencies' (an outbound call).
    with tracer.start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute("peer.service", target)   # who we called
        time.sleep(0.05)
    print(f"  ✓ Sent dependency {name!r} → {target!r}  (table: dependencies)")


def send_exception() -> None:
    """Emit an exception (lands in the 'exceptions' table), correlated to a span."""
    message = input("  Exception message [Something went wrong]: ").strip() or "Something went wrong"

    with tracer.start_as_current_span("playground-error", kind=SpanKind.SERVER) as span:
        try:
            # raise throws an exception. RuntimeError is a built-in exception type. We raise and
            # immediately catch it so we have a real exception object (with a stack trace) to record.
            raise RuntimeError(message)
        except RuntimeError as err:
            # record_exception attaches the error (with stack trace) to this span -> 'exceptions' table.
            span.record_exception(err)
            # Mark the span itself as failed, so it also shows success == false in 'requests'.
            span.set_status(Status(StatusCode.ERROR, message))
    print(f"  ✓ Sent exception: {message!r}  (table: exceptions)")


def send_metric() -> None:
    """Increment a counter (lands in the 'customMetrics' table)."""
    raw = input("  How much to add to the counter? [1]: ").strip() or "1"
    # int(raw) converts the text to a whole number; if it isn't a number, fall back to 1.
    try:
        amount = int(raw)
    except ValueError:
        amount = 1
    if amount <= 0:
        # An OTel Counter is monotonic: it accepts positive increments only. An UpDownCounter is
        # the separate instrument to use when a measurement must also decrease.
        print("  ⚠ A counter increment must be positive; using 1 instead.")
        amount = 1
    # The dict is optional dimensions (labels) you can group by later in KQL.
    demo_counter.add(amount, {"source": "playground"})
    print(f"  ✓ Added {amount} to counter 'playground.events'  (table: customMetrics)")


# ================================================================================================
# QUERYING — read the last 5 minutes of a table back out of Application Insights
# ================================================================================================

# We build the query client lazily (only when first needed) and cache it — along with the
# resolved resource id — in this module-level dict, so we don't pay the auth cost unless the user
# actually queries. A dict is a simple, mutable cache. We seed the id from the env var (may be None).
_query_state = {"client": None, "resource_id": RESOURCE_ID}


def _resolve_resource_id():
    """Return the Application Insights resource id, asking the user to paste it once if the
    APPLICATIONINSIGHTS_RESOURCE_ID env var wasn't set — so you don't have to restart the app."""
    if _query_state["resource_id"]:
        return _query_state["resource_id"]

    # Not set via the env var — let the user paste it now instead of forcing a restart.
    print("  Querying needs the Application Insights RESOURCE ID (and that you've run `az login`).")
    print("  Get it with:  az monitor app-insights component show \\")
    print("                  --app ai200-appinsights --resource-group ai200-rg --query id -o tsv")
    pasted = input("  Paste the resource id (or press Enter to skip): ").strip()
    if not pasted:
        return None
    _query_state["resource_id"] = pasted   # remember it for the rest of this session
    return pasted


def _get_logs_client():
    """Return a LogsQueryClient, or None if querying isn't set up. Imports are done here so the
    SEND-only path never requires the query packages to be installed."""
    # First make sure we know WHICH resource to query (env var or pasted at the prompt).
    if not _resolve_resource_id():
        return None

    if _query_state["client"] is not None:
        return _query_state["client"]

    try:
        # These come from the separate query/auth packages (installed in SETUP above).
        from azure.monitor.query import LogsQueryClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        print("  ⚠ Missing packages. Run:  pip install azure-monitor-query azure-identity")
        return None

    # DefaultAzureCredential tries several sign-in methods in order; after `az login` it uses your
    # Azure CLI session automatically — no secrets in code.
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)
    _query_state["client"] = client   # cache it for next time
    return client


# LogsQueryClient uses the Log Analytics schema even though query_resource scopes the request to
# one Application Insights resource. That means AppRequests/TimeGenerated here, rather than the
# backward-compatible requests/timestamp names shown in Application Insights -> Logs. Each query
# returns the newest 20 rows; the five-minute window comes from the `timespan` argument below.
_QUERIES = {
    "traces": "AppTraces | project TimeGenerated, Message, SeverityLevel | order by TimeGenerated desc | take 20",
    "requests": "AppRequests | project TimeGenerated, Name, ResultCode, DurationMs, Success | order by TimeGenerated desc | take 20",
    "dependencies": "AppDependencies | project TimeGenerated, Name, Target, Success, DurationMs | order by TimeGenerated desc | take 20",
    "exceptions": "AppExceptions | project TimeGenerated, ExceptionType, OuterMessage, OperationId | order by TimeGenerated desc | take 20",
    "customMetrics": "AppMetrics | project TimeGenerated, Name, Sum | order by TimeGenerated desc | take 20",
}


def query_recent(kind: str) -> None:
    """Print the last 5 minutes of one table."""
    client = _get_logs_client()
    if client is None:
        return   # not configured; helpful message already printed

    from azure.monitor.query import LogsQueryStatus   # local import keeps SEND-only path clean

    query = _QUERIES[kind]
    print(f"\n  Querying last 5 minutes of '{kind}' ...")
    # query_resource runs KQL against the App Insights resource. timespan bounds it to 5 minutes.
    # Wrap it: if you're not signed in (or lack access), show a friendly hint instead of crashing.
    try:
        response = client.query_resource(
            _query_state["resource_id"], query, timespan=timedelta(minutes=5)
        )
    except Exception as err:   # noqa: BLE001 — any auth/network error should be handled, not fatal
        print(f"  ⚠ Query failed: {err}")
        print("    Check that you ran `az login` and have at least 'Reader' on the resource.")
        return

    if response.status != LogsQueryStatus.SUCCESS:
        print("  ⚠ Query did not fully succeed (partial or failed). Try again in a moment.")
        return

    # A result has one or more tables; each has .columns (names) and .rows (lists of values).
    for table in response.tables:
        if not table.rows:
            print("  (no rows — remember telemetry takes 1–3 minutes to appear)")
            continue
        # Print the column headers, then each row, tab-separated. "\t".join(...) glues a list of
        # strings with tabs. We str(...) every value because rows can hold numbers, datetimes, etc.
        print("  " + "\t".join(table.columns))
        for row in table.rows:
            print("  " + "\t".join(str(value) for value in row))
    print()


# ================================================================================================
# The menu loop
# ================================================================================================

def flush() -> None:
    """Force any buffered telemetry to be sent now. Telemetry is batched in the background, so we
    flush on exit (and after sends) to avoid losing the tail. Guarded because not every provider
    exposes force_flush."""
    for provider in (trace.get_tracer_provider(), metrics.get_meter_provider()):
        try:
            provider.force_flush()   # blocks briefly until the buffer is sent
        except Exception:
            pass   # some provider types don't have force_flush; ignore


def clear_screen() -> None:
    """Wipe the terminal so the next menu redraws cleanly at the top. This is an ANSI escape
    sequence: \\033[H moves the cursor home (top-left), \\033[J clears from there down. Works on
    Linux/macOS terminals and modern Windows Terminal."""
    print("\033[H\033[J", end="")


def pause() -> None:
    """Wait for a keypress so query output stays on screen until you're ready to move on —
    otherwise the long menu would immediately scroll the results out of view."""
    input("\n  Press Enter to continue...")


MENU = """
================= OpenTelemetry Playground =================
SEND telemetry:
  1) Send a log (traces)
  2) Send a request (requests)
  3) Send a dependency / outbound call (dependencies)
  4) Send an exception (exceptions)
  5) Send a metric (customMetrics)

QUERY last 5 minutes:
  6) Show recent logs (traces)
  7) Show recent requests
  8) Show recent dependencies
  9) Show recent exceptions
 10) Show recent metrics (customMetrics)

  0) Quit
===========================================================
"""

# This dict maps each menu number to the function that handles it. Using a dict instead of a long
# if/elif chain keeps the loop tidy — a common Python pattern ("dispatch table").
ACTIONS = {
    "1": send_log,
    "2": send_request,
    "3": send_dependency,
    "4": send_exception,
    "5": send_metric,
    "6": lambda: query_recent("traces"),         # lambda = a tiny inline function with no name
    "7": lambda: query_recent("requests"),
    "8": lambda: query_recent("dependencies"),
    "9": lambda: query_recent("exceptions"),
    "10": lambda: query_recent("customMetrics"),
}


# Standard Python entry point: only runs when you execute this file directly.
if __name__ == "__main__":
    print("Connected to Application Insights. (Telemetry takes 1–3 minutes to become queryable.)")
    input("Press Enter to open the menu...")
    try:
        # `while True:` loops forever until we `break` out of it (when the user picks 0).
        while True:
            clear_screen()    # start each round with a clean screen so the menu is at the top
            print(MENU)
            choice = input("Pick an option: ").strip()

            if choice == "0":
                break

            action = ACTIONS.get(choice)   # look up the handler; None if the choice is invalid
            if action is None:
                print("  ✗ Not a valid option, try again.")
            else:
                action()      # run the chosen SEND or QUERY function
                flush()       # push what we just sent so it starts making its way to Azure

            # Hold the output on screen until the user is ready; only THEN loop back and redraw
            # the menu (which clear_screen() wipes to). This is the fix for results scrolling away.
            pause()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or end-of-input: exit cleanly instead of dumping a stack trace.
        print("\nInterrupted.")
    finally:
        # `finally` always runs, even on error — a good place to flush before the program ends.
        print("Flushing telemetry before exit...")
        flush()
        time.sleep(2)   # give the background exporter a moment to finish sending
        print("Bye.")
