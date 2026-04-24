import streamlit as st
import re
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ==========================================================
# AURORA AI HR ASSISTANT - ULTIMATE FINAL VERSION
# ==========================================================

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="Aurora AI HR Assistant",
    page_icon="🤖",
    layout="wide"
)

load_dotenv()

# ==========================================================
# CUSTOM CSS
# ==========================================================
st.markdown("""
<style>

/* Main page */
.block-container{
    padding-top:3rem !important;
    padding-bottom:1rem;
}

/* Sidebar */
section[data-testid="stSidebar"]{
    background: linear-gradient(180deg,#081028,#0f172a);
}

section[data-testid="stSidebar"] *{
    color:white !important;
}

/* Sidebar buttons (Logout) */
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
    color:white !important;
}

/* Main buttons */
div.stButton > button{
    border-radius:10px;
    font-weight:700;
}

/* Login input labels */
label{
    color:#111827 !important;
    font-weight:700 !important;
    font-size:18px !important;
}

/* Input boxes */
input{
    background:white !important;
    color:black !important;
    border:2px solid #d1d5db !important;
    border-radius:10px !important;
}

/* Login page button */
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

/* Title */
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

init()

# ==========================================================
# HELPERS
# ==========================================================
def detect_leave_type(text):
    t = text.lower()

    if any(x in t for x in ["fever","flu","doctor","clinic","mc","sick","hospital"]):
        return "sick"

    if any(x in t for x in ["urgent","family","accident","emergency","pipe burst"]):
        return "emergency"

    if any(x in t for x in ["trip","holiday","vacation","annual","break"]):
        return "annual"

    if any(x in t for x in ["stress","burnout","mental health"]):
        return "sick"

    return None


def emotion_message(leave_type):
    if leave_type == "sick":
        return "🩺 I'm sorry you're feeling unwell. I hope you recover soon."
    elif leave_type == "emergency":
        return "⚠️ That sounds urgent. I will help immediately."
    elif leave_type == "annual":
        return "🌴 Sounds like a well-deserved break!"
    return "🙂"


def parse_days(text):
    t = text.lower()

    if "half" in t:
        return 0.5

    m = re.search(r'(\d+)', t)
    if m:
        return int(m.group(1))

    return None


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

        months = {
            "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
            "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12
        }

        return f"{datetime.now().year}-{months[mon]:02d}-{day:02d}"

    return None


def reliability_score(user):
    h = st.session_state.history[user]

    score = 100

    if h["requests"] > 2:
        score -= (h["requests"]-2)*20

    if h["days"] > 15:
        score -= 10

    if len(h["reasons"]) >= 3:
        if h["reasons"][-1] == h["reasons"][-2] == h["reasons"][-3]:
            score -= 10

    if h["requests"] == 0:
        score += 5

    score = max(0,min(score,100))
    return score


def manpower_ok(dept, leave_date):
    dept_total = {
        "Engineering":2,
        "Sales":2
    }

    min_required = 1

    already = len(
        st.session_state.approved_leaves.get(
            leave_date, {}
        ).get(dept, [])
    )

    remain = dept_total.get(dept,2) - already - 1
    return remain >= min_required


# ==========================================================
# PROCESS LEAVE
# ==========================================================
def process_leave(user, leave_type, days, leave_date, reason):
    dept = st.session_state.users[user]["dept"]
    score = reliability_score(user)

    limits = {
        "annual":2,
        "sick":1,
        "emergency":1
    }

    balance = st.session_state.leave_balances[user][leave_type]
    used = st.session_state.monthly_stats[user][leave_type]

    # reliability deny
    if score < 30:
        return f"""
❌ Reliability Score: **{score}**

Too many frequent leave requests recently.

Please speak with HR.
"""

    # if no balance
    if days > balance:
        return f"""
❌ Rejected - No {leave_type} balance.

### Alternatives:
- Unpaid leave
- Half-day leave
- Work from home
"""

    # monthly limit exceeded
    if used + days > limits[leave_type]:
        st.session_state.pending_review.append({
            "user":user,
            "type":leave_type,
            "days":days,
            "date":leave_date,
            "reason":reason,
            "issue":"Monthly Limit Exceeded"
        })

        st.session_state.monthly_stats[user]["allowance"] = False

        return f"""
⚠️ Monthly {leave_type} limit exceeded.

Request sent to manager review.

Attendance allowance revoked.

Reliability Score: **{score}**
"""

    # manpower issue
    if not manpower_ok(dept, leave_date):
        st.session_state.pending_review.append({
            "user":user,
            "type":leave_type,
            "days":days,
            "date":leave_date,
            "reason":reason,
            "issue":"Low Manpower"
        })

        return """
⚠️ Too many staff already on leave that date.

Sent to manager review.

Suggested alternatives:
- Another date
- Half-day leave
"""

    # APPROVE
    st.session_state.leave_balances[user][leave_type] -= days
    st.session_state.monthly_stats[user][leave_type] += days

    if leave_date not in st.session_state.approved_leaves:
        st.session_state.approved_leaves[leave_date] = {}

    if dept not in st.session_state.approved_leaves[leave_date]:
        st.session_state.approved_leaves[leave_date][dept] = []

    st.session_state.approved_leaves[leave_date][dept].append(user)

    # history update
    st.session_state.history[user]["days"] += days
    st.session_state.history[user]["requests"] += 1
    st.session_state.history[user]["reasons"].append(reason.lower())

    remain = st.session_state.leave_balances[user][leave_type]

    return f"""
✅ Approved Successfully

- Type: {leave_type.title()}
- Days: {days}
- Date: {leave_date}
- Remaining Balance: {remain}
- Reliability Score: {score}
"""


# ==========================================================
# LOGIN PAGE
# ==========================================================
if not st.session_state.logged_in:

    st.markdown(
        "<div class='big-title'>🤖 Aurora AI HR Assistant</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;color:#6b7280;font-size:20px;margin-bottom:30px;'>Smart Leave Management System</p>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,2,1])

    with c2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):

            if username in st.session_state.users and \
               st.session_state.users[username]["pw"] == password:

                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = st.session_state.users[username]["role"]

                st.session_state.messages = [{
                    "role":"assistant",
                    "content":f"👋 Welcome back {username.title()}! How can I help today?"
                }]

                st.rerun()

            else:
                st.error("Invalid Login")

# ==========================================================
# MAIN APP
# ==========================================================
else:

    user = st.session_state.username
    role = st.session_state.role

    # ----------------------------
    # SIDEBAR
    # ----------------------------
    with st.sidebar:

        st.markdown("## 🤖 Aurora AI")
        st.caption("HR Leave Assistant")

        st.markdown("---")
        st.markdown(f"### 👤 {user.title()}")

        if role != "manager":
            st.write("🏢", st.session_state.users[user]["dept"])

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

        if role != "manager":

            st.markdown("---")
            st.markdown("## 📊 Dashboard")

            st.metric("🌴 Annual", st.session_state.leave_balances[user]["annual"])
            st.metric("🩺 Sick", st.session_state.leave_balances[user]["sick"])
            st.metric("⚡ Emergency", st.session_state.leave_balances[user]["emergency"])

            used = (
                st.session_state.monthly_stats[user]["annual"] +
                st.session_state.monthly_stats[user]["sick"] +
                st.session_state.monthly_stats[user]["emergency"]
            )

            st.metric("📅 Used This Month", used)

            pending = len([
                x for x in st.session_state.pending_review
                if x["user"] == user
            ])

            st.metric("⏳ Pending", pending)

            st.metric("⭐ Trust Score", reliability_score(user))

            if st.session_state.monthly_stats[user]["allowance"]:
                st.success("🎁 Allowance Active")
            else:
                st.error("❌ Allowance Revoked")

    # ----------------------------
    # MAIN BODY
    # ----------------------------
    st.title("🤖 Aurora AI HR Assistant")
    st.caption("Human-like smart leave chatbot")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # EMPLOYEE CHAT
    if role != "manager":

        if prompt := st.chat_input("Type your leave request..."):

            st.session_state.messages.append({
                "role":"user",
                "content":prompt
            })

            with st.chat_message("user"):
                st.markdown(prompt)

            text = prompt.lower()
            state = st.session_state.leave_state

            # STEP 1
            if not state:

                leave_type = detect_leave_type(text)

                if leave_type:
                    state["type"] = leave_type
                    reply = emotion_message(leave_type) + "\n\nHow many days leave do you need?"
                else:
                    reply = "Please tell me if this is Annual, Sick or Emergency leave."

            # STEP 2
            elif "days" not in state:

                days = parse_days(text)

                if days:
                    state["days"] = days
                    reply = "📅 What date do you need leave? (today / tomorrow / 25 apr)"
                else:
                    reply = "How many days leave do you need?"

            # STEP 3
            elif "date" not in state:

                dt = parse_date(text)

                if dt:
                    state["date"] = dt
                    reply = "📝 Please briefly tell me the reason."
                else:
                    reply = "Please enter valid date."

            # STEP 4
            else:

                state["reason"] = prompt

                reply = process_leave(
                    user,
                    state["type"],
                    state["days"],
                    state["date"],
                    state["reason"]
                )

                st.session_state.leave_state = {}

            with st.chat_message("assistant"):
                st.markdown(reply)

            st.session_state.messages.append({
                "role":"assistant",
                "content":reply
            })

    # ----------------------------
    # MANAGER DASHBOARD
    # ----------------------------
    if role == "manager":

        st.markdown("---")
        st.header("👑 Manager Dashboard")

        if not st.session_state.pending_review:
            st.success("No pending requests.")

        for i, req in enumerate(st.session_state.pending_review):

            with st.expander(f"{req['user']} - {req['issue']}"):

                st.write("Type:", req["type"])
                st.write("Days:", req["days"])
                st.write("Date:", req["date"])
                st.write("Reason:", req["reason"])

                c1,c2 = st.columns(2)

                if c1.button("Approve", key=f"a{i}"):

                    st.session_state.pending_review.pop(i)
                    st.success("Approved")
                    st.rerun()

                if c2.button("Reject", key=f"r{i}"):

                    st.session_state.pending_review.pop(i)
                    st.error("Rejected")
                    st.rerun()