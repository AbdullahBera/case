import streamlit as st
from typing import Callable, Any

def setup_page_style():
    """Set up the page styling with custom CSS"""
    st.markdown("""
    <style>
        div.card {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h3 {
            color: #262730;
            margin-bottom: 10px;
        }
        .card-title {
            font-weight: bold;
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

def create_card(container, title: str, icon: str, content_function: Callable, *args, **kwargs):
    """Create a card with a title and content"""
    with container:
        st.markdown(f"<h3>{icon} {title}</h3>", unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            content_function(*args, **kwargs)
            st.markdown('</div>', unsafe_allow_html=True)