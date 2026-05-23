import asyncio
import logging
import signal
from app.core.logging import configure_logging
from app.services.agents.agent_worker import AgentWorkerService
from app.db.session import engine

configure_logging()
logger = logging.getLogger(__name__)

async def main() -> None:
    logger.info("Initializing Agent Worker Service...")
    worker = AgentWorkerService()
    
    loop = asyncio.get_running_loop()
    
    async def shutdown(sig_name: str):
        logger.info(f"Received exit signal {sig_name}. Shutting down worker...")
        await worker.stop()
        logger.info("Worker stopped. Exiting main.")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

    def handle_drain(sig_name: str):
        logger.info(f"Received {sig_name}. Entering drain mode...")
        worker.drain()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s.name)))
        except NotImplementedError:
            pass
            
    try:
        loop.add_signal_handler(signal.SIGUSR1, lambda: handle_drain("SIGUSR1"))
    except (NotImplementedError, AttributeError):
        pass

    await worker.start()

    logger.info("Agent Worker daemon loop started.")
    try:
        while worker.is_running:
            try:
                processed = await worker.run_once()
                if not processed:
                    await asyncio.sleep(1.0)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in agent worker run loop: {e}", exc_info=True)
                await asyncio.sleep(2.0)
    finally:
        if worker.is_running:
            await worker.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Agent Worker terminated.")
    finally:
        try:
            asyncio.run(engine.dispose())
        except Exception:
            pass
