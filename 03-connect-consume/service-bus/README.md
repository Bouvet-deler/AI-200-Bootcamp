# Azure Service Bus

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Queue and process back-end operations by using Azure Service Bus,
including dead-letter queue handling, messages, topics, and subscriptions*

> 🚧 **Stub** — fill this in using [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md)
> and the fully-written [KQL guide](../../04-secure-monitor/kql/) as the quality bar.

## What it is

An enterprise **message broker**. A **queue** decouples producer from consumer (one-to-one);
**topics + subscriptions** fan a message out to many consumers (publish/subscribe). Messages
that keep failing land in a **dead-letter queue (DLQ)** for inspection.

## Why it's on the exam

Sending/receiving messages; queues vs topics/subscriptions; handling the DLQ; peek-lock vs
receive-and-delete.

## Core concepts · Setup · Hands-on (Python) · Exam gotchas · Quiz yourself · Further reading

_To be written._
