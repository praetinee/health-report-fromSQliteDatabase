import streamlit as st

def inject_global_styles():
    st.markdown(
        """
        <style>
            /* Responsive Text and Layout */
            html, body, [class*="css"] {
                font-family: "Sarabun", sans-serif;
                font-size: 16px;
                color: inherit;
            }

            /* Make report container flexible */
            .reportview-container .main {
                display: flex;
                flex-direction: column;
                align-items: stretch;
                padding: 1rem;
            }

            /* Responsive table */
            table {
                width: 100%;
                display: block;
                overflow-x: auto;
                border-collapse: collapse;
            }

            th, td {
                padding: 6px 12px;
                text-align: left;
                white-space: nowrap;
            }

            @media screen and (max-width: 768px) {
                body {
                    font-size: 14px;
                }
                .reportview-container .main {
                    padding: 0.5rem;
                }
            }

            /* Advice box styling */
            .advice-box {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
                padding: 0.75rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
