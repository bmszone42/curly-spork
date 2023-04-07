# Import required libraries
import streamlit as st
import redis
import json
import time

# Connect to Redis database
#r = redis.Redis(host='localhost', port=6379, db=0)
# r = redis.Redis(
#   host='redis-10975.c238.us-central1-2.gce.cloud.redislabs.com',
#   port=10975,
#   password= st.secrets["REDIS_PASSWORD"],
#   db = 0)

# Get Redis configuration from st.secrets
redis_host = st.secrets["redis"]["host"]
redis_port = st.secrets["redis"]["port"]
redis_password = st.secrets["redis"]["password"]

# Connect to Redis database
r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, db=0)

# Function to store data in Redis
def store_data_in_redis(key, value):
    timestamp = time.time()
    data = {
        "value": value,
        "created": timestamp,
    }
    r.set(key, json.dumps(data))

def get_sorted_data():
    data = {}
    for key in r.keys():
        json_data = r.get(key).decode("utf-8")
        data[int(key.decode("utf-8"))] = json.loads(json_data)
    return dict(sorted(data.items(), key=lambda item: item[1]["created"]))

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
    sorted_data = get_sorted_data()
    for key, data in sorted_data.items():
        st.write(f"Key: {key}, Value: {data['value']}, Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created']))}")

# Run the Streamlit app
if __name__ == "__main__":
    main()
