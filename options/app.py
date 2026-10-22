"""Option payoff and profit at expiration. Run with:  streamlit run options/app.py"""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from payoff import SHARES_PER_CONTRACT, break_even, payoff, profit

st.set_page_config(page_title="Option payoffs", page_icon="📈")
st.title("Option payoff and profit at expiration")
st.caption("MSF 8615 class exercise: an AI agent wrote this app, and its tests pass. "
           "Check it against your own numbers before you trust it.")

c1, c2 = st.columns(2)
option = c1.selectbox("Option", ["call", "put"])
position = c2.radio("Position", ["long", "short"], horizontal=True)
K = st.slider("Strike price K ($)", 350, 460, 405, 5)
premium = st.number_input("Option price, $ per share", min_value=0.0, value=17.65 if option == "call" else 20.0, step=0.05)
contracts = st.number_input("Number of contracts (100 shares each)", min_value=1, value=1, step=1)

S = np.arange(350, 461, 1.0)
sign = 1 if position == "long" else -1
df = pd.DataFrame({"Stock price at expiration": S,
                   "Payoff": sign * payoff(option, S, K),
                   "Profit": profit(option, position, S, K, premium)})
long = df.melt("Stock price at expiration", var_name="line", value_name="$ per share")
chart = alt.Chart(long).mark_line(strokeWidth=2.5).encode(
    x="Stock price at expiration:Q", y="$ per share:Q",
    color=alt.Color("line:N", scale=alt.Scale(domain=["Payoff", "Profit"], range=["#0f8f7a", "#c99700"])),
    strokeDash=alt.condition(alt.datum.line == "Payoff", alt.value([6, 4]), alt.value([1, 0])))
zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#6b7580").encode(y="y:Q")
st.altair_chart((chart + zero).properties(height=360), width="stretch")

be = break_even(option, K, premium)
per_contract = SHARES_PER_CONTRACT * contracts
usd = lambda x, d=0: f"\\${x:,.{d}f}"  # escaped: in st.markdown, text between two $ signs is LaTeX math
if position == "long":
    loss = f"{usd(premium * per_contract)} (the premium)"
    gain = "unlimited" if option == "call" else f"{usd((K - premium) * per_contract)} (if the stock falls to 0)"
else:
    gain = f"{usd(premium * per_contract)} (the premium)"
    loss = "unlimited" if option == "call" else f"{usd((K - premium) * per_contract)} (if the stock falls to 0)"
st.markdown(f"**Break-even:** {usd(be, 2)} at expiration. **Maximum gain:** {gain}. **Maximum loss:** {loss}. "
            f"Amounts for {contracts} contract{'s' if contracts > 1 else ''} of {SHARES_PER_CONTRACT} shares.")
st.caption("European option, at expiration only. Profit = payoff − premium for a long position; the short side is the mirror image.")
