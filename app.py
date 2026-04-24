import streamlit as st
import requests
import os
import re
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# ===============================
# 1. Setup & Configuration
# ===============================
load_dotenv()
API_KEY = os.getenv("GLM_API_KEY")
API_URL = "https://api.ilmu.ai/api/paas/v4/chat/completions"

# ===============================
# 2. Advanced HR Database
# ===============================
class HRSystem:
    def __init__(self):
        # User Data
        if "users" not in st.session_state:
            st.session_state.users = {
                "meena": {"pw": "meena123", "role": "employee", "dept": "Engineering"},
                "daksha": {"pw": "daksha123", "role": "employee", "dept": "Engineering"},
                "lesh": {"pw": "lesh123", "role": "employee", "dept": "Sales"},
                "meenash": {"pw": "meenash123", "role": "employee", "dept": "Sales"},
                "manager": {"pw": "admin123", "role": "manager", "dept": "HR"}
            }
        
        # Balances & Monthly Tracking
        if "leave_balances" not in st.session_state:
            st.session_state.leave_balances = {
                "meena": {"annual": 12, "sick": 15, "emergency": 5},
                "daksha": {"annual": 12, "sick": 12, "emergency": 4},
                "lesh": {"annual": 10, "sick": 10, "emergency": 3},
                "meenash": {"annual": 15, "sick": 15, "emergency": 6}
            }
        
        # Track monthly usage & Attendance Allowance (True = eligible)
        if "monthly_stats" not in st.session_state:
            st.session_state.monthly_stats = {u: {"annual": 0, "sick": 0, "emergency": 0, "allowance": True} for u in st.session_state.users}
            
        if "approved_leaves" not in st.session_state: st.session_state.approved_leaves = {} # Format: {date: {dept: [users]}}
        if "pending_review" not in st.session_state: st.session_state.pending_review = []
        if "leave_history" not in st.session_state: st.session_state.leave_history = []

    def check_manpower(self, dept, leave_date):
        # Rule: Min 1 person must remain in Engineering/Sales
        dept_info = {"Engineering": 2, "Sales": 2} # Total members
        min_staff = 1
        already_out = len(st.session_state.approved_leaves.get(leave_date, {}).get(dept, []))
        return (dept_info.get(dept, 2) - already_out) > min_staff

db = HRSystem()

# ===============================
# 3. Logic & Processing
# ===============================
def process_leave(user, l_type, days, l_date, reason):
    dept = st.session_state.users[user]["dept"]
    limits = {"annual": 2, "sick": 1, "emergency": 1}
    
    # 1. Balance Check
    if days > st.session_state.leave_balances[user][l_type]:
        return f"❌ **Rejected:** Insufficient balance. **Alternatives:**\n- Take Unpaid Leave\n- Request a half-day (0.5) instead.", "rejected"

    # 2. Monthly Limit & Allowance Check
    current_month_usage = st.session_state.monthly_stats[user][l_type]
    if (current_month_usage + days) > limits[l_type]:
        st.session_state.pending_review.append({"user": user, "type": l_type, "days": days, "date": l_date, "reason": reason, "issue": "Limit Exceeded"})
        return "⚠️ **Limit Exceeded:** This request exceeds your monthly limit. It's sent to your manager for review. Note: Your **Attendance Allowance** will be revoked if approved.", "pending"

    # 3. Manpower Check
    if not db.check_manpower(dept, l_date):
        st.session_state.pending_review.append({"user": user, "type": l_type, "days": days, "date": l_date, "reason": reason, "issue": "Low Manpower"})
        return "⚠️ **Manpower Alert:** Too many people are away on this date. Sent to Manager for override review.", "pending"

    # 4. Auto-Approval
    st.session_state.leave_balances[user][l_type] -= days
    st.session_state.monthly_stats[user][l_type] += days
    if l_date not in st.session_state.approved_leaves: st.session_state.approved_leaves[l_date] = {}
    if dept not in st.session_state.approved_leaves[l_date]: st.session_state.approved_leaves[l_date][dept] = []
    st.session_state.approved_leaves[l_date][dept].append(user)
    
    st.session_state.leave_history.append({"user": user, "type": l_type, "days": days, "date": l_date, "status": "Approved"})
    return f"✅ **Approved!** Your {l_type} leave for {l_date} is confirmed.", "approved"

# ===============================
# 4. UI Rendering
# ===============================
st.set_page_config(page_title="Aurora AI HR", layout="wide")

if "logged_in" not in st.session_state:
    st.title("🤖 Aurora AI Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u]["pw"] == p:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.session_state.role = st.session_state.users[u]["role"]
            st.session_state.messages = []
            st.rerun()
else:
    # Sidebar
    with st.sidebar:
        st.title(f"👤 {st.session_state.username.title()}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        
        if st.session_state.role != "manager":
            st.markdown("---")
            st.subheader("Balances")
            st.write(f"Annual: {st.session_state.leave_balances[st.session_state.username]['annual']}")
            st.write(f"Sick: {st.session_state.leave_balances[st.session_state.username]['sick']}")
            allowance = "✅ Active" if st.session_state.monthly_stats[st.session_state.username]["allowance"] else "❌ Revoked"
            st.write(f"Attendance Allowance: {allowance}")

    # Main Chat
    st.title("🤖 Aurora AI HR Assistant")
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("I need leave..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        # AI Integration (Mocking logic for fast demo)
        # In a real presentation, GLM would extract these 4 fields:
        l_type = "annual" if "annual" in prompt.lower() else "sick" if "sick" in prompt.lower() else "emergency"
        days = 1 # Simplified extraction
        l_date = "2025-04-25"
        
        response, status = process_leave(st.session_state.username, l_type, days, l_date, prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Manager View
    if st.session_state.role == "manager":
        st.markdown("---")
        st.header("👑 Manager Dashboard")
        if not st.session_state.pending_review:
            st.info("No pending requests.")
        for i, req in enumerate(st.session_state.pending_review):
            with st.expander(f"Review: {req['user']} ({req['issue']})"):
                st.write(f"Request: {req['days']} day(s) of {req['type']} on {req['date']}")
                c1, c2 = st.columns(2)
                if c1.button("Approve Anyway", key=f"app_{i}"):
                    if req['issue'] == "Limit Exceeded":
                        st.session_state.monthly_stats[req['user']]["allowance"] = False
                    st.session_state.leave_history.append({"user": req['user'], "type": req['type'], "days": req['days'], "date": req['date'], "status": "Approved (Manager Override)"})
                    st.session_state.pending_review.pop(i)
                    st.rerun()
                if c2.button("Reject", key=f"rej_{i}"):
                    st.session_state.pending_review.pop(i)
                    st.rerun()