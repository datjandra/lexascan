import streamlit as st
import feedparser
import requests
import os
from bs4 import BeautifulSoup
from functools import lru_cache

USER_ID = 'openai'
APP_ID = 'chat-completion'
# Change these to whatever model and text URL you want to use
MODEL_ID = 'gpt-4-vision-alternative'
MODEL_VERSION_ID = '12b67ac2b5894fb9af9c06ebf8dc02fb'
PAT = os.environ.get('PAT')

# Function to fetch RSS feed items
@lru_cache(maxsize=128)
def fetch_feed(url):
    feed = feedparser.parse(url)
    return feed.entries

# Function to fetch and parse HTML content with caching based on item ID
html_cache = {}
@lru_cache(maxsize=128)
def fetch_html_content(item_id, item_url):
    if item_id in html_cache:
        return html_cache[item_id]

    response = requests.get(item_url)
    soup = BeautifulSoup(response.content, "html.parser")
    html_content = soup.get_text()
    html_cache[item_id] = html_content
    return html_content

# Main function to run the Streamlit app
def main():
    st.title("LexaScan")

    # Input field for entering RSS URL
    rss_url = st.text_input("Enter RSS URL:", "https://feeds.bbci.co.uk/news/rss.xml")

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
                
                # Create formatted string with title, image URL, and description
                formatted_string = f"Title: {selected_item.title}\n"
                if 'image' in selected_item:
                    formatted_string += f"Image URL: {selected_item.image.url}\n"
                formatted_string += f"Description: {selected_item.summary}"

                # Write formatted string to text area
                st.text_area("Item Details", value=formatted_string, height=200)

            except Exception as e:
                st.error(f"Error fetching RSS feed: {e}")

if __name__ == "__main__":
    main()
