import requests
import json
import logging

logger = logging.getLogger(__name__)


def post_request(url: str, payload: dict, timeout: int = 300) -> str:
    """
    Generic HTTP POST request wrapper, handles errors and JSON parsing
    """
    try:
        logger.info(f"Sending request to {url} with payload size: {len(str(payload))}")
        response = requests.post(url, json=payload, timeout=timeout)

        if response.status_code != 200:
            return f"Service Error ({response.status_code}): {response.text}"

        result_json = response.json()

        if "error" in result_json:
            return f"Tool Execution Failed: {result_json['error']}"

        return json.dumps(result_json, ensure_ascii=False)

    except requests.exceptions.ConnectionError:
        return f"Connection Error: Cannot reach service at {url}. Is the container running?"
    except Exception as e:
        return f"Internal Tool Error: {str(e)}"