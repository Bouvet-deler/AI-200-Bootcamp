# First install the SDK (run in your terminal, not in Python):
#   python -m pip install azure-monitor-opentelemetry
#
# Then set the connection string from the CLI step above, e.g. (bash/fish):
#   export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString>"

import os        # 'import' loads a module (a library). 'os' lets us read environment variables.
import logging   # Python's built-in logging library — the standard way to emit log lines.
import time      # Used at shutdown to give the background telemetry exporter time to flush.

# `from X import y` pulls selected names into scope. The Azure helper configures export, while
# the OpenTelemetry names below create spans and describe whether a span succeeded or failed.
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Read the connection string from the environment.
# os.environ is a dict-like object of environment variables; [".."] looks one up.
# We pass it explicitly so the intent is obvious (the SDK can also auto-detect it).
connection_string = os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]

# One call wires the OpenTelemetry pipeline to Azure Monitor:
# from now on, Python `logging` records and traces are exported to Application Insights.
configure_azure_monitor(connection_string=connection_string)

# Get a named logger. __name__ is a built-in variable = this module's name ("__main__" when
# run directly). Using a named logger is the conventional Python pattern.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # emit INFO and above (INFO, WARNING, ERROR, ...)

# A tracer creates spans. Recording a caught exception on a span produces exception telemetry;
# logger.exception(...) alone is still a log record and belongs in the 'traces' table.
tracer = trace.get_tracer(__name__)


def process_order(order_id: int) -> None:
    # `-> None` is a type hint meaning "returns nothing". Hints are optional docs; Python
    # doesn't enforce them at runtime.
    # A context manager starts the span here and always ends it when the indented block exits.
    # This manual span gives a caught exception somewhere to be recorded and correlated.
    with tracer.start_as_current_span("process_order") as span:
        logger.info("Processing order %s", order_id)  # INFO log -> the 'traces' table.

        # try/except is Python's error handling: run the risky code, catch failures.
        try:
            if order_id < 0:
                # `raise` throws an exception. ValueError is a built-in exception type.
                raise ValueError("order_id cannot be negative")
            if order_id > 100:
                # A warning is still a log; severityLevel distinguishes it in KQL.
                logger.warning("Large order ID detected: %s", order_id)
        except ValueError as error:
            # Caught exceptions are not automatically attached to a span, so record the details
            # explicitly and separately mark the span's outcome as an error.
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR))
            # logger.exception writes the ERROR-level log and stack trace to 'traces'. The
            # record_exception call above is what also creates correlated exception telemetry.
            logger.exception("Failed to process order %s", order_id)


def validate_inventory(item: str, quantity: int) -> bool:
    # A helper that logs a warning for invalid input.
    # A plain logger.warning(...) is a 'traces' record (severityLevel = 2). Azure Monitor's
    # Python OpenTelemetry integration has one deliberate exception: the reserved
    # `microsoft.custom_event.name` value in logging's `extra` dict routes this record to
    # 'customEvents'. `extra` adds structured properties without changing the text message.
    if quantity < 0:
        logger.warning(
            "Invalid quantity %s for item %s",
            quantity,
            item,
            extra={
                "microsoft.custom_event.name": "InventoryValidationFailed",
                "item": item,
                "quantity": quantity,
            },
        )
        return False
    return True


# `if __name__ == "__main__":` means "only run this when the file is executed directly"
# (not when imported by another file). Standard Python entry-point idiom.
if __name__ == "__main__":
    # Process a few orders to generate varied telemetry
    process_order(1)      # INFO: normal order
    process_order(50)     # INFO: another normal order
    process_order(150)    # WARNING: large order ID
    process_order(-5)    # ERROR: triggers exception
    
    # Validate some inventory items
    validate_inventory("Widget", 10)    # valid, no log
    validate_inventory("Gadget", -3)    # WARNING: invalid quantity

    # Telemetry is buffered and flushed in the background. Give it a moment before the
    # program exits so the data is actually sent.
    time.sleep(5)        # Pause five seconds before the Python process exits.
    print("Done. Check Application Insights > Logs in a minute or two.")
