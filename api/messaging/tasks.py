import logging

from core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name='publish_event', ignore_result=True)
def publish_event(event_type: str, payload: dict, queue: str = 'default'):
    """
    The generic Celery task that acts as the Event Bus publisher.

    It determines which listener task should receive the event based on event_type
    and then dispatches the message. In a simple Celery setup, this is often
    done by routing or by calling the appropriate listener task directly.

    NOTE: In a real-world Kafka/RabbitMQ system, this task would instead
    send the serialized payload to the broker. Here, we use direct task calls
    to simulate the routing functionality.
    """
    logger.info("Event Bus received event: %s | Payload keys: %s", event_type, list(payload.keys()))

    celery_app.send_task(
        event_type,                     # The task name is the event type
        args=[event_type, payload],     # Listener tasks expect (event_type, payload)
        queue=queue                     # Specify the queue to route the task
        # The broker (and settings.py) will use the task name (event_type)
        # to apply further routing.
    )