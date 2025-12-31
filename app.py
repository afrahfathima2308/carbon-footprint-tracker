import streamlit as st
import pandas as pd
import json
import requests
import plotly.express as px
import datetime

# --- Gemini API Configuration ---
# The API key will be automatically provided by the Canvas environment at runtime.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
API_KEY = " " # Leave this empty. Canvas will inject the key.

# --- Function to call Gemini API ---
def get_gemini_response(prompt):
    """
    Calls the Gemini API with a given prompt and returns the generated text.
    """
    headers = {'Content-Type': 'application/json'}
    chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
    payload = {"contents": chat_history}

    try:
        response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        result = response.json()

        if result.get("candidates") and len(result["candidates"]) > 0 and \
           result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts") and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            return result["candidates"][0]["content"]["parts"][0].get("text", "No text content found.")
        else:
            return "No valid response or content from Gemini API."
    except requests.exceptions.RequestException as e:
        st.error(f"🚫 API Error: {e}. Please check your internet connection or try again later.")
        return f"Error calling Gemini API: {e}"
    except json.JSONDecodeError:
        st.error("🚫 API Error: Could not decode response from Gemini. The API might have returned an unexpected format.")
        return "Error decoding JSON response from Gemini API."
    except Exception as e:
        st.error(f"🚫 An unexpected error occurred during API call: {e}")
        return f"An unexpected error occurred: {e}"

# --- Carbon Emission Factors (Simplified, illustrative values) ---
# Values are in kg CO2e per unit
EMISSION_FACTORS = {
    "transportation": {
        "gasoline_car_km": 0.21,  # kg CO2e per km for average gasoline car
        "electric_car_km": 0.05,  # kg CO2e per km for average electric car (considering grid emissions)
        "public_transport_km": 0.04, # kg CO2e per km for bus/train
        "flight_km": 0.15, # kg CO2e per km for air travel
    },
    "electricity": {
        "kwh": 0.23,  # kg CO2e per kWh (average grid mix)
    },
    "diet": {
        "high_meat": 2.5,  # kg CO2e per day
        "medium_meat": 1.5, # kg CO2e per day
        "low_meat": 0.8,    # kg CO2e per day
        "vegetarian": 0.5,  # kg CO2e per day
        "vegan": 0.3,       # kg CO2e per day
    },
    "waste": {
        "kg_waste": 0.2, # kg CO2e per kg of waste (landfill emissions)
    }
}

# --- Initialize Session State for Progress Tracking ---
if 'footprint_history' not in st.session_state:
    st.session_state.footprint_history = []
if 'current_footprint' not in st.session_state:
    st.session_state.current_footprint = None

# --- Carbon Footprint Calculation Function ---
def calculate_footprint(transport_km, transport_type, electricity_kwh, diet_choice, waste_kg):
    """Calculates the carbon footprint based on user inputs."""
    total_co2e = 0
    breakdown = {}

    # Transportation
    transport_co2e = 0
    if transport_type == "Gasoline Car":
        transport_co2e = transport_km * EMISSION_FACTORS["transportation"]["gasoline_car_km"]
    elif transport_type == "Electric Car":
        transport_co2e = transport_km * EMISSION_FACTORS["transportation"]["electric_car_km"]
    elif transport_type == "Public Transport":
        transport_co2e = transport_km * EMISSION_FACTORS["transportation"]["public_transport_km"]
    elif transport_type == "Flight":
        transport_co2e = transport_km * EMISSION_FACTORS["transportation"]["flight_km"]
    total_co2e += transport_co2e
    breakdown["Transportation"] = transport_co2e

    # Electricity
    electricity_co2e = electricity_kwh * EMISSION_FACTORS["electricity"]["kwh"]
    total_co2e += electricity_co2e
    breakdown["Electricity"] = electricity_co2e

    # Diet
    diet_co2e = 0
    if diet_choice == "High Meat (Daily)":
        diet_co2e = EMISSION_FACTORS["diet"]["high_meat"] * 30 # Per month
    elif diet_choice == "Medium Meat (Few times/week)":
        diet_co2e = EMISSION_FACTORS["diet"]["medium_meat"] * 30
    elif diet_choice == "Low Meat (Once/week)":
        diet_co2e = EMISSION_FACTORS["diet"]["low_meat"] * 30
    elif diet_choice == "Vegetarian":
        diet_co2e = EMISSION_FACTORS["diet"]["vegetarian"] * 30
    elif diet_choice == "Vegan":
        diet_co2e = EMISSION_FACTORS["diet"]["vegan"] * 30
    total_co2e += diet_co2e
    breakdown["Diet"] = diet_co2e

    # Waste
    waste_co2e = waste_kg * EMISSION_FACTORS["waste"]["kg_waste"]
    total_co2e += waste_co2e
    breakdown["Waste"] = waste_co2e

    return total_co2e, breakdown

# --- Streamlit UI ---
st.set_page_config(layout="wide", page_title="Personal Carbon Footprint Tracker") # Removed 'icon' argument

st.title("🌱 Your Personal Carbon Footprint Tracker")
st.markdown("""
Welcome! This interactive tool helps you understand your environmental impact and provides personalized tips to reduce it.
Let's embark on a journey towards a more sustainable lifestyle!
""")

# --- Sidebar for Inputs ---
st.sidebar.header("📊 Your Monthly Activity Data")
st.sidebar.markdown("Tell us about your lifestyle to calculate your footprint.")

with st.sidebar.expander("🚗 Transportation"):
    transport_km = st.number_input("Kilometers driven/traveled per month:", min_value=0, value=500, step=10, key="transport_km_sidebar", help="Estimate your total travel distance by car, public transport, or flights.")
    transport_type = st.selectbox("Primary mode of transport:",
                                  ("Gasoline Car", "Electric Car", "Public Transport", "Flight"),
                                  key="transport_type_sidebar", help="Choose the mode that represents the majority of your travel.")

with st.sidebar.expander("💡 Electricity Usage"):
    electricity_kwh = st.number_input("Electricity consumed per month (kWh):", min_value=0, value=300, step=10, key="electricity_kwh_sidebar", help="Check your electricity bill for this value.")

with st.sidebar.expander("🍎 Diet Choices"):
    diet_choice = st.selectbox("Your typical diet:",
                               ("High Meat (Daily)", "Medium Meat (Few times/week)", "Low Meat (Once/week)", "Vegetarian", "Vegan"),
                               key="diet_choice_sidebar", help="Your dietary choices have a significant impact on your carbon footprint.")

with st.sidebar.expander("🗑 Waste Generation"):
    waste_kg = st.number_input("Waste generated per month (kg):", min_value=0.0, value=15.0, step=0.5, key="waste_kg_sidebar", help="Estimate the weight of waste you generate (e.g., 1 large trash bag is ~5-10kg).")

st.sidebar.markdown("---")
if st.sidebar.button("Calculate My Carbon Footprint ✨", type="primary"):
    total_footprint, breakdown = calculate_footprint(
        transport_km, transport_type, electricity_kwh, diet_choice, waste_kg
    )
    
    st.session_state.current_footprint = {
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "total": total_footprint,
        "breakdown": breakdown
    }
    st.session_state.footprint_history.append(st.session_state.current_footprint)
    st.sidebar.success("Footprint calculated!")

# --- Main Content Area ---
if st.session_state.current_footprint:
    st.header("Results: Your Monthly Carbon Footprint 📊")
    st.info("Here's your estimated environmental impact for the month. Remember, every step counts!")

    current_total_footprint = st.session_state.current_footprint["total"]
    current_breakdown = st.session_state.current_footprint["breakdown"]

    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric(label="Total Monthly CO2e", value=f"{current_total_footprint:.2f} kg", delta="Estimated Impact")
    with col_metric2:
        # Simple comparison to a "good" target, adjust as needed
        target_footprint = 500 # kg CO2e per month as an example target
        delta_value = f"{(current_total_footprint - target_footprint):.2f} kg vs. target"
        delta_color = "inverse" if current_total_footprint > target_footprint else "normal"
        st.metric(label="Compared to Target (500 kg CO2e)", value=f"{current_total_footprint:.2f} kg", delta=delta_value, delta_color=delta_color)

    st.subheader("Footprint Breakdown by Category 📈")
    breakdown_df = pd.DataFrame(current_breakdown.items(), columns=['Category', 'CO2e (kg)'])
    fig = px.pie(breakdown_df, values='CO2e (kg)', names='Category',
                 title='How Your Activities Contribute to Emissions',
                 hole=0.4,
                 color_discrete_sequence=px.colors.qualitative.Pastel) # Donut chart
    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
    st.plotly_chart(fig, use_container_width=True)

    # --- Personalized Reduction Tips (Gemini API) ---
    st.header("3. Personalized Reduction Tips ✨")
    st.markdown("Based on your footprint breakdown, our AI Guardian has crafted some tailored suggestions to help you reduce your impact. Small changes can make a big difference!")

    # Identify top contributing categories
    sorted_breakdown = sorted(current_breakdown.items(), key=lambda item: item[1], reverse=True)
    top_categories = ", ".join([cat for cat, co2 in sorted_breakdown if co2 > 0])

    if top_categories:
        gemini_prompt = f"The user's monthly carbon footprint is {current_total_footprint:.2f} kg CO2e. The main contributing categories are: {top_categories}. Please provide 3-5 actionable and practical tips for reducing carbon emissions in these specific areas, suitable for an individual. Focus on easy-to-implement changes and provide a brief explanation for each tip. Format as a bulleted list."
        
        with st.spinner("Our AI is thinking of the best tips for you... 🧠"):
            ai_tips = get_gemini_response(gemini_prompt)
            st.markdown(ai_tips)
    else:
        st.info("No specific categories identified for tips as your footprint is very low or zero. Keep up the great work!")

# --- Progress Tracking ---
st.header("4. Your Footprint History & Progress 🕰")
st.markdown("See how your efforts are paying off! Each time you calculate your footprint, it's saved here.")

if st.session_state.footprint_history:
    history_df = pd.DataFrame(st.session_state.footprint_history)
    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.sort_values(by='date')

    st.dataframe(history_df[['date', 'total']].rename(columns={'total': 'Monthly CO2e (kg)'}), use_container_width=True)

    if len(history_df) > 1:
        fig_history = px.line(history_df, x='date', y='total',
                              title='Your Carbon Footprint Journey Over Time',
                              labels={'total': 'Monthly CO2e (kg)', 'date': 'Date'},
                              markers=True)
        fig_history.update_xaxes(dtick="M1", tickformat="%b\n%Y") # Monthly ticks
        st.plotly_chart(fig_history, use_container_width=True)
    else:
        st.info("Calculate your footprint a few more times to unlock your personalized progress graph! Keep going! 💪")
else:
    st.info("Calculate your first carbon footprint using the sidebar to start tracking your history!")

st.markdown("---")
with st.expander("💡 About Carbon Footprints & This Tracker"):
    st.markdown("""
    A carbon footprint is the total amount of greenhouse gases (GHG) that are generated by our actions.
    This tracker provides an *estimation* based on simplified emission factors. Real-world calculations can be much more complex,
    involving detailed data on specific energy sources, vehicle models, agricultural practices, and waste management systems.
    
    *Why track your footprint?*
    * *Awareness:* Understand which activities contribute most to your emissions.
    * *Actionable Insights:* Identify areas where you can make the biggest difference.
    * *Motivation:* See your progress and stay motivated on your sustainability journey.
    
    Remember, every small step towards reducing your footprint contributes to a healthier planet!
    """)

# Reset button
if st.button("Start Fresh / Reset Data"):
    st.session_state.footprint_history = []
    st.session_state.current_footprint = None
    st.experimental_rerun()
    st.success("Data reset! You can now start a new tracking journey.")