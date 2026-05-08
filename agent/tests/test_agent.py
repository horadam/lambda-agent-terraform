import json
import unittest
from unittest.mock import MagicMock, patch


def make_text_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def make_tool_use_response(tool_use_id: str, tool_name: str) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_use_id
    block.name = tool_name
    block.input = {}
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def make_mock_client(side_effect=None, return_value=None):
    mock_client = MagicMock()
    if side_effect:
        mock_client.messages.create.side_effect = side_effect
    else:
        mock_client.messages.create.return_value = return_value
    return mock_client


class TestRunAgent(unittest.TestCase):
    @patch("agent.agent._get_client")
    def test_direct_text_response(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(
            return_value=make_text_response("Hello, world!")
        )

        from agent.agent import run_agent
        result = run_agent("Say hello")

        self.assertEqual(result, "Hello, world!")
        self.assertEqual(mock_get_client.return_value.messages.create.call_count, 1)

    @patch("agent.agent._get_client")
    def test_tool_use_loop(self, mock_get_client):
        tool_response = make_tool_use_response("tool_123", "get_current_time")
        final_response = make_text_response("The time is 2026-05-07 12:00:00.")
        mock_get_client.return_value = make_mock_client(
            side_effect=[tool_response, final_response]
        )

        from agent.agent import run_agent
        result = run_agent("What time is it?")

        self.assertIn("time", result.lower())
        self.assertEqual(mock_get_client.return_value.messages.create.call_count, 2)

        second_call_messages = mock_get_client.return_value.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]
        self.assertEqual(tool_result_msg["role"], "user")
        self.assertEqual(tool_result_msg["content"][0]["type"], "tool_result")
        self.assertEqual(tool_result_msg["content"][0]["tool_use_id"], "tool_123")


class TestHandler(unittest.TestCase):
    @patch("agent.agent._get_client")
    def test_handler_success(self, mock_get_client):
        mock_get_client.return_value = make_mock_client(
            return_value=make_text_response("42")
        )

        from agent.handler import handler
        event = {"body": json.dumps({"input": "What is the answer?"})}
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["output"], "42")

    def test_handler_missing_input_key(self):
        from agent.handler import handler
        event = {"body": json.dumps({"wrong_key": "data"})}
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("error", body)

    def test_handler_malformed_body(self):
        from agent.handler import handler
        event = {"body": "not-json"}
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
