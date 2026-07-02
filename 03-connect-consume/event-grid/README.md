# Azure Event Grid

**Domain:** 03 — Connect to and consume Azure services (20–25%)
**Maps to skill:** *Implement event-driven workflows by using Azure Event Grid, including
filters, custom events, and retries*

> 🚧 **Stub** — fill this in using [`docs/TOPIC_TEMPLATE.md`](../../docs/TOPIC_TEMPLATE.md)
> and the fully-written [KQL guide](../../04-secure-monitor/kql/) as the quality bar.

## What it is

An **event routing** service. Publishers emit **events** ("something happened"); Event Grid
delivers them to subscribers, applying **filters** so each subscriber only gets what it cares
about. It **retries** failed deliveries automatically.

## Why it's on the exam

Publishing **custom events**, subscription **filters** (subject/event-type), and delivery
**retry**/dead-letter behavior. Know Event Grid (events) vs Service Bus (messages).

## Core concepts · Setup · Hands-on (Python) · Exam gotchas · Quiz yourself · Further reading

_To be written._
