import sys
from token_manager import init_atm
import agent_atm as atm


def main():
    print("Hello from adk-app-with-atm-as-localapp!")
    init_atm()

    # Simulate ADK Agent Chat interaction
    user_prompt = "Analyze this financial dataset."
    print(f"User Prompt: {user_prompt}")

    with atm.context(username="adk_user", session_id="sess_adk_101"):
        # Record user request
        req_ev = atm.add_user_request(user_prompt, token_count=15, model_id="gemini-2.5-pro")
        print(f"--> Logged Request: {req_ev.token_count} tokens")

        # Simulate ADK model response
        model_resp = "Financial dataset analysis complete. High growth potential detected."
        resp_ev = atm.add_model_response(model_resp, token_count=45, model_id="gemini-2.5-pro")
        print(f"--> Logged Response: {resp_ev.token_count} tokens")

    print("adk-app-with-atm-as-localapp execution completed successfully.")


if __name__ == "__main__":
    main()
