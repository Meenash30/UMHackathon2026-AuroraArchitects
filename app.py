import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load API Key from .env file
load_dotenv()
API_KEY = os.getenv("GLM_API_KEY")

# USE ILMU.AI URL (Matches your console login)
API_URL = "https://api.ilmu.ai/api/paas/v4/chat/completions"

# Phase 3, Step 14: Mock Database
leave_balances = {
    "Daksha": 12,
    "Lesh": 10,
    "Meenash": 15
}

st.set_page_config(page_title="Aurora AI HR Assistant", page_icon="🤖")
st.title("🤖 Aurora AI HR Assistant")
st.markdown("I can help you with leave requests and balance checks.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare data for API
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Instruction for the AI (The "Agentic" part)
    system_prompt = {
        "role": "system", 
        "content": "You are an HR Assistant. If a user asks for leave, ensure you get: 1. Date, 2. Duration, 3. Reason. Once you have all three pieces of info, you MUST include the exact phrase 'Processing your request...' in your reply."
    }
    
    payload = {
        "model": "glm-4", 
        "messages": [system_prompt] + st.session_state.messages
    }

    with st.chat_message("assistant"):
        try:
            # Try real API call
            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            full_response = response.json()['choices'][0]['message']['content']
            
            # Step 14 Logic: Check database if AI is ready to approve
            if "Processing your request" in full_response:
                user_name = "Meenash" # Mocking the logged-in user
                balance = leave_balances.get(user_name, 0)
                full_response += f"\n\n--- \n🔍 **Database Check:** \nUser: {user_name} \nRemaining Balance: {balance} days. \n**Status: Approved** ✅"
            
            st.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            # Safety Fallback if API fails
            st.warning("Switching to offline mode...")
            mock_res = "I'm having trouble connecting to my brain, but I can see you want leave. Please provide the date, duration, and reason!"
            if "april" in prompt.lower():
                 mock_res = f"Processing your request... \n\n🔍 **Database Check:** Your balance is {leave_balances['Meenash']} days. Approved!"
            
            st.markdown(mock_res)
            st.session_state.messages.append({"role": "assistant", "content": mock_res})