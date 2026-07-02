# First install the SDK (run in your terminal, not in Python):
#   python -m pip install azure-monitor-opentelemetry
#
# Then set the connection string from the CLI step above, e.g. (bash/fish):
#   export APPLICATIONINSIGHTS_CONNECTION_STRING="<paste the connectionString>"

import os        # 'import' loads a module (a library). 'os' lets us read environment variables.
import logging   # Python's built-in logging library — the standard way to emit log lines.

# Import ONE function from the Azure SDK. `from X import y` pulls just `y` into scope.
from azure.monitor.opentelemetry import configure_azure_monitor

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


def process_order(order_id: int) -> None:
    # `-> None` is a type hint meaning "returns nothing". Hints are optional docs; Python
    # doesn't enforce them at runtime.
    logger.info("Processing order %s", order_id)  # an INFO log -> shows up in the 'traces' table

    # try/except is Python's error handling: run the risky code, catch failures.
    try:
        if order_id < 0:
            # `raise` throws an exception. ValueError is a built-in exception type.
            raise ValueError("order_id cannot be negative")
        elif order_id > 100:
            # Log a warning for unusually large order IDs
            logger.warning("Large order ID detected: %s", order_id)
    except ValueError:
        # logger.exception logs at ERROR level AND attaches the stack trace.
        # This surfaces in the 'exceptions' table in Application Insights.
        logger.exception("Failed to process order %s", order_id)

def validate_inventory(item: str, quantity: int) -> bool:
    # A helper function that logs a custom event
    # Custom events appear in the 'customEvents' table in Application Insights
    if quantity < 0:
        logger.warning("Invalid quantity %s for item %s", quantity, item)
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
    import time          # imports can appear anywhere; here it's local to this block
    time.sleep(5)        # pause 5 seconds
    print("Done. Check Application Insights > Logs in a minute or two.")
