import agent_atm as atm

def main():
    print("Hello from adk-app-with-atm-as-webserver!")
    # Initialize ATM with remote data manager pointing to standalone server
    atm.init(data_manager="remote", base_url="http://127.0.0.1:8000", default_app_id="adk-remote-bot", telemetry_failure_policy="warn")
    
    user_prompt = "Generate a quarterly revenue summary."
    print(f"User Prompt: {user_prompt}")
    
    with atm.context(username="remote_user", session_id="sess_remote_202"):
        req_ev = atm.add_user_request(user_prompt, token_count=25, model_id="gemini-2.5-flash")
        print(f"--> Remote Logged Request: {req_ev.token_count} tokens")
        
        model_resp = "Quarterly revenue increased by 14% across all regions."
        resp_ev = atm.add_model_response(model_resp, token_count=80, model_id="gemini-2.5-flash")
        print(f"--> Remote Logged Response: {resp_ev.token_count} tokens")

    print("adk-app-with-atm-as-webserver execution completed successfully.")

if __name__ == "__main__":
    main()
