import json
import os
import time
from typing import Optional
from urllib.parse import urljoin
import fusion

error_codes = {"INTERNAL", "NOT_FOUND", "ALREADY_EXISTS", "INVALID_ARGUMENT", "NOT_AUTHENTICATED",
               "PERMISSION_DENIED", "NOT_IMPLEMENTED", "FAILED_PRECONDITION", "CONFLICT", "FAILED_TRANSACTION"}


ENV_VAR_FUSION_ISSUER_ID = "FUSION_ISSUER_ID"
ENV_VAR_FUSION_PRIVATE_KEY_FILE = "FUSION_PRIVATE_KEY_FILE"
ENV_VAR_FUSION_TOKEN_ENDPOINT = "FUSION_TOKEN_ENDPOINT"
ENV_VAR_FUSION_API_HOST = "FUSION_API_HOST"
ENV_VAR_FUSION_ACCESS_TOKEN = "FUSION_ACCESS_TOKEN"
BASE_PATH = "api/v1"


def get_fusion_config() -> fusion.Configuration:
    """
    Configure OAuth2 access token for authorization.
    Retrieve Fusion configuration with custom `issuer_id`, `private_key_file`, `host` and `token_endpoint`.

    Raises:
        Exception

    Returns:
        fusion.Configuration
    """
    config = fusion.Configuration()

    # required values
    if (ENV_VAR_FUSION_ISSUER_ID not in os.environ or ENV_VAR_FUSION_PRIVATE_KEY_FILE not in os.environ) and ENV_VAR_FUSION_ACCESS_TOKEN not in os.environ:
        raise ValueError(
            f"Environmental variables neither '{ENV_VAR_FUSION_ISSUER_ID}' and '{ENV_VAR_FUSION_PRIVATE_KEY_FILE} nor '{ENV_VAR_FUSION_ACCESS_TOKEN}' are set!"
        )

    if ENV_VAR_FUSION_ACCESS_TOKEN in os.environ:
        config.access_token = os.environ[ENV_VAR_FUSION_ACCESS_TOKEN]
    if ENV_VAR_FUSION_ISSUER_ID in os.environ and ENV_VAR_FUSION_PRIVATE_KEY_FILE in os.environ:
        config.issuer_id = os.environ[ENV_VAR_FUSION_ISSUER_ID]
        config.private_key_file = os.environ[ENV_VAR_FUSION_PRIVATE_KEY_FILE]

    # optional values
    if ENV_VAR_FUSION_API_HOST in os.environ:
        config.host = urljoin(os.environ[ENV_VAR_FUSION_API_HOST], BASE_PATH)
    if ENV_VAR_FUSION_TOKEN_ENDPOINT in os.environ:
        config.token_endpoint = os.environ[ENV_VAR_FUSION_TOKEN_ENDPOINT]

    return config


def wait_operation_finish(op_id: str, client: fusion.ApiClient, timeout: Optional[float] = None) -> fusion.models.operation.Operation:
    """
    wait_operation_finish wait until operation status is Succeeded or Failed. Then returns you that operation.
    if the operation takes longer than expected, it will raise an Exception

    Args:
        op_id (str): the id of operation
        client (fusion.ApiClient):
        timeout: timeout after which the function will exit

    Raises:
        Exception

    Returns:
        fusion.models.operation.Operation
    """
    op_cli = fusion.OperationsApi(client)
    start_time = time.now()
    while True:
        op = op_cli.get_operation(op_id)
        if op.status == "Succeeded" or op.status == "Failed":
            return op
        if timeout is not None and time.now() - start_time > timeout:
            raise RuntimeError("Waiting for operation timed out.")
        time.sleep(op.retry_in / 1000)


def wait_operation_succeeded(op_id: str, client: fusion.ApiClient) -> fusion.models.operation.Operation:
    """
    wait_operation_succeeded calls wait_operation_finish and expect the result is succeeded.
    if the operation is in other status, it will raise an expection

    Args:
        op_id (str)
        client (fusion.ApiClient)

    Raises:
        Exception

    Returns:
        fusion.models.operation.Operation
    """
    op = wait_operation_finish(op_id, client)

    if op.status == "Succeeded":
        return op
    else:
        # this is how we handle asynchronous error
        # if operation failed, the error field should be set. We can check it by op.error
        # op.error uses fusion.models.error.Error
        print_error(op.error)
        raise Exception(f"operation did not succeed! {op}")


def ApiException_to_ErrorResponse(e: fusion.rest.ApiException) -> fusion.models.error_response.ErrorResponse:
    """
        the current swagger spec only allow the response of most request to be Operation.
        So when it sees different response body such as ErrorResponse it will raise an ApiException.
        But the body of ApiException still contains all information for ErrorResponse.
        This function is used to convert the ApiException to ErrorResponse.

    Args:
        e (fusion.rest.ApiException)

    Returns:
        fusion.models.error_response.ErrorResponse
    """
    error_response_dict = json.loads(e.body)
    err_dict = error_response_dict['error']
    err = fusion.models.error.Error(**err_dict)
    return fusion.models.error_response.ErrorResponse(request_id=error_response_dict['request_id'], error=err)


def print_error(err: fusion.models.error.Error):
    """
    this function prints all fields in Error

    Args:
        err (fusion.models.error.Error)
    """
    if err is None:
        return
    if err.pure_code in error_codes:
        pass
    else:
        print("unknown pure code")
    print(f"pure_code={err.pure_code}; http_code={err.http_code}; message={err.message}; details={err.details}")
