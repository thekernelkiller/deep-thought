import streamlit as st
import requests
import json

# Configure page settings
st.set_page_config(
    page_title="AI Chat Companion",
    page_icon="💬",
    layout="wide"
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Project Deep Thought")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What would you like to discuss?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Show thinking message
        message_placeholder.markdown("🤔 Thinking...")
        
        try:
            # Send request to FastAPI backend with chat history
            response = requests.post(
                "http://localhost:8000/chat",
                json={
                    "text": prompt,
                    "history": st.session_state.messages[:-1]  # Exclude current message
                }
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            
            full_response = response.json()["response"]
            message_placeholder.markdown(full_response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            message_placeholder.markdown("❌ An error occurred. Please try again.")

# Add a clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()