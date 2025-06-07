import streamlit as st
import math
from scipy.stats import norm

# --- Custom CSS for Syntx Vibe ---
st.markdown("""
<style>
body {
    background-color: #0b1120 !important;
}
[data-testid="stAppViewContainer"] {
    background-color: #0b1120 !important;
    color: #e0e7ef !important;
}
[data-testid="stHeader"] {background: none;}
[data-testid="stSidebar"] {
    background: #161e2e;
    color: #e0e7ef;
}
h1, h2, h3, h4 {
    color: #0ea5e9 !important;
}
.stButton>button {
    background: #0ea5e9;
    color: white;
    border-radius: 8px;
    font-weight: 500;
}
.stButton>button:hover {
    background: #0369a1;
}
.stDataFrame, .stTable {
    background: #101928;
    color: #e0e7ef;
}
</style>
""", unsafe_allow_html=True)

# --- Dashboard Title ---
st.title("Black-Scholes Pricing Engine")

# Side Paramater inpput panel
st.sidebar.header("Input Paramaters")
S = st.sidebar.number_input("Underlying Price (S)", value=200.0)
K= st.sidebar.number_input("Strike Price (K)", value=200.0)
T = st.sidebar.number_input("Days Till Expiry", value=45) / 256
V = st.sidebar.number_input("Implied Volatility (%)", value=20.0) / 100
R = st.sidebar.number_input("Risk-Free Rate (%)", value=5.0) / 100
calculate = st.sidebar.button("Calculate", key="calculate")
# --- Outputs Panel ---
if calculate:

    d1_den = V * math.sqrt(T)
    d1_num = (math.log(S/K)) + (R + (V**2)/2)*T
    d1 = d1_num / d1_den
    d2 = d1 - d1_den
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)

    call_price = (S * N_d1) - K * math.exp(-R*T)*N_d2
    put_price = (K * math.exp(-R * T) * (1 - N_d2)) - (S * (1 - N_d1))

        # PDF of d1
    pdf_d1 = norm.pdf(d1)

    # Delta
    delta_call = N_d1
    delta_put = N_d1 - 1

    # Gamma
    gamma = pdf_d1 / (S * V * math.sqrt(T))

    # Vega (per 1% change in volatility)
    vega = S * pdf_d1 * math.sqrt(T) / 100

    # Theta
    theta_call = (-S * pdf_d1 * V / (2 * math.sqrt(T)) -
                R * K * math.exp(-R * T) * N_d2) / 365
    theta_put = (-S * pdf_d1 * V / (2 * math.sqrt(T)) +
                R * K * math.exp(-R * T) * (1 - N_d2)) / 365

    # Rho
    rho_call = K * T * math.exp(-R * T) * N_d2 / 100
    rho_put = -K * T * math.exp(-R * T) * (1 - N_d2) / 100


    st.success("Calculation ran! (Insert output here)")
    # For demonstration:
    st.metric(label="Test", value=T, delta=None)
    st.metric(label="Test", value=N_d2, delta=None)
    st.metric(label="Call Price", value=call_price, delta=None)
    st.metric(label="Put Price", value=put_price, delta=None)
    st.metric(label="Delta", value="delta_call: {:.4f}, delta_put: {:.4f}".format(delta_call, delta_put))
    st.metric(label="Gamma", value=gamma)
    st.metric(label="Vega", value=vega)
    st.metric(label="Theta", value=theta_call, )
    st.metric(label="Rho", value=rho_call)

# --- Visualization Placeholder ---
with st.expander("📊 What is Black-Scholes?", expanded=False):
    st.latex("C = S N(d_1) - K e^{-rT} N(d_2)")
    st.latex(r"d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}")
    st.latex(r"d_2 = d_1 - \sigma\sqrt{T}")
    st.info(" The Black-Scholes model is used to calculate the theoretical price of European-style options. It considers the discounted price of the option based on the risk-neutral probability. Where N is the Cummalitive Distribution Function (CDF) of the standard normal distribution.")
    # Use st.pyplot, st.plotly_chart, etc.

# --- Backtesting Panel Placeholder ---
with st.expander("🧪 Backtesting (coming soon)", expanded=False):
    st.info("Set up your strategy and view backtest results here.")

# --- Documentation/Theory Panel (optional) ---
with st.expander("📖 Black-Scholes Formula"):
    st.latex(r"""
        C = S N(d_1) - K e^{-rT} N(d_2)
    """)
    st.markdown("""
    - $S$ = underlying price  
    - $K$ = strike price  
    - $T$ = time to maturity  
    - $r$ = risk-free rate  
    - $\sigma$ = volatility  
    """)

