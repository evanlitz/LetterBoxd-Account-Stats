"""
Test which Claude models are available with your API key.
"""

from anthropic import Anthropic
from config import Config

def test_models():
    """Test different Claude model names to see which ones work."""

    print("\nTesting Claude API models...")
    print("="*60)

    client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # List of model names to try
    models_to_test = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-haiku-20241022",
    ]

    working_models = []

    for model_name in models_to_test:
        try:
            print(f"\nTrying: {model_name}...", end=" ")

            # Try a minimal API call
            response = client.messages.create(
                model=model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )

            print("✓ WORKS!")
            working_models.append(model_name)

        except Exception as e:
            if "404" in str(e) or "not_found" in str(e):
                print("✗ Not found (404)")
            elif "401" in str(e):
                print("✗ Authentication error")
            elif "429" in str(e):
                print("✗ Rate limited")
            else:
                print(f"✗ Error: {str(e)[:50]}")

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    if working_models:
        print(f"\n✓ Working models ({len(working_models)}):")
        for model in working_models:
            print(f"  - {model}")

        print(f"\nRecommendation: Use '{working_models[0]}' in config.py")
        print(f"\nUpdate config.py line 31 to:")
        print(f'    CLAUDE_MODEL = "{working_models[0]}"')
    else:
        print("\n✗ No working models found!")
        print("\nPossible issues:")
        print("  1. Check your ANTHROPIC_API_KEY in .env file")
        print("  2. Verify your API key is active at https://console.anthropic.com")
        print("  3. Make sure you have credits in your account")
        print("  4. Your API key might be for a different tier/version")

if __name__ == "__main__":
    test_models()
