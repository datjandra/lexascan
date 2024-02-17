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
    rss_url = st.text_input("Enter RSS URL:")

    # Button to fetch RSS items
    if st.button("Fetch RSS Items"):
        if rss_url:
            try:
                items = fetch_feed(rss_url)

                # Display selected item content
                selected_item_index = st.selectbox("Select an item", range(len(items)))
                selected_item = items[selected_item_index]
                st.write(selected_item.title)

                # Fetch and display HTML content with caching based on item ID
                item_id = selected_item.id if selected_item.id else selected_item.link
                item_content = fetch_html_content(item_id, selected_item.link)
                st.write(item_content)

            except Exception as e:
                st.error(f"Error fetching RSS feed: {e}")

if __name__ == "__main__":
    main()
