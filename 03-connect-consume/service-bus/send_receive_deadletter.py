# Azure Service Bus — queue, dead-letter queue, topic, and subscription walkthrough
# This file is: send_receive_deadletter.py
#
# Goal: use the resources created in README.md to send and settle queue messages, inspect a
# dead-lettered message, and prove that topic subscription filtering makes independent copies.
#
# Run: python send_receive_deadletter.py
#
# Use a dedicated lab namespace. This sample intentionally completes every message it receives
# so that repeated runs begin cleanly; it is not a production queue processor.

# `os` lets Python read environment variables. The connection string stays outside source code
# instead of being copied into this file.
import os

# `uuid4` creates a random identifier. Adding one to each MessageId makes every run distinct,
# which is useful even if you later enable Service Bus duplicate detection.
from uuid import uuid4

# These are the synchronous Azure Service Bus SDK types used by the sample:
# - ServiceBusClient opens a connection to a namespace.
# - ServiceBusMessage represents a message we send.
# - ServiceBusReceiveMode selects Peek-Lock rather than relying on its default implicitly.
# - ServiceBusSubQueue.DEAD_LETTER selects the built-in DLQ receiver.
from azure.servicebus import (
    ServiceBusClient,
    ServiceBusMessage,
    ServiceBusReceiveMode,
    ServiceBusSubQueue,
)


def body_as_text(message):
    # A received message body is an iterable of byte chunks. `b"".join(...)` combines those
    # chunks into one bytes value, and `.decode("utf-8")` turns UTF-8 bytes back into Python text.
    # This sample sent text bodies, so UTF-8 is the matching decoding.
    return b"".join(message.body).decode("utf-8")


def send_demo_messages(client, queue_name, topic_name, run_id):
    # `ServiceBusMessage` carries both a body and useful broker/application metadata.
    # The MessageId values are stable within this run and can be used for tracing or
    # idempotency. `subject` is a simple classification; application_properties hold values
    # that a topic subscription rule can inspect without parsing the body.
    queue_messages = [
        ServiceBusMessage(
            "Create invoice for order 1001",
            message_id=f"queue-good-{run_id}",
            subject="ValidOrder",
            application_properties={"priority": "normal"},
        ),
        ServiceBusMessage(
            "Create invoice for order 1002, but its tax identifier is invalid",
            message_id=f"queue-invalid-{run_id}",
            subject="InvalidOrder",
            application_properties={"priority": "high"},
        ),
    ]

    # A sender is an AMQP link aimed at one queue. The `with` statement closes the link when
    # this indented block ends, even if the send raises an exception.
    with client.get_queue_sender(queue_name=queue_name) as sender:
        # Sending a Python list creates a small batch. Both messages are accepted by the broker
        # before this call returns, then they wait durably for a receiver.
        sender.send_messages(queue_messages)

    # The topic messages carry the same `priority` application property used by the SQL
    # subscription rule created in the README. The all-orders subscription receives both;
    # the high-priority subscription receives only the first.
    topic_messages = [
        ServiceBusMessage(
            "Order 2001 was created with high priority",
            message_id=f"topic-high-{run_id}",
            subject="OrderCreated",
            application_properties={"priority": "high"},
        ),
        ServiceBusMessage(
            "Order 2002 was created with normal priority",
            message_id=f"topic-normal-{run_id}",
            subject="OrderCreated",
            application_properties={"priority": "normal"},
        ),
    ]

    # A topic sender looks like a queue sender. Service Bus creates the durable subscription
    # copies according to each subscription's rules after accepting these messages.
    with client.get_topic_sender(topic_name=topic_name) as sender:
        sender.send_messages(topic_messages)

    # f-strings put the values in `{...}` directly into readable output.
    print(f"Sent 2 queue messages to '{queue_name}' and 2 topic messages to '{topic_name}'.")


def process_queue_messages(client, queue_name):
    # Peek-Lock is explicit here to make the safety behavior visible: a message is locked but
    # is not removed until the receiver calls complete_message, abandon_message, or
    # dead_letter_message.
    with client.get_queue_receiver(
        queue_name=queue_name,
        receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    ) as receiver:
        # `receive_messages` returns a Python list. It waits up to five seconds for a message
        # and returns earlier if messages are available; 10 is the maximum this small demo asks
        # for in one call.
        messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)

        # An empty list is false in an `if` condition. This makes a no-message result clear
        # instead of silently doing nothing.
        if not messages:
            print(f"No queue messages were available in '{queue_name}'.")
            return

        # `for` visits each received message in the list once.
        for message in messages:
            # Convert the AMQP byte body into the text that this sample originally sent.
            body = body_as_text(message)

            # The invalid message is deliberately routed to the DLQ. Real applications make
            # this choice only when retrying cannot help, for example malformed input.
            if message.subject == "InvalidOrder":
                receiver.dead_letter_message(
                    message,
                    reason="InvalidTaxIdentifier",
                    error_description="The demo intentionally rejects this invalid order.",
                )
                print(f"Dead-lettered queue message '{message.message_id}': {body}")
            else:
                # `complete_message` is the positive acknowledgment. It permanently removes
                # the locked message only after the business work has succeeded.
                receiver.complete_message(message)
                print(f"Completed queue message '{message.message_id}': {body}")


def inspect_and_clear_dead_letters(client, queue_name):
    # Passing `sub_queue=ServiceBusSubQueue.DEAD_LETTER` opens the queue's built-in DLQ instead
    # of its normal active-message queue. The DLQ uses the same Peek-Lock settlement model.
    with client.get_queue_receiver(
        queue_name=queue_name,
        sub_queue=ServiceBusSubQueue.DEAD_LETTER,
        receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    ) as receiver:
        # This one lab message should arrive immediately after process_queue_messages moves it.
        messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)

        if not messages:
            print(f"No dead-letter messages were available for '{queue_name}'.")
            return

        for message in messages:
            # The service preserves the reason and detailed description supplied by the
            # dead-letter call, making a DLQ a useful diagnostic work queue.
            body = body_as_text(message)
            print(
                f"DLQ message '{message.message_id}': {body} "
                f"(reason={message.dead_letter_reason!r}, "
                f"description={message.dead_letter_error_description!r})"
            )

            # Completing a DLQ message deletes that DLQ copy. A real repair flow would first
            # create and send a corrected NEW message, then complete this original copy.
            receiver.complete_message(message)
            print(f"Removed DLQ message '{message.message_id}' after inspection.")


def receive_subscription_messages(client, topic_name, subscription_name):
    # Consumers never receive from a topic directly. They create a receiver for one named
    # subscription, whose message copy and settlement state are independent of other subscriptions.
    with client.get_subscription_receiver(
        topic_name=topic_name,
        subscription_name=subscription_name,
        receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    ) as receiver:
        messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)

        if not messages:
            print(f"No messages were available in subscription '{subscription_name}'.")
            return

        for message in messages:
            body = body_as_text(message)
            print(
                f"Subscription '{subscription_name}' received "
                f"'{message.message_id}': {body}"
            )

            # Each subscription copy must be completed separately. Completing the all-orders
            # copy does not remove the high-priority subscription's copy.
            receiver.complete_message(message)


def get_connection_string():
    # `os.environ.get(..., "")` returns an empty string instead of raising KeyError when the
    # variable is missing. `.strip()` removes accidental whitespace from a pasted value.
    connection_string = os.environ.get("SERVICEBUS_CONNECTION_STRING", "").strip()

    # A shared-access Service Bus connection string has these three identifying sections.
    # Checking their names is safe: the code never prints the actual secret key.
    expected_parts = (
        "Endpoint=sb://",
        "SharedAccessKeyName=",
        "SharedAccessKey=",
    )

    # `all(...)` returns True only when every required section occurs in the value. Fail here
    # with an actionable message rather than letting the SDK report a generic malformed value.
    if not all(part in connection_string for part in expected_parts):
        raise RuntimeError(
            "SERVICEBUS_CONNECTION_STRING is empty or malformed. Set it to the complete "
            "Primary Connection String for the demo-send-listen policy. It starts with "
            "'Endpoint=sb://' and includes both 'SharedAccessKeyName=' and "
            "'SharedAccessKey='; do not use the namespace hostname, primary key alone, "
            "or the placeholder from the README."
        )

    # Return the validated connection string to main without ever displaying its secret key.
    return connection_string


def main():
    # This helper validates the secret's shape without exposing it. The remaining entity-name
    # lookups use square brackets so Python raises a clear KeyError if one was not configured.
    connection_string = get_connection_string()
    queue_name = os.environ["SERVICEBUS_QUEUE_NAME"]
    topic_name = os.environ["SERVICEBUS_TOPIC_NAME"]
    all_subscription_name = os.environ["SERVICEBUS_ALL_SUBSCRIPTION_NAME"]
    priority_subscription_name = os.environ["SERVICEBUS_PRIORITY_SUBSCRIPTION_NAME"]

    # `.hex` gives a compact text representation of the UUID; slicing `[:8]` keeps the demo
    # MessageIds readable while still making a second run distinct.
    run_id = uuid4().hex[:8]

    # `from_connection_string` builds a client from the learning-only SAS credential exported in
    # the README. Production applications should generally use DefaultAzureCredential with a
    # managed identity instead, so no connection-string secret needs to be stored.
    with ServiceBusClient.from_connection_string(connection_string) as client:
        # One open client can create several short-lived senders and receivers for the same
        # namespace, avoiding repeated connection setup.
        send_demo_messages(client, queue_name, topic_name, run_id)
        process_queue_messages(client, queue_name)
        inspect_and_clear_dead_letters(client, queue_name)
        receive_subscription_messages(client, topic_name, all_subscription_name)
        receive_subscription_messages(client, topic_name, priority_subscription_name)


# This guard runs main only when this file is executed with
# `python send_receive_deadletter.py`. It does not run automatically if another Python file
# imports this module.
if __name__ == "__main__":
    main()
