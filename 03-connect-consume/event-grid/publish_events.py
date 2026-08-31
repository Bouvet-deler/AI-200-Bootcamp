# Azure Event Grid — publishing custom events with the Python SDK
# This file is: publish_events.py
#
# Goal: send a handful of CloudEvents to the custom topic created in the README's Setup
# section, so you can watch Event Grid route them to whatever handler you registered.
#
# Two events share the subject "orders/12345" (an order being created, then shipped).
# One event has the subject "inventory/sku-998" instead. If your event subscription was
# created with --subject-begins-with "orders/" (as the README's Setup does), the inventory
# event never reaches your handler — the SUBJECT FILTER drops it before delivery. That's the
# easiest way to *see* filtering work: two events show up where you're watching, one doesn't.
#
# Run:  python publish_events.py

# `import os` gives access to environment variables — how the topic endpoint and key reach
# this script, instead of hardcoding secrets in source.
import os

# AzureKeyCredential wraps a plain access key (like a connection string) so SDK clients can
# authenticate with it. The alternative — azure.identity.DefaultAzureCredential — uses Microsoft
# Entra ID / managed identity instead of a key; production code should generally prefer that,
# but a raw key keeps this sample's setup to two environment variables.
from azure.core.credentials import AzureKeyCredential

# CloudEvent is Azure's Python type for the CloudEvents v1.0 schema (see README Core concepts
# §2). EventGridPublisherClient accepts this type when publishing to a CloudEvents topic, so you
# don't hand-build the JSON envelope.
from azure.core.messaging import CloudEvent

# EventGridPublisherClient is the SDK's client for sending events TO a topic. This Event Grid
# Basic sample uses push delivery, so receiving happens in the destination handler (an Azure
# Function or webhook), not in this script.
from azure.eventgrid import EventGridPublisherClient


def main():
    # os.environ[...] (square brackets, not .get()) raises immediately with a clear
    # KeyError if the variable is missing — better than a confusing failure deep inside the
    # SDK call below. Use .get() instead when a default is acceptable; here it isn't.
    topic_endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
    topic_key = os.environ["EVENTGRID_TOPIC_KEY"]

    # Construct the client once. `credential=` accepts anything implementing Azure's
    # credential protocol — here an AzureKeyCredential wrapping the topic's access key.
    client = EventGridPublisherClient(topic_endpoint, AzureKeyCredential(topic_key))

    # A Python list literal — CloudEvent objects, one per event we want to publish.
    # CloudEvent fields, and what they map to conceptually:
    #   source  — WHERE the event came from. Convention: a URI-like path identifying the
    #             publisher, not a specific instance. Reused across events from this app.
    #   type    — WHAT KIND of event this is. Convention: "<Domain>.<PastTenseVerb>",
    #             e.g. "Orders.OrderCreated". This is what an `includedEventTypes` filter
    #             matches against.
    #   subject — WHICH SPECIFIC resource the event is about, e.g. "orders/12345". This is
    #             what a `subjectBeginsWith`/`subjectEndsWith` filter matches against.
    #   data    — your actual payload. Any JSON-serializable Python value (here, a dict).
    # `id` and `time` are NOT set below — the SDK fills in a unique id and the current UTC
    # timestamp automatically when they're omitted.
    events = [
        CloudEvent(
            source="/ai200-bootcamp/orders",
            type="Orders.OrderCreated",
            subject="orders/12345",
            data={"orderId": 12345, "customer": "frank", "total": 129.99},
        ),
        CloudEvent(
            source="/ai200-bootcamp/orders",
            type="Orders.OrderShipped",
            subject="orders/12345",
            data={"orderId": 12345, "carrier": "postnord", "trackingNumber": "PN123456789SE"},
        ),
        # Different subject prefix ("inventory/" instead of "orders/") — this is the event a
        # subscription filtered to `subjectBeginsWith "orders/"` will NOT receive.
        CloudEvent(
            source="/ai200-bootcamp/inventory",
            type="Inventory.StockLow",
            subject="inventory/sku-998",
            data={"sku": "sku-998", "quantityRemaining": 3},
        ),
    ]

    # `client.send(...)` accepts a single CloudEvent or a list — sending the list in one call
    # is one HTTP request instead of three, which is both faster and how you'd batch in
    # production. Event Grid fans each event out independently to every matching subscription.
    client.send(events)

    # f-strings (formatted string literals) interpolate expressions inside {}. len(events)
    # counts how many CloudEvent objects are in the list.
    print(f"Published {len(events)} events to {topic_endpoint}")


# The `if __name__ == "__main__":` guard is Python's way of saying "only run this when the
# file is executed directly (`python publish_events.py`), not when it's imported by another
# module." This lets one Python file work both as a runnable script and as an importable module.
if __name__ == "__main__":
    main()
