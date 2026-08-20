# Azure Functions — Python v2 programming model
# This file is: function_app.py  (the name matters — the host looks for exactly this file)
#
# The v2 model puts EVERY function of the app in ONE file, registered on ONE `app`
# object using decorators. There are no per-function folders and no function.json files.
#
# The three functions below form a small chain, so you can see triggers and bindings
# working together:
#
#   HTTP request ──▶ HttpHello ──(output binding)──▶ "demo-queue" ──▶ QueueProcessor
#                                                    TimerCleanup runs on its own schedule
#
# Run locally:  func start
# Deploy:       func azure functionapp publish <your-function-app-name>

# `import x as y` gives the module a shorter local alias — Python's equivalent of a
# C# `using Alias = Namespace;`. Everything from the Functions SDK hangs off `func`.
import azure.functions as func

# `logging` is Python's built-in logging module (roughly ILogger in .NET). The Functions
# host captures anything you log here and forwards it to the console (locally) and to
# Application Insights (when deployed).
import logging

# `os` gives access to environment variables — how application settings reach your code.
import os

# `from x import y` pulls a single name out of a module instead of the whole module.
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# The FunctionApp object
# ---------------------------------------------------------------------------
# Exactly ONE FunctionApp instance per app, created at module level. The host imports
# this file, finds this object, and reads the decorators below to discover your functions.
#
# http_auth_level sets the DEFAULT authorization level for every HTTP function in the app:
#   ANONYMOUS — no key required (fine for learning; wide open in production)
#   FUNCTION  — caller must pass a function key (?code=... or the x-functions-key header)
#   ADMIN     — caller must pass the master key
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ---------------------------------------------------------------------------
# 1. HTTP trigger + Queue OUTPUT binding
# ---------------------------------------------------------------------------
# A "decorator" is Python's `@something` syntax written directly above a function. It is
# a function that wraps your function — the closest .NET analogy is an attribute, except
# it actually executes. Here each decorator registers metadata with `app`.
#
# Decorators are applied bottom-up, but for Functions the order between them does not
# matter; what matters is that they sit directly above the `def`.

# @app.function_name — the name the function is registered under in Azure (what you see
# in the portal and in logs). Without it, the Python function name is used.
@app.function_name(name="HttpHello")
# @app.route — makes this an HTTP-triggered function.
#   route="hello"     → the URL is /api/hello  (the ROUTE is the whole path after /api;
#                       the function name does NOT appear in the URL)
#   methods=[...]     → which HTTP verbs are accepted
#   auth_level        → overrides the app-wide default set on FunctionApp above
@app.route(route="hello", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
# @app.queue_output — an OUTPUT BINDING. Anything you write to the `outputQueue`
# parameter is sent to the queue by the host after the function returns. You never
# create a QueueClient or handle a connection string yourself.
#   arg_name="outputQueue" → must match the parameter name in the `def` line below
#   queue_name="demo-queue" → the queue the message lands in (auto-created if missing)
#   connection="StorageConnection" → the NAME of an app setting holding the connection
#                       string — not the connection string itself. Set it in
#                       local.settings.json locally, and in the Function App's
#                       Environment variables when deployed.
@app.queue_output(arg_name="outputQueue", queue_name="demo-queue", connection="StorageConnection")
def http_hello(req: func.HttpRequest, outputQueue: func.Out[str]) -> func.HttpResponse:
    """
    HTTP-triggered function that greets the caller and drops a message on a queue.

    The triple-quoted block above is a docstring — Python's built-in documentation
    comment, equivalent to an XML doc comment in C#.

    Args:
        req: the incoming request. This is the TRIGGER BINDING — the host parses the
             raw HTTP request and hands you an object. Useful members:
               req.params           — dict of query-string values (?name=Azure)
               req.headers          — dict of headers
               req.method           — "GET", "POST", ...
               req.get_body()       — raw body as bytes
               req.get_json()       — body parsed as JSON into a dict (raises on bad JSON)
        outputQueue: the OUTPUT BINDING declared by @app.queue_output. `func.Out[str]`
             is a write-only holder — call `.set(value)` on it to emit a message.

    Returns:
        func.HttpResponse — returned straight to the caller.
    """
    logging.info("HttpHello: processing an HTTP request.")

    # `req.params.get("name")` returns None instead of raising when the key is absent —
    # this is dict.get(), Python's equivalent of TryGetValue with a null default.
    name = req.params.get("name")

    # In Python, `if not x:` is true for None AND for an empty string — one check covers
    # "missing" and "blank".
    if not name:
        # try/except is Python's try/catch. get_json() raises ValueError when the body
        # is not valid JSON, which is the normal case for a plain GET with no body.
        try:
            req_body = req.get_json()
            name = req_body.get("name")
        except ValueError:
            name = None

    # `or` returns the first truthy operand, so this is a concise default. Reads as
    # "name, or 'Azure Functions' if name is empty".
    name = name or "Azure Functions"

    # An f-string ("formatted string literal") interpolates expressions inside {} —
    # the same idea as C#'s $"Hello, {name}".
    message = f"Hello, {name}! This HTTP-triggered function executed successfully."

    # Write to the output binding. The host sends this to "demo-queue" AFTER the
    # function returns successfully — if the function throws, nothing is enqueued.
    outputQueue.set(message)
    logging.info("HttpHello: queued a message for demo-queue.")

    # Application settings arrive as environment variables. os.environ.get() returns
    # None (or the second argument) when the setting is not present, so it never throws.
    environment = os.environ.get("APP_ENVIRONMENT", "local")
    logging.info(f"HttpHello: running in environment '{environment}'.")

    return func.HttpResponse(message, status_code=200, mimetype="text/plain")


# ---------------------------------------------------------------------------
# 2. Queue trigger
# ---------------------------------------------------------------------------
# This function wakes up on its own whenever a message appears in "demo-queue" —
# including the messages HttpHello above puts there.
@app.function_name(name="QueueProcessor")
# @app.queue_trigger — the TRIGGER BINDING. The host polls the queue for you, and calls
# this function once per message. No polling loop, no client, no connection code.
#   arg_name="msg"  → must match the parameter name below
#   connection      → again the NAME of an app setting, not the value
@app.queue_trigger(arg_name="msg", queue_name="demo-queue", connection="StorageConnection")
def queue_processor(msg: func.QueueMessage) -> None:
    """
    Queue-triggered function.

    `-> None` is a type hint meaning "returns nothing" (like `void`). Python does not
    enforce hints at runtime — they document intent and help editors.

    Args:
        msg: the dequeued message. Useful members:
               msg.get_body()    — the message content as bytes
               msg.id            — the message id assigned by Azure Storage
               msg.dequeue_count — how many times this message has been delivered
               msg.pop_receipt   — token used for manual delete/update
               msg.insertion_time / msg.expiration_time
    """
    logging.info("QueueProcessor: processing a queue message.")

    # Queue messages are bytes on the wire. .decode("utf-8") turns bytes into a str —
    # Python keeps the two types strictly separate, unlike C# where string is the default.
    message_body = msg.get_body().decode("utf-8")

    logging.info(f"QueueProcessor: id={msg.id} dequeue_count={msg.dequeue_count}")
    logging.info(f"QueueProcessor: body={message_body}")

    # dequeue_count > 1 means a previous attempt failed and the host redelivered the
    # message. After maxDequeueCount attempts (5 by default, set in host.json) the
    # message is moved to the poison queue "demo-queue-poison".
    if msg.dequeue_count > 1:
        logging.warning(f"QueueProcessor: retry number {msg.dequeue_count} for this message.")

    # Your real work goes here — call an API, write to Cosmos DB, transform data, ...
    logging.info(f"QueueProcessor: done -> Processed: {message_body}")

    # Returning normally tells the host the message was handled, and it is deleted from
    # the queue. Raising an exception leaves the message to be retried.


# ---------------------------------------------------------------------------
# 3. Timer trigger
# ---------------------------------------------------------------------------
@app.function_name(name="TimerCleanup")
# @app.timer_trigger — fires on a schedule, with no external caller involved.
#   schedule uses a SIX-field NCRONTAB expression:
#       {second} {minute} {hour} {day} {month} {day-of-week}
#   "0 */5 * * * *" = at second 0, every 5th minute, every hour, every day  → every 5 min.
#   Note the leading seconds field: standard Linux cron has five fields, Azure has six.
#   More examples:  "0 0 * * * *"   every hour on the hour
#                   "0 30 9 * * *"  every day at 09:30
#                   "0 0 9 * * 1"   every Monday at 09:00
#   Schedules run in UTC unless the WEBSITE_TIME_ZONE app setting says otherwise.
#   run_on_startup=True would also fire the function every time the host starts — handy
#   while developing, but avoid it in production (it fires on every scale-out too).
@app.timer_trigger(arg_name="timer", schedule="0 */5 * * * *", run_on_startup=False)
def timer_cleanup(timer: func.TimerRequest) -> None:
    """
    Timer-triggered function — the serverless equivalent of a cron job.

    Args:
        timer: schedule information. The ONLY member available in Python is:
               timer.past_due — True when the host is running this invocation late
                                (for example after the app was scaled to zero).
    """
    logging.info("TimerCleanup: timer trigger fired.")

    # datetime.now(timezone.utc) is the correct way to get the current UTC time.
    # (The older datetime.utcnow() is deprecated from Python 3.12 because it returns a
    # "naive" datetime with no timezone attached.)
    now = datetime.now(timezone.utc)

    # .isoformat() renders an ISO 8601 string, e.g. "2026-08-20T09:15:00+00:00".
    logging.info(f"TimerCleanup: executed at {now.isoformat()}")

    if timer.past_due:
        logging.warning("TimerCleanup: this invocation is past due (running late).")

    # Real cleanup work would go here — for example deleting blobs older than 30 days,
    # purging expired Cosmos DB documents, or emitting a daily report.
    logging.info("TimerCleanup: cleanup task completed.")
