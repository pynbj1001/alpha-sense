from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from openai import APIConnectionError, APITimeoutError

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["backend_url"] = "https://api.openai.com/v1"
config["deep_think_llm"] = "o4-mini"
config["quick_think_llm"] = "gpt-4.1-mini"
config["max_debate_rounds"] = 1
config["online_tools"] = True

# Initialize with custom config
ta = TradingAgentsGraph(debug=False, config=config)

# Forward propagate with network retry for transient API failures
max_attempts = 3
decision = None
for attempt in range(1, max_attempts + 1):
    try:
        _, decision = ta.propagate("NVDA", "2024-05-10")
        break
    except (APIConnectionError, APITimeoutError) as e:
        if attempt == max_attempts:
            raise
        print(
            f"[Attempt {attempt}/{max_attempts}] transient API error: {e}. Retrying..."
        )

print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
