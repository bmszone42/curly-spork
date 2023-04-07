# Import required libraries
import streamlit as st
import redis

# Connect to Redis database
r = redis.Redis(host='localhost', port=6379, db=0)

# Function to store data in Redis
def store_data_in_redis(key, value):
    r.set(key, value)

# Streamlit app
def main():
    st.title("Store Data in Redis using Streamlit")

    # Input fields with sliders
    st.subheader("Enter your data using sliders")
    key = st.slider("Select a key", 0, 100, 0)
    value = st.slider("Select a value", 0, 100, 0)

    # Button to store data
    if st.button("Store data"):
        store_data_in_redis(key, value)
        st.success(f"Data stored successfully: Key: {key}, Value: {value}")

    # Display stored data
    st.subheader("Stored data")
    for key in r.keys():
        st.write(f"Key: {key.decode('utf-8')}, Value: {r.get(key).decode('utf-8')}")

# Run the Streamlit app
if __name__ == "__main__":
    main()
