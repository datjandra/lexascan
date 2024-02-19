import streamlit as st
import feedparser
import requests
import os
import json
from functools import lru_cache

from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2

from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from trulens_eval import TruChain, Feedback, OpenAI, Huggingface, Tru

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

hugs = Huggingface()
openai = OpenAI()
tru = Tru()

# Function to fetch RSS feed items
@lru_cache(maxsize=128)
def fetch_feed(url):
    feed = feedparser.parse(url)
    return feed.entries

# Function to extract info
@lru_cache(maxsize=128)
def extract_info(text):
    prompt = f"""
    Here is some text and an optional image link.
    Extract named entities such as people, places, companies, and organizations from the image and text into a structured JSON format.
    Extract any dates and times from the text.
    Extract any objects from the image.

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

# Function to extract text info only using TruLens
@lru_cache(maxsize=128)
def extract_text_info(text):
    try:
       template = f"""
        Here is some text.
        Extract named entities such as people, places, companies, and organizations from the text into a structured JSON format.
        Extract any dates and times from the text.

        {text}
        """

        prompt = PromptTemplate(input_variables=["text"], template=template)
        llm = ChatOpenAI(model_name="gpt-3.5-turbo")
        chain = LLMChain(llm=llm, prompt=prompt, memory=memory, verbose=True)

        f_relevance = Feedback(openai.relevance).on_input_output()

        # TruLens Eval chain recorder
        chain_recorder = TruChain(
            chain, app_id="contextual-chatbot", feedbacks=[f_relevance]
        )
    except:
        # ignore all errors
        pass
    
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
                if image_url:
                    formatted_string += f"Image URL: {image_url}\n"
                formatted_string += f"Description: {selected_item.summary}"

                # Write formatted string to text area
                item_details = st.text_area("Details", value=formatted_string, height=200)

                if st.button("Extract"):
                    if item_details:
                        extracted_info = extract_info(item_details)
                        st.write("Extracted Info:")
                        st.json(extracted_info)

                        extract_text_info(item_details)
                        
            except Exception as e:
                st.error(f"Error fetching RSS feed: {e}")

if __name__ == "__main__":
    main()
