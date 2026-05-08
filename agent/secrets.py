import json
import os

import boto3


def _load_api_key() -> None:
    secret_name = os.environ.get("SECRET_NAME")
    if not secret_name:
        return  # local dev: set ANTHROPIC_API_KEY directly in the environment

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    os.environ["ANTHROPIC_API_KEY"] = response["SecretString"]


# Runs once per Lambda container (cached on warm invocations).
_load_api_key()
