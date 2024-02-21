import streamlit as st
import feedparser
import requests
import os
import json
from functools import lru_cache

from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

from trulens_eval import Feedback, Tru, TruBasicApp
from trulens_eval.feedback.provider import OpenAI

USER_ID = 'openai'
APP_ID = 'chat-completion'
# Change these to whatever model and text URL you want to use
MODEL_ID = 'gpt-4-vision-alternative'
MODEL_VERSION_ID = os.environ.get('MODEL_VERSION_ID')
PAT = os.environ.get('PAT')

channel = ClarifaiChannel.get_grpc_channel()
stub = service_pb2_grpc.V2Stub(channel)
metadata = (('authorization', 'Key ' + PAT),)
userDataObject = resources_pb2.UserAppIDSet(user_id=USER_ID, app_id=APP_ID)

# Initialize TruLens
tru = Tru()
tru.reset_database()

# Initialize OpenAI provider
provider = OpenAI()

f_controversiality = Feedback(
    provider.controversiality_with_cot_reasons,
    name="Controversiality",
    higher_is_better=False,
).on_output()

feedbacks = [
    f_controversiality
]    

# Function to fetch RSS feed items
@lru_cache(maxsize=128)
def fetch_feed(url):
    feed = feedparser.parse(url)
    return feed.entries

# Function to extract info
@lru_cache(maxsize=128)
def extract_info_clarifai(text):
    prompt = f"""
    Here is some text with an optional image link. Extract named entities like people, places, companies, and organizations from the image and text into a structured JSON format. Extract any dates and times from the text. Extract objects from the image.

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
    return output.data.text.raw

from openai import OpenAI
client = OpenAI()

def extract_info_openai(text, image_url):
    response = client.chat.completions.create(
      model="gpt-4-vision",
      messages=[
        {
          "role": "user",
          "content": [
            {"type": "text", "text": text},
            {
              "type": "image_url",
              "image_url": {
                "url": image_url,
              },
            },
          ],
        }
      ],
      max_tokens=300,
    )
    return response.choices[0]

# Initialize TruLens recorder
tru_llm_standalone_recorder = TruBasicApp(extract_info_clarifai, app_id="LexaScan", feedbacks=feedbacks)

@lru_cache(maxsize=128)
def extract_info(prompt_input, image_url):
    # prompt_output = extract_info_clarifai(prompt_input)
    prompt_output = extract_info_openai(prompt_input, image_url)
    try:    
        tru_llm_standalone_recorder.app(prompt_input)
    except:
        pass
    return json.loads(prompt_output)

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
                st.sidebar.header("News Items")

                # Extract titles of RSS items
                item_titles = [item.title for item in items]

                 # Display selected item content by title
                selected_item_title = st.sidebar.selectbox("Select an item", item_titles, key="selectbox_key")
                selected_item = next(item for item in items if item.title == selected_item_title)

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
                formatted_string += f"Description: {selected_item.summary}\n"
                if image_url:
                    formatted_string += f"Image:\n{image_url}"
                    
                # Write formatted string to text area
                item_details = st.text_area("Details", value=formatted_string, height=200)

                if st.button("Extract"):
                    if item_details:
                        extracted_info = extract_info(item_details, image_url)
                        st.write("Extracted Info:")
                        st.json(extracted_info)
                        
            except Exception as e:
                st.error(f"Error fetching RSS feed: {e}")

if __name__ == "__main__":
    main()
