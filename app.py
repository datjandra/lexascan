import streamlit as st
import feedparser
import requests
import os
import json
from functools import lru_cache

from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

USER_ID = 'openai'
APP_ID = 'chat-completion'
# Change these to whatever model and text URL you want to use
MODEL_ID = 'gpt-4-vision-alternative'
MODEL_VERSION_ID = '12b67ac2b5894fb9af9c06ebf8dc02fb'
PAT = os.environ.get('PAT')

channel = ClarifaiChannel.get_grpc_channel()
stub = service_pb2_grpc.V2Stub(channel)
metadata = (('authorization', 'Key ' + PAT),)
userDataObject = resources_pb2.UserAppIDSet(user_id=USER_ID, app_id=APP_ID)

# Function to fetch RSS feed items
@lru_cache(maxsize=128)
def fetch_feed(url):
    feed = feedparser.parse(url)
    return feed.entries

# Function to extract info
@lru_cache(maxsize=128)
def extract_info(text):
    prompt = f"""
    Here is a news text and image link.
    Extract named entities such as people, places, companies, and organizations into a structured JSON format.
    Extract any dates and times.
    Extract objects in the image that correlate with the text.

    {text}
    """
    
    post_model_outputs_response = stub.PostModelOutputs(
        service_pb2.PostModelOutputsRequest(
            user_app_id=userDataObject,  # The userDataObject is created in the overview and is required when using a PAT
            model_id=MODEL_ID,
            version_id=MODEL_VERSION_ID,  # This is optional. Defaults to the latest model version
            inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(
                        text=resources_pb2.Text(
                            raw=prompt
                            # url=TEXT_FILE_URL
                            # raw=file_bytes
                        )
                    )
                )
            ]
        ),
        metadata=metadata
    )
    
    if post_model_outputs_response.status.code != status_code_pb2.SUCCESS:
        print(post_model_outputs_response.status)

    # Since we have one input, one output will exist here
    output = post_model_outputs_response.outputs[0]

    print("Completion:\n")
    return json.loads(output.data.text.raw)

# Main function to run the Streamlit app
def main():
    st.title("LexaScan")

    # Input field for entering RSS URL
    rss_url = st.text_input("Enter RSS URL:", "https://feeds.bbci.co.uk/news/world/rss.xml")

    # Button to fetch RSS items
    if "clicked" not in st.session_state:
        st.session_state.clicked = False
    if st.button("Fetch RSS Items") or st.session_state["clicked"]:
        st.session_state["clicked"] = True
        if rss_url:
            try:
                items = fetch_feed(rss_url)

                # Display selected item content
                selected_item_index = st.selectbox("Select an item", range(len(items)), key="selectbox_key")
                selected_item = items[selected_item_index]

                # Extracting image URL from media:thumbnail tag
                image_url = None
                for key in selected_item.keys():
                    print(key)
                    if 'media' in key:
                        image_url = selected_item[key][0]['url']
                        break

                if image_url:
                    st.image(image_url, use_column_width=True)
                
                # Create formatted string with title, image URL, and description
                formatted_string = f"Title: {selected_item.title}\n"
                if image_url:
                    formatted_string += f"Image URL: {image_url}\n"
                formatted_string += f"Description: {selected_item.summary}"

                # Write formatted string to text area
                item_details = st.text_area("Item Details", value=formatted_string, height=200)

                if "clicked" not in st.session_state:
                    st.session_state.clicked = False
                if st.button("Extract") or st.session_state["clicked"]:
                    st.session_state["clicked"] = True
                    if item_details:
                        extracted_info = extract_info(item_details)
                        st.write("Extracted Info:")
                        st.json(extracted_info)

            except Exception as e:
                st.error(f"Error fetching RSS feed: {e}")

if __name__ == "__main__":
    main()
