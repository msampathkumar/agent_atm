import agent_atm as atm
from agent_atm import LLMPayload


def run_demo():
    print("\n=== 1. Initializing agent-atm ===")
    # Initialize the singleton instance with SQLite database storage
    atm.init(
        data_manager="sqlite", db_path="usage.db", default_app_id="finance-advisor"
    )
    print("ATM initialized with SQLite manager (db: usage.db)")

    print("\n=== 2. Registering Hooks ===")

    @atm.hook("pre")
    def auditor_pre_hook(event):
        print(
            f"   [Pre-hook] Auditing event. Type: {event.event_type}, Tokens: {event.token_count}"
        )
        if event._additional_metadata_config:
            print(
                f"             Custom Config metadata: {event._additional_metadata_config}"
            )
        if event._additional_metadata_tags:
            print(f"             Tags metadata: {event._additional_metadata_tags}")

    @atm.hook("post")
    def slack_alert_post_hook(event):
        if event.token_count > 5000:
            print("   [Post-hook] ALERT: Extremely large request detected!")

    print("Pre and Post hooks successfully registered.")

    print("\n=== 3. Setting Up Token Quota Limits ===")
    # Set daily quota of 10,000 tokens for VIP users
    atm.limits.add(
        scope=atm.Scope(user="vip-user"),
        quota=atm.Quota(day_limit=10000),
        alert_level=atm.AlertLevel.BLOCKING,
    )

    # Set a strict limit of 100 tokens per minute for free-tier users
    atm.limits.add(
        scope=atm.Scope(user="free-user"),
        quota=atm.Quota(minute_limit=100),
        alert_level=atm.AlertLevel.BLOCKING,
    )

    print("Quota Limit Rules successfully configured.")

    print("\n=== 4. Running Context Enriched Requests ===")
    # Use context scoping to inject user, session, list tags, and arbitrary key-value configs
    with atm.context(
        session_id="session-abc-123",
        username="vip-user",
        _additional_metadata_tags=["prod", "investments"],
        department="wealth-management",
        customer_tier="platinum",
    ):
        print("Logging user prompt event...")
        atm.add_user_request(
            content="What are the top stocks to buy right now?",
            token_count=12,  # Explicit token count
        )

        print("Logging model response event...")
        atm.add_model_response(
            content="Based on current market capitalization...",
            token_count=35,  # Explicit token count
        )

    print("\n=== 5. Direct LLMPayload Dataclass Recording ===")
    # Passing a structured payload directly
    payload = LLMPayload(
        content="Provide stock option evaluation matrix.",
        model_id="gemini-pro",
        token_count_override=150,
        _additional_metadata_tags=["custom-payload"],
        _additional_metadata_config={"evaluation": "options"},
    )
    print("Logging user request via direct LLMPayload instance...")
    atm.add_user_request(payload)

    response_payload = LLMPayload(
        content="Here is the option evaluation matrix based on Black-Scholes...",
        model_id="gemini-pro",
        token_count_override=250,
        event_type="response",
        _additional_metadata_tags=["custom-payload"],
        _additional_metadata_config={"evaluation": "options"},
    )
    print("Logging model response via direct LLMPayload instance...")
    atm.add_model_response(response_payload)

    print("\n=== 6. Simulating Quota Breach (Free User) ===")
    with atm.context(
        username="free-user", app_id="basic-portal", department="marketing"
    ):
        print("First LLM call (40 tokens request + 30 tokens response)...")
        atm.add_user_request("Tell me a short joke.", token_count=40)
        atm.add_model_response(
            "Why don't scientists trust atoms? Because they make up everything!",
            token_count=30,
        )

        print(
            "Second LLM call (40 tokens request + 30 tokens response - Should breach minute limit of 100)..."
        )
        try:
            # Total tokens: 40 (req) + 30 (resp) + 40 (req) = 110 > 100
            atm.add_user_request("Tell me another short joke.", token_count=40)
        except atm.TokenQuotaExceeded as e:
            print(f"   [Quota Exceeded Exception Captured!]: {e}")

    print("\n=== Demo Execution Complete ===")
    print("Run uvicorn to view live telemetry in the beautiful dashboard:")
    print("    ATM_DB_PATH=usage.db uvicorn agent_atm.dashboard.server:app --reload\n")


if __name__ == "__main__":
    run_demo()
