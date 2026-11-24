---
id: pf-poison-message
title: Poison message blocking or failing a partition
service: payflow
version: 1
updated: 2026-11-20
---
# Poison message on a partition

## Symptoms
- Lag grows on exactly one partition while the others are near zero.
- The processor log repeats the same `partition=N offset=M` with a deserialisation or validation error.

## Why it usually does not block
Malformed JSON and validation failures are configured as non-retryable, so they go to the DLT on the first attempt and the partition moves on. If a partition **is** stuck, the error is being classified as retryable by mistake: blocking retries hold the partition for the in-place attempts (~0.5 s apart), then the message hops to a retry topic.

## Steps
1. Find the offset: processor logs, or `kafka-console-consumer.sh --partition N --offset M --max-messages 1`.
2. Check the exception class. If it is a `DeserializationException`, `MethodArgumentNotValidException` or `IllegalArgumentException` and it was retried, the non-retryable list in `RetryConfig` is missing that class. That is a code fix.
3. Short-term: the message will reach the DLT after the 4th attempt anyway (about 7 seconds). Do not skip offsets by hand.
