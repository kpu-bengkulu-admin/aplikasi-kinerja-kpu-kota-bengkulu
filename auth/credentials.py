import json
import os

import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


TOKEN_FILE = "auth/oauth_token.json"


def get_google_credentials():

    token_data = None

    # ===============================
    # MODE LOCAL
    # ===============================
    if os.path.exists(TOKEN_FILE):

        with open(
            TOKEN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            token_data = json.load(f)

    # ===============================
    # MODE STREAMLIT CLOUD
    # ===============================
    else:

        try:

            if "oauth_token" in st.secrets:

                token_data = dict(
                    st.secrets["oauth_token"]
                )

        except Exception:

            st.exception(e)
            raise

    if token_data is None:

        raise Exception(
            "oauth_token.json tidak ditemukan."
        )

    credentials = Credentials(

        token=token_data.get("token"),

        refresh_token=token_data.get(
            "refresh_token"
        ),

        token_uri=token_data.get(
            "token_uri"
        ),

        client_id=token_data[
            "client_id"
        ],

        client_secret=token_data[
            "client_secret"
        ],

        scopes=tuple(
            token_data["scopes"]
        ),
    )

    if not credentials.valid:

        credentials.refresh(Request())

    return credentials