import streamlit as st

# --- MOCK DATA (Simulating the HR Database) ---
USER_BALANCE = 12
TEAM_BUSY_DATE = "2026-04-24"

def process_leave(text):
    """
    This function acts as your 'AI logic'. 
    In a full version, this would call the Gemini GLM API.
    """
    # Simple extraction logic for the prototype
    target_date = "2026-04-25" 
    
    if target_date == TEAM_BUSY_DATE:
        return "❌ DENIED: Team capacity reached for April 24th. Please pick another day."
    
    if "urgent" in text.lower():
        return f"✅ APPROVED (Urgent): Date {target_date} logged. New Balance: {USER_BALANCE - 1} days."
    
    return f"⏳ PENDING: Your request for {target_date} has been sent to HR for review."

# --- STREAMLIT UI ---
st.set_page_config(page_title="Aurora AI HR", page_icon="🤖")

st.title("🤖 Aurora AI HR Assistant")
st.write(f"Hello, **Daksha**! Your current leave balance: **{USER_BALANCE} days**")

st.divider()

# User Input Box
user_input = st.text_input("How can I help you today?", placeholder="e.g. I need leave on 25th April, urgent")

if st.button("Submit Request"):
    if user_input:
        with st.spinner("AI is analyzing your request and checking calendar..."):
            # Call our logic function
            response = process_leave(user_input)
            
            st.success("Analysis Complete!")
            st.info(f"**AI Response:** {response}")
    else:
        st.warning("Please enter your leave request details first.")

st.sidebar.markdown("### Team: Aurora Architects 🏗️")
st.sidebar.info("UM Hackathon 2026 Prototype")