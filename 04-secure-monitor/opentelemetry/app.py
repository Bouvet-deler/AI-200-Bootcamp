# A tiny app that emits all THREE OpenTelemetry signals to Application Insights:
#   - a manual TRACE (a span you create by hand, for your own business logic)
#   - a METRIC (a numeric counter)
#   - an auto-instrumented DEPENDENCY (an outbound HTTP call, tracked for free)
#   - LOG lines (which land in the 'traces' table)
#
# First install the SDK + an HTTP library (run in your terminal, not in Python):
#   python -m pip install azure-monitor-opentelemetry requests
#
# Then set the connection string from the setup step (bash/fish):
#   export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString>"

import os        # 'import' loads a library. 'os' lets us read environment variables.
import time      # used at the end to let buffered telemetry flush before we exit.
import logging   # Python's built-in logging library — emits log lines to the 'traces' table.

import requests  # a popular HTTP client. The Azure distro AUTO-instruments it: every call it
                 # makes becomes a 'dependency' span with no extra code from us.

# The Azure Monitor OpenTelemetry Distro. `from X import y` pulls just `y` into scope.
# configure_azure_monitor() wires the whole OTel pipeline (traces + metrics + logs) to
# Application Insights in ONE call — this is the Microsoft-recommended onboarding path.
from azure.monitor.opentelemetry import configure_azure_monitor

# `metrics` and `trace` are the OpenTelemetry APIs. We call them AFTER configure_... has set up
# the SDK behind them, so anything we record is actually exported to Azure.
from opentelemetry import metrics, trace

# Read the connection string from the environment. os.environ is a dict-like object of
# environment variables; ["..."] looks one up (and errors loudly if it's missing).
connection_string = os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]

# One call configures traces, metrics, AND logs, and points them at Application Insights.
# From here on: Python `logging` records, auto-instrumented library calls, and any spans/metrics
# we create are all exported. (The SDK can auto-detect the env var too, but we pass it
# explicitly so the intent is obvious.)
configure_azure_monitor(connection_string=connection_string)

# A named logger is the conventional Python pattern. __name__ is a built-in variable holding
# this module's name ("__main__" when the file is run directly).
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # emit INFO and above (INFO, WARNING, ERROR, ...)

# Get a TRACER (makes spans) and a METER (makes metrics). Naming them after the module is the
# OpenTelemetry convention — it tags the telemetry with where it came from.
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# A COUNTER is a metric that only goes up (e.g. "orders processed"). We create it once here and
# .add(...) to it later. It surfaces in the 'customMetrics' table in Application Insights.
orders_counter = meter.create_counter(
    "orders.processed",                         # the metric name you'll query on
    description="Number of orders processed",   # human-readable description
)


def process_order(order_id: int) -> None:
    # `-> None` is a type hint meaning "returns nothing". Hints are optional docs; Python does
    # not enforce them at runtime.

    # Create a MANUAL span for our business logic. `with ... as span:` is Python's context
    # manager: the span STARTS here and automatically ENDS (recording its duration) when the
    # 'with' block exits — even if an error is thrown. This span becomes the root operation and
    # shows up in the 'requests' table; everything inside shares its operation_Id (trace ID).
    with tracer.start_as_current_span("process_order") as span:
        # ATTRIBUTES are key/value tags on the span — searchable context about this operation.
        span.set_attribute("order.id", order_id)

        logger.info("Processing order %s", order_id)  # INFO log -> 'traces' table

        # An auto-instrumented outbound call. Because 'requests' is instrumented by the distro,
        # this HTTP GET automatically becomes a child 'dependency' span sharing our operation_Id
        # — that shared id is exactly the correlation you 'join' on in KQL.
        response = requests.get("https://example.com", timeout=10)
        logger.info("Fetched status %s", response.status_code)

        # try/except is Python's error handling: run risky code, catch failures.
        try:
            if order_id < 0:
                # `raise` throws an exception. ValueError is a built-in exception type.
                raise ValueError("order_id cannot be negative")
        except ValueError as err:
            # Attach the exception to the CURRENT span. record_exception() surfaces it in the
            # 'exceptions' table, correlated to this trace.
            span.record_exception(err)
            # logger.exception logs at ERROR level and attaches the stack trace.
            logger.exception("Failed to process order %s", order_id)
            return  # stop early on a bad order; don't count it as processed

        # Increment the metric by 1. The dict is optional DIMENSIONS (extra labels) you can
        # group by later in KQL, e.g. count processed orders per status.
        orders_counter.add(1, {"status": "ok"})


# `if __name__ == "__main__":` means "only run this when the file is executed directly" (not
# when imported by another file). Standard Python entry-point idiom.
if __name__ == "__main__":
    process_order(1)     # normal order: span + dependency + metric + logs
    process_order(50)    # another normal order
    process_order(-5)    # bad order: records an exception, no metric increment

    # Telemetry is buffered and flushed in the background (BatchSpanProcessor). Give it a moment
    # before the program exits so the buffer is actually sent — otherwise you lose the tail.
    print("Flushing telemetry...")
    time.sleep(5)        # pause 5 seconds
    print("Done. Check Application Insights > Logs in a minute or two.")
