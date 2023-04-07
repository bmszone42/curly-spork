# Import required libraries
import streamlit as st
import redis
import json
import time
import pandas as pd
from io import BytesIO


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
        "value": key * value,
        "created": timestamp,
    }
    r.set(key, json.dumps(data))

def get_sorted_data():
    data = {}
    for key in r.keys():
        try:
            json_data = r.get(key).decode("utf-8")
            deserialized_data = json.loads(json_data)
            if "created" in deserialized_data:
                data[int(key.decode("utf-8"))] = deserialized_data
        except json.JSONDecodeError:
            pass
    return dict(sorted(data.items(), key=lambda item: item[1]["created"]))

def delete_all_keys():
    for key in r.keys():
        r.delete(key)

def save_data_to_excel(sorted_data):
    data_list = []

    for key, data in sorted_data.items():
        data_list.append({
            "Key": key,
            "Value": data["value"],
            "Created": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data["created"]))
        })

    df = pd.DataFrame(data_list)

    with BytesIO() as bIO:
        writer = pd.ExcelWriter(bIO, engine='openpyxl')
        df.to_excel(writer, index=False)
        writer.save()
        bIO.seek(0)
        return bIO.read()

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
        
    # Reset and delete all data with confirmation
    with st.expander("Reset and delete all data"):
        st.warning("This will delete all of your data. Are you sure?")
        if st.button("Yes, delete all data"):
            delete_all_keys()
            st.success("All data has been deleted.")

    # Display stored data
    st.subheader("Stored data")
    sorted_data = get_sorted_data()
    for key, data in sorted_data.items():
        st.write(f"Key: {key}, Value: {data['value']}, Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created']))}")
        
     # Button to save data to an Excel file
    excel_data = save_data_to_excel(sorted_data)
    st.download_button(
        label="Save data to Excel",
        data=excel_data,
        file_name="output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        
        
# Run the Streamlit app
if __name__ == "__main__":
    main()
