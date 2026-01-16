from gradio_chat_agent.ui.theme import AgentTheme

def test_agent_theme_initialization():
    theme = AgentTheme()
    # Verify that standard color variables are available, implying successful initialization of Base
    # We check for generated attributes that Gradio themes typically expose or use internally
    # Since we cannot easily check constructor arguments on the object, we check for side effects
    
    # Gradio themes set attributes like `primary_50`, `primary_100`, etc. based on the hue.
    assert hasattr(theme, "primary_50")
    assert hasattr(theme, "primary_500")
    
    assert hasattr(theme, "secondary_50")
    assert hasattr(theme, "secondary_500")
    
    assert hasattr(theme, "neutral_50")
    assert hasattr(theme, "neutral_500")