import logging

logger = logging.getLogger("action_handler")

action_registry = {}    

def register_action(action_name):
    def decorator(func):
        print(f"Registering action: {action_name}")
        action_registry[action_name] = func
        print(f"Updated action registry: {action_registry}")
        return func
    return decorator

def execute_action(agent, action_name, **kwargs):
    print(f"Action registry: {action_registry}")
    if action_name in action_registry:
        return action_registry[action_name](agent, **kwargs)
    else:
        logger.error(f"Action {action_name} not found")
        return None
    

