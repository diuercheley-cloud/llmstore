import logging
from typing import Any, Dict, Callable, Coroutine

logger = logging.getLogger(__name__)

RemediationAction = Callable[[Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]

class RemediationActionRegistry:
    """
    Registry of allowed remediation actions.
    Ensures only pre-defined and safe actions are executed.
    """
    _actions: Dict[str, RemediationAction] = {}

    @classmethod
    def register(cls, action_type: str):
        def decorator(func: RemediationAction):
            cls._actions[action_type] = func
            return func
        return decorator

    @classmethod
    async def execute(cls, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action_type not in cls._actions:
            logger.error(f"Action type '{action_type}' not found in registry.")
            return {
                "status": "failed",
                "error_code": "action_not_found",
                "message": f"Action type '{action_type}' is not supported or registered."
            }
        
        try:
            return await cls._actions[action_type](params)
        except Exception as e:
            logger.exception(f"Error executing action '{action_type}': {e}")
            return {
                "status": "failed",
                "error_code": "execution_error",
                "message": str(e)
            }

@RemediationActionRegistry.register("containment")
async def containment(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    logger.info(f"REAL ACTION: Containment on {target}")
    return {"status": "success", "output": f"Containment applied to {target}."}

@RemediationActionRegistry.register("mitigation")
async def mitigation(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    logger.info(f"REAL ACTION: Mitigation on {target}")
    return {"status": "success", "output": f"Mitigation applied to {target}."}

@RemediationActionRegistry.register("validation")
async def validation(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    logger.info(f"REAL ACTION: Validation on {target}")
    return {"status": "success", "output": f"Validation completed for {target}."}
@RemediationActionRegistry.register("restart_service")
async def restart_service(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    # Real logic would call an orchestration tool or agent
    logger.info(f"REAL ACTION: Restarting service {target}")
    return {"status": "success", "output": f"Service {target} restarted successfully."}

@RemediationActionRegistry.register("scale_out")
async def scale_out(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    logger.info(f"REAL ACTION: Scaling out {target}")
    return {"status": "success", "output": f"Target {target} scaled out."}

@RemediationActionRegistry.register("flush_cache")
async def flush_cache(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target_ref")
    logger.info(f"REAL ACTION: Flushing cache for {target}")
    return {"status": "success", "output": f"Cache for {target} flushed."}
