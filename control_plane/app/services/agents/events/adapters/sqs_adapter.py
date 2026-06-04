# Owner: agent-platform
import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from aioboto3 import Session
    HAS_SQS = True
except ImportError:
    HAS_SQS = False
    logger.info("aioboto3 not installed; SQS adapter will use simulated mode")

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class SQSAdapter:
    """
    Adapter for AWS SQS event triggering.
    Supports both real (aioboto3/boto3) and simulated modes.
    """
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self._queue_url: str = ""

    def _is_enabled(self) -> bool:
        return getattr(self.settings, 'sqs_trigger_enabled',
                       getattr(self.settings, 'agent_event_driven_enabled', False))

    async def start_consumer(self, queue_url: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        if not self._is_enabled():
            logger.warning("SQS trigger is disabled. Skipping consumer start.")
            return

        self._callback = callback
        self._queue_url = queue_url
        self._running = True

        if HAS_SQS:
            session = Session()
            self._client = await session.client('sqs').__aenter__()
            self._task = asyncio.create_task(self._consume_loop())
            logger.info(f"SQS consumer started for queue: {queue_url}")
        elif HAS_BOTO3:
            self._client = boto3.client('sqs')
            self._task = asyncio.create_task(self._consume_loop_sync())
            logger.info(f"SQS consumer started (boto3 sync) for queue: {queue_url}")
        else:
            logger.info(f"SQS consumer started in simulated mode for queue: {queue_url}")

    async def _consume_loop(self):
        while self._running:
            try:
                response = await self._client.receive_message(
                    QueueUrl=self._queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                )
                messages = response.get('Messages', [])
                for msg in messages:
                    if not self._running:
                        break
                    try:
                        body = json.loads(msg['Body'])
                        await self._callback(body)
                        await self._client.delete_message(
                            QueueUrl=self._queue_url,
                            ReceiptHandle=msg['ReceiptHandle'],
                        )
                    except Exception as e:
                        logger.error(f"SQS callback error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SQS receive error: {e}")
                await asyncio.sleep(5)

    def _consume_loop_sync(self):
        import threading
        def _run():
            while self._running:
                try:
                    response = self._client.receive_message(
                        QueueUrl=self._queue_url,
                        MaxNumberOfMessages=10,
                        WaitTimeSeconds=20,
                    )
                    messages = response.get('Messages', [])
                    for msg in messages:
                        if not self._running:
                            break
                        try:
                            body = json.loads(msg['Body'])
                            asyncio.run_coroutine_threadsafe(
                                self._callback(body),
                                asyncio.get_event_loop(),
                            )
                            self._client.delete_message(
                                QueueUrl=self._queue_url,
                                ReceiptHandle=msg['ReceiptHandle'],
                            )
                        except Exception as e:
                            logger.error(f"SQS callback error: {e}")
                except Exception as e:
                    logger.error(f"SQS receive error: {e}")
                    import time
                    time.sleep(5)
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    async def stop_consumer(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if HAS_SQS and self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        logger.info("SQS consumer stopped")
