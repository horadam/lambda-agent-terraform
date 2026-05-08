import json
import logging
import agent.secrets  # noqa: F401 — sets ANTHROPIC_API_KEY in os.environ before client init
from agent.agent import run_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        body = json.loads(event["body"])
        user_input = body["input"]
        logger.info("input: %s", user_input)
        result = run_agent(user_input)
        logger.info("output: %s", result)
        return {"statusCode": 200, "body": json.dumps({"output": result})}
    except Exception as e:
        logger.exception("unhandled error")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
