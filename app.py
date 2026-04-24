import streamlit as st
import re
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

st.set_page_config(
    page_title="Aurora AI HR Assistant",
    page_icon="🤖",
    layout="wide"
)

load_dotenv()
GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_URL = "https://api.ilmu.ai/v1/chat/completions"
GLM_MODEL = "ilmu-glm-5.1"

# ==========================================================
# CUSTOM CSS
# ==========================================================
st.markdown("""
<style>
.block-container{
    padding-top:3rem !important;
    padding-bottom:1rem;
}
section[data-testid="stSidebar"]{
    background: linear-gradient(180deg,#081028,#0f172a);
}
section[data-testid="stSidebar"] *{
    color:white !important;
}
section[data-testid="stSidebar"] .stButton > button{
    background:#2563eb !important;
    color:white !important;
    border:none !important;
    border-radius:10px !important;
    font-weight:700 !important;
    padding:10px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover{
    background:#1d4ed8 !important;
}
div.stButton > button{
    border-radius:10px;
    font-weight:700;
}
label{
    color:#111827 !important;
    font-weight:700 !important;
    font-size:18px !important;
}
input{
    background:white !important;
    color:black !important;
    border:2px solid #d1d5db !important;
    border-radius:10px !important;
}
.stButton > button{
    background:#2563eb;
    color:white;
    border:none;
    border-radius:10px;
    padding:10px 20px;
    font-weight:700;
}
.stButton > button:hover{
    background:#1d4ed8;
}
.big-title{
    font-size:56px;
    font-weight:900;
    color:#2563eb;
    text-align:center;
    margin-top:20px;
    margin-bottom:10px;
    line-height:1.2;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# SESSION STATE INIT
# ==========================================================
def init():
    if "users" not in st.session_state:
        st.session_state.users = {
            "meena":{"pw":"meena123","role":"employee","dept":"Engineering"},
            "daksha":{"pw":"daksha123","role":"employee","dept":"Engineering"},
            "lesh":{"pw":"lesh123","role":"employee","dept":"Sales"},
            "meenash":{"pw":"meenash123","role":"employee","dept":"Sales"},
            "manager":{"pw":"admin123","role":"manager","dept":"HR"},
        }

    if "leave_balances" not in st.session_state:
        st.session_state.leave_balances = {
            "meena":{"annual":12,"sick":15,"emergency":5},
            "daksha":{"annual":10,"sick":12,"emergency":4},
            "lesh":{"annual":8,"sick":10,"emergency":3},
            "meenash":{"annual":15,"sick":15,"emergency":6},
        }

    if "monthly_stats" not in st.session_state:
        st.session_state.monthly_stats = {
            u:{
                "annual":0,
                "sick":0,
                "emergency":0,
                "allowance":True
            }
            for u in st.session_state.users
        }

    if "history" not in st.session_state:
        st.session_state.history = {
            u:{
                "days":0,
                "requests":0,
                "reasons":[]
            }
            for u in st.session_state.users
        }

    if "approved_leaves" not in st.session_state:
        st.session_state.approved_leaves = {}

    if "pending_review" not in st.session_state:
        st.session_state.pending_review = []

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "leave_state" not in st.session_state:
        st.session_state.leave_state = {}

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Document storage
    if "leave_documents" not in st.session_state:
        st.session_state.leave_documents = {}

    # Notifications for employees
    if "notifications" not in st.session_state:
        st.session_state.notifications = {}

    # Per‑user chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

init()

# ==========================================================
# HELPERS
# ==========================================================
def call_glm_extract(user_message):
    if not GLM_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = """
You are an HR leave extraction engine. Understand leave requests only.

Return ONLY valid JSON. Never greet, explain, or give generic HR support text.

Fields:
- leave_type: "annual", "sick", or "emergency"
- days: number (0.5 for half day)
- date: YYYY-MM-DD (use today's date for "today", tomorrow's for "tomorrow")
- reason: short phrase
- reply: a very short, empathetic sentence acknowledging the request

Example:
{"leave_type":"sick","days":0.5,"date":"2025-04-26","reason":"medical appointment","reply":"I understand. Processing your half-day sick leave."}
"""
    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,
        "max_tokens": 120
    }
    try:
        r = requests.post(GLM_URL, headers=headers, json=payload, timeout=8)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]
        return json.loads(content)
    except Exception:
        return None

def detect_leave_type(text):
    t = text.lower()
    emergency = ["emergency","emmergency","urgent","accident","passed away","death","funeral","hospitalized","grandfather died","grandmother died","family emergency"]
    if any(kw in t for kw in emergency):
        return "emergency"
    sick = ["sick","doctor","clinic","mc","fever","flu","tired","exhausted","headache","migraine","not feeling well","cough","cold","stomach","vomit","diarrhea"]
    if any(kw in t for kw in sick):
        return "sick"
    annual = ["annual","holiday","vacation","travel","rest","trip","family trip","break","wedding","birthday"]
    if any(kw in t for kw in annual):
        return "annual"
    return None

def parse_days(text):
    t = text.lower()
    if "half" in t:
        return 0.5
    word_map = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    for w, val in word_map.items():
        if w in t:
            return val
    m = re.search(r'(\d+)', t)
    return int(m.group(1)) if m else None

def parse_date(text):
    t = text.lower()
    if "today" in t:
        return datetime.now().strftime("%Y-%m-%d")
    if "tomorrow" in t:
        return (datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.search(r'(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', t)
    if m:
        day = int(m.group(1))
        mon = m.group(2)
        months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
        return f"{datetime.now().year}-{months[mon]:02d}-{day:02d}"
    return None

def reliability_score(user):
    h = st.session_state.history[user]
    score = 100
    if h["requests"] > 2:
        score -= (h["requests"]-2)*20
    if h["days"] > 15:
        score -= 10
    if len(h["reasons"]) >= 3 and h["reasons"][-1] == h["reasons"][-2] == h["reasons"][-3]:
        score -= 10
    if h["requests"] == 0:
        score += 5
    return max(0, min(100, score))

def manpower_ok(dept, leave_date):
    dept_total = {"Engineering":2, "Sales":2}
    already = len(st.session_state.approved_leaves.get(leave_date, {}).get(dept, []))
    remain = dept_total.get(dept,2) - already - 1
    return remain >= 1

def is_duplicate_pending(user, leave_type, leave_date):
    for p in st.session_state.pending_review:
        if p["user"] == user and p["type"] == leave_type and p["date"] == leave_date:
            return True
    return False

def already_approved_for_date(user, leave_date):
    dept = st.session_state.users[user]["dept"]
    return user in st.session_state.approved_leaves.get(leave_date, {}).get(dept, [])

# ==========================================================
# PROCESS LEAVE (UPDATED: annual never goes to manager)
# ==========================================================
def process_leave(user, leave_type, days, leave_date, reason):
    dept = st.session_state.users[user]["dept"]
    score = reliability_score(user)
    limits = {"annual": 2, "sick": 3, "emergency": 2}
    balance = st.session_state.leave_balances[user][leave_type]
    used = st.session_state.monthly_stats[user][leave_type]

    # Duplicate approved leave check
    if already_approved_for_date(user, leave_date):
        return f"⚠️ You already have an approved leave on {leave_date}. Please choose a different date."

    # Proof required logic (already checked in conversation flow)
    has_proof = user in st.session_state.leave_documents
    if leave_type == "sick" and days >= 2 and not has_proof:
        return "⚠️ Medical certificate required for sick leave of 2 days or more. Please upload a document."
    if leave_type == "emergency" and not has_proof:
        return "⚠️ Please upload supporting proof (if available) for emergency leave."

    # ----- MANAGER REVIEW RULES (UPDATED) -----
    # Only Sick (>2 days) and Emergency (>1 day) go to manager
    # Annual leave never goes to manager (auto process)

    # Sick leave > 2 days -> manager review
    if leave_type == "sick" and days > 2:
        if not is_duplicate_pending(user, leave_type, leave_date):
            st.session_state.pending_review.append({
                "user": user,
                "type": leave_type,
                "days": days,
                "date": leave_date,
                "reason": reason,
                "issue": "Manager Approval Required (Sick >2 Days)"
            })
        return f"⚠️ Your sick leave request for {days} day(s) has been forwarded to manager for approval."

    # Emergency leave > 1 day -> manager review
    if leave_type == "emergency" and days > 1:
        if not is_duplicate_pending(user, leave_type, leave_date):
            st.session_state.pending_review.append({
                "user": user,
                "type": leave_type,
                "days": days,
                "date": leave_date,
                "reason": reason,
                "issue": "Manager Approval Required (Emergency >1 Day)"
            })
        return f"⚠️ Your emergency leave request for {days} day(s) has been forwarded to manager for approval."

    # All other cases (annual leave, sick <=2 days, emergency ==1 day) continue to normal checks

    # Reliability check
    if score < 30:
        return f"❌ Reliability Score: {score}\nToo many frequent leave requests. Please speak with HR."

    # Balance check
    if days > balance:
        return f"❌ Rejected - No {leave_type} balance.\nAlternatives: Unpaid leave, half-day, work from home."

    # Monthly limit exceeded (existing rule, also sends to manager)
    if used + days > limits[leave_type]:
        if not is_duplicate_pending(user, leave_type, leave_date):
            st.session_state.pending_review.append({
                "user": user,
                "type": leave_type,
                "days": days,
                "date": leave_date,
                "reason": reason,
                "issue": "Monthly Limit Exceeded"
            })
            st.session_state.monthly_stats[user]["allowance"] = False
        return f"⚠️ Monthly {leave_type} limit exceeded. Request sent to manager review."

    # Manpower issue
    if not manpower_ok(dept, leave_date):
        if not is_duplicate_pending(user, leave_type, leave_date):
            st.session_state.pending_review.append({
                "user": user,
                "type": leave_type,
                "days": days,
                "date": leave_date,
                "reason": reason,
                "issue": "Low Manpower"
            })
        return "⚠️ Too many staff already on leave that date. Sent to manager review."

    # AUTO APPROVE (for annual leave, sick <=2 days, emergency ==1 day, and all rules passed)
    st.session_state.leave_balances[user][leave_type] -= days
    st.session_state.monthly_stats[user][leave_type] += days
    if leave_date not in st.session_state.approved_leaves:
        st.session_state.approved_leaves[leave_date] = {}
    if dept not in st.session_state.approved_leaves[leave_date]:
        st.session_state.approved_leaves[leave_date][dept] = []
    st.session_state.approved_leaves[leave_date][dept].append(user)
    st.session_state.history[user]["days"] += days
    st.session_state.history[user]["requests"] += 1
    st.session_state.history[user]["reasons"].append(reason.lower())
    remain = st.session_state.leave_balances[user][leave_type]
    proof_msg = f"📎 Proof: {st.session_state.leave_documents.get(user, {}).get('name', 'None')}" if user in st.session_state.leave_documents else "📎 No proof uploaded"
    return f"""
✅ Approved Successfully
- Type: {leave_type.title()}
- Days: {days}
- Date: {leave_date}
- Remaining: {remain}
- Reliability: {score}
- {proof_msg}
"""

# ==========================================================
# LOGIN PAGE
# ==========================================================
if not st.session_state.logged_in:
    st.markdown("<div class='big-title'>🤖 Aurora AI HR Assistant</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#6b7280;font-size:20px;margin-bottom:30px;'>Smart Leave Management System</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if username in st.session_state.users and st.session_state.users[username]["pw"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = st.session_state.users[username]["role"]

                # Per‑user conversation history
                if username not in st.session_state.chat_history:
                    st.session_state.chat_history[username] = [
                        {
                            "role": "assistant",
                            "content": f"👋 Welcome back {username.title()}! How can I help today?"
                        }
                    ]
                st.session_state.messages = st.session_state.chat_history[username]
                st.rerun()
            else:
                st.error("Invalid Login")
else:
    user = st.session_state.username
    role = st.session_state.role

    # SIDEBAR
    with st.sidebar:
        st.markdown("## 🤖 Aurora AI")
        st.caption("HR Leave Assistant")
        st.markdown("---")
        st.markdown(f"### 👤 {user.title()}")
        if role != "manager":
            st.write("🏢", st.session_state.users[user]["dept"])
        if st.button("🚪 Logout"):
            keys = ["logged_in", "messages", "leave_state", "username", "role"]
            for k in keys:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        if role != "manager":
            st.markdown("---")
            st.markdown("## 📊 Dashboard")
            st.metric("🌴 Annual", st.session_state.leave_balances[user]["annual"])
            st.metric("🩺 Sick", st.session_state.leave_balances[user]["sick"])
            st.metric("⚡ Emergency", st.session_state.leave_balances[user]["emergency"])
            used = sum(st.session_state.monthly_stats[user][t] for t in ["annual","sick","emergency"])
            st.metric("📅 Used This Month", used)
            pending = len([x for x in st.session_state.pending_review if x["user"] == user])
            st.metric("⏳ Pending", pending)
            st.metric("⭐ Trust Score", reliability_score(user))
            if st.session_state.monthly_stats[user]["allowance"]:
                st.success("🎁 Allowance Active")
            else:
                st.error("❌ Allowance Revoked")

            # Leave history in sidebar
            st.markdown("---")
            st.markdown("### 📜 Leave History")
            for r in st.session_state.history[user]["reasons"][-5:]:
                st.write("•", r)

    # MAIN BODY
    st.title("🤖 Aurora AI HR Assistant")
    st.caption("Intelligent, conversational leave chatbot with document upload")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ==========================================================
    # EMPLOYEE CHAT (hidden uploader, notifications, history)
    # ==========================================================
    if role != "manager":

        # Show manager notification if any
        if user in st.session_state.notifications:
            st.success(st.session_state.notifications[user])
            del st.session_state.notifications[user]

        # Session flags for uploader control
        if "show_uploader" not in st.session_state:
            st.session_state.show_uploader = False
        if "awaiting_upload" not in st.session_state:
            st.session_state.awaiting_upload = False

        # Show file uploader only when flagged
        if st.session_state.show_uploader:
            uploaded_file = st.file_uploader(
                "📎 Upload Proof Document",
                type=["pdf", "png", "jpg", "jpeg"],
                key="doc_uploader"
            )
            if uploaded_file is not None:
                st.session_state.leave_documents[user] = {
                    "name": uploaded_file.name,
                    "data": uploaded_file.getvalue()
                }
                st.success("Supporting document uploaded successfully.")
                st.session_state.show_uploader = False
                st.session_state.awaiting_upload = False

                # Continue conversation after upload
                state = st.session_state.leave_state
                if "days" not in state:
                    reply = "How many days do you need?"
                elif "date" not in state:
                    reply = "Which date would you like the leave to start?"
                elif "reason" not in state:
                    reply = "May I know the reason for your leave?"
                else:
                    reply = process_leave(
                        user,
                        state["type"],
                        state["days"],
                        state["date"],
                        state["reason"]
                    )
                    st.session_state.leave_state = {}

                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.session_state.chat_history[user] = st.session_state.messages
                st.rerun()

        # Chat input
        if prompt := st.chat_input("Type your leave request..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.chat_history[user] = st.session_state.messages
            with st.chat_message("user"):
                st.markdown(prompt)

            state = st.session_state.leave_state
            with st.spinner("Aurora is thinking..."):
                ai = call_glm_extract(prompt)

            # AI extraction (or fallback)
            if ai:
                if ai.get("leave_type"):
                    state["type"] = ai["leave_type"]
                if ai.get("days") is not None:
                    state["days"] = ai["days"]
                if ai.get("date"):
                    state["date"] = ai["date"]
                if ai.get("reason"):
                    state["reason"] = ai["reason"]
            else:
                leave_type = detect_leave_type(prompt)
                days = parse_days(prompt)
                dt = parse_date(prompt)
                if leave_type:
                    state["type"] = leave_type
                if days:
                    state["days"] = days
                if dt:
                    state["date"] = dt
                if "reason" not in state and "type" in state and "days" in state and "date" in state:
                    state["reason"] = prompt

            st.session_state.leave_state = state

            # Flow control
            if "type" not in state:
                reply = "I couldn't determine the leave type. Is this Annual, Sick or Emergency leave?"

            # Emergency leave flow
            elif state["type"] == "emergency":
                has_proof = user in st.session_state.leave_documents
                if not has_proof:
                    reply = """⚠️ Emergency leave requires supporting proof.

Please upload a document before we continue."""
                    st.session_state.show_uploader = True
                    st.session_state.awaiting_upload = True
                elif "days" not in state:
                    reply = "How many days do you need?"
                elif "date" not in state:
                    reply = "Which date would you like the leave to start?"
                elif "reason" not in state:
                    reply = "May I know the reason for your leave?"
                else:
                    reply = process_leave(user, state["type"], state["days"], state["date"], state["reason"])
                    st.session_state.leave_state = {}

            # Sick leave flow
            elif state["type"] == "sick":
                if "days" not in state:
                    reply = "How many days do you need?"
                else:
                    has_proof = user in st.session_state.leave_documents
                    if state["days"] >= 2 and not has_proof:
                        reply = """⚠️ Sick leave for 2 or more days requires a Medical Certificate.

Please upload proof before we continue."""
                        st.session_state.show_uploader = True
                        st.session_state.awaiting_upload = True
                    elif "date" not in state:
                        reply = "Which date would you like the leave to start?"
                    elif "reason" not in state:
                        reply = "May I know the reason for your leave?"
                    else:
                        reply = process_leave(user, state["type"], state["days"], state["date"], state["reason"])
                        st.session_state.leave_state = {}

            # Annual leave flow (no upload)
            else:
                if "days" not in state:
                    reply = "How many days do you need?"
                elif "date" not in state:
                    reply = "Which date would you like the leave to start?"
                elif "reason" not in state:
                    reply = "May I know the reason for your leave?"
                else:
                    reply = process_leave(user, state["type"], state["days"], state["date"], state["reason"])
                    st.session_state.leave_state = {}

            with st.chat_message("assistant"):
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.chat_history[user] = st.session_state.messages
            st.rerun()

    # ==========================================================
    # MANAGER DASHBOARD (with notifications and chat history update)
    # ==========================================================
    if role == "manager":
        st.markdown("---")
        st.header("👑 Manager Dashboard")
        if not st.session_state.pending_review:
            st.success("No pending requests.")
        else:
            for i, req in enumerate(st.session_state.pending_review):
                with st.expander(f"{req['user']} - {req['issue']} - {req['date']}"):
                    st.write("**Employee:**", req["user"])
                    st.write("**Leave Type:**", req["type"].title())
                    st.write("**Days:**", req["days"])
                    st.write("**Date:**", req["date"])
                    st.write("**Reason:**", req["reason"])
                    st.write("**Reliability Score:**", reliability_score(req["user"]))
                    proof = st.session_state.leave_documents.get(req["user"])
                    if proof:
                        st.write("**Proof:**", proof["name"])
                        st.download_button("📎 Download Proof", data=proof["data"], file_name=proof["name"], key=f"d_{i}")
                    else:
                        st.write("**Proof:** No document uploaded")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Approve", key=f"a{i}"):
                        target = req["user"]
                        lt = req["type"]
                        days = req["days"]
                        ld = req["date"]
                        reason = req["reason"]
                        dept = st.session_state.users[target]["dept"]
                        if st.session_state.leave_balances[target][lt] < days:
                            st.error(f"Insufficient balance for {target}.")
                        else:
                            st.session_state.leave_balances[target][lt] -= days
                            st.session_state.monthly_stats[target][lt] += days
                            if ld not in st.session_state.approved_leaves:
                                st.session_state.approved_leaves[ld] = {}
                            if dept not in st.session_state.approved_leaves[ld]:
                                st.session_state.approved_leaves[ld][dept] = []
                            st.session_state.approved_leaves[ld][dept].append(target)
                            st.session_state.history[target]["days"] += days
                            st.session_state.history[target]["requests"] += 1
                            st.session_state.history[target]["reasons"].append(reason.lower())

                            # Notification to employee
                            st.session_state.notifications[target] = (
                                f"✅ Your {lt.title()} leave for {days} day(s) on {ld} "
                                f"has been APPROVED by manager."
                            )
                            # Add to employee chat history
                            if target not in st.session_state.chat_history:
                                st.session_state.chat_history[target] = []
                            st.session_state.chat_history[target].append({
                                "role": "assistant",
                                "content": f"✅ Manager approved your {lt.title()} leave request."
                            })
                            # Remove proof
                            if target in st.session_state.leave_documents:
                                del st.session_state.leave_documents[target]
                            st.session_state.pending_review.pop(i)
                            st.success(f"Approved {target}'s {lt} leave.")
                            st.rerun()
                    if col2.button("❌ Reject", key=f"r{i}"):
                        target = req["user"]
                        # Notification to employee
                        st.session_state.notifications[target] = (
                            f"❌ Your {req['type'].title()} leave on {req['date']} "
                            f"was REJECTED by manager."
                        )
                        # Add to employee chat history
                        if target not in st.session_state.chat_history:
                            st.session_state.chat_history[target] = []
                        st.session_state.chat_history[target].append({
                            "role": "assistant",
                            "content": f"❌ Manager rejected your {req['type'].title()} leave request."
                        })
                        if target in st.session_state.leave_documents:
                            del st.session_state.leave_documents[target]
                        st.session_state.pending_review.pop(i)
                        st.error("Rejected.")
                        st.rerun()
                    
